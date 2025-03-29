import random
import time
import datetime
import redis
import requests
import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class ProcessSimulator:
    def __init__(
        self,
        mode: str,
        process_name: str,
        process_next: str = None,
        influxdb_url: str = None,
        influxdb_token: str = None,
        influxdb_org: str = None,
        redis_url: str = "redis://localhost:6379",
        agent_url: str = None,
        sim_speed: float = 5.0,
    ):
        self._process_name = process_name
        self._process_next = process_next
        
        self._influxdb_client = InfluxDBClient(
            url=influxdb_url,
            token=influxdb_token,
            org=influxdb_org
        )
        self._write_api = self._influxdb_client.write_api(write_options=SYNCHRONOUS)
        self._status_bucket = f"{self._process_name}_status"
        self._process_bucket = f"{self._process_name}_process"

        self._redis_client = redis.from_url(
            redis_url,
            decode_responses=True
        )
        
        self._agent_url = agent_url

        self._is_broken = False
        self._runtime = 0.0
        self._failure_prob = 0.0
        self._item = []

        self._step_time = max(np.random.normal(10, 2), 5) / sim_speed
        self._maintain_time = max(np.random.normal(15, 5), 10) / sim_speed
        self._repair_time = max(np.random.normal(60, 10), 45) / sim_speed
        
        self._mode = mode
        if self._mode == "producer":
            self._run_loop = self._run_producer
        elif self._mode == "relay":
            self._run_loop = self._run_relay
        elif self._mode == "consumer":
            self._run_loop = self._run_consumer
        else:
            raise ValueError("Invalid mode")

    def _logging_status(self, event_type, event_status, available):
        point = (
            Point("status_log")
            .tag("process", self._process_name)
            .field("event_type", event_type)
            .field("event_status", event_status)
            .field("available", int(available))
            .time(datetime.datetime.now())
        )
        try:
            self._write_api.write(bucket=self._status_bucket, record=point)
            print(f"Logging status: {event_type} {event_status} {available}")
        except Exception as e:
            print(f"InfluxDB status_log error: {e}")

    def _logging_process(self, event_type, event_status, available):
        point = (
            Point("process_log")
            .tag("process", self._process_name)
            .field("event_type", event_type)
            .field("event_status", event_status)
            .field("available", int(available))
            .time(datetime.datetime.now())
        )
        try:
            self._write_api.write(bucket=self._process_bucket, record=point)
            print(f"Logging process: {event_type} {event_status} {available}")
        except Exception as e:
            print(f"InfluxDB process_log error: {e}")

    def _should_fail(self):
        return random.random() < self._failure_prob

    def _repair(self):
        self._logging_status("repair", "start", False)
        time.sleep(self._repair_time)
        self._reset()
        self._logging_status("repair", "finish", True)

    def _maintenance(self):
        self._logging_status("maintenance", "start", False)
        time.sleep(self._maintain_time)
        self._reset()
        self._logging_status("maintenance", "finish", True)

    def _reset(self):
        self._runtime = 0.0
        self._failure_prob = 0.0
        self._is_broken = False

    def _update_failure_rate(self):
        self._failure_prob = 1 - np.exp(-self._runtime / 120)

    def _check_maintenance(self):
        if self._agent_url is None:
            if self._failure_prob > 0.15:
                self._maintenance()
        else:
            try:
                res = requests.post(self._agent_url, json={"process_id": self._process_name}, timeout=5)
                res.raise_for_status()
                result = res.json()
                if result.get("need_maintenance", False):
                    self._maintenance()
            except Exception as e:
                print(e)

    def _receive_item(self, process_name):
        item = self._redis_client.blpop(process_name)
        if item is None:
            return None
        return item[1]

    def _process_step(self):
        self._logging_process("step", "start", True)
        time.sleep(self._step_time)
        self._runtime += self._step_time
        self._update_failure_rate()
        if self._should_fail():
            self._is_broken = True
            self._logging_status("failure", "", False)
            self._logging_process("step", "interrupt", False)
            self._repair()
            return False
        self._logging_process("step", "finish", True)
        return True

    def _run_producer(self):
        item_id = 0
        while True:
            try:
                item = f"item_{item_id}"
                self._redis_client.rpush(self._process_next, item)
                item_id += 1
                time.sleep(self._step_time)
                #self._logging_process("produce", "finish", True)
            except Exception as e:
                print(e)

    def _run_relay(self):
        while True:
            try:
                item = self._receive_item(self._process_name)
                if item is None:
                    continue
                if not self._process_step():
                    continue
                self._redis_client.rpush(self._process_next, item)
                self._check_maintenance()
            except Exception as e:
                print(e)

    def _run_consumer(self):
        while True:
            try:
                item = self._receive_item(self._process_name)
                if item is None:
                    continue
                if not self._process_step():
                    continue
                self._check_maintenance()
            except Exception as e:
                print(e)

    def run(self):
        self._run_loop()
