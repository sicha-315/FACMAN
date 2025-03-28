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
        process_name: str,
        mode: str,
        process_prev: str = None,
        process_next: str = None,
        influxdb_url: str = None,
        influxdb_token: str = None,
        influxdb_org: str = None,
        redis_url: str = "localhost",
        agent_url: str = None,
        sim_speed: float = 5.0,
    ):
        self.process_name = process_name
        self.process_prev = process_prev
        self.process_next = process_next
        
        self.influxdb_client = InfluxDBClient(
            url=influxdb_url,
            token=influxdb_token,
            org=influxdb_org
        )
        self.write_api=self.influxdb_client.write_api(write_options=SYNCHRONOUS)
        self.status_bucket = f"{self.process_name}_status"
        self.process_bucket = f"{self.process_name}_process"

        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True
        )
        
        self.agent_url = agent_url

        self.is_broken = False
        self.runtime = 0.0
        self.failure_prob = 0.0
        self.item = []

        self.step_time = max(np.random.normal(10, 2), 5) / sim_speed
        self.maintain_time = max(np.random.normal(15, 5), 10) / sim_speed
        self.repair_time = max(np.random.normal(60, 10), 45) / sim_speed
        
        self.mode = mode
        if self.mode == "producer":
            self.run_loop = self.run_producer
        elif self.mode == "relay":
            self.run_loop = self.run_relay
        elif self.mode == "consumer":
            self.run_loop = self.run_consumer
        else:
            raise ValueError("Invalid mode")

    # InfluxDB에 상태 로그 저장
    def logging_status(self, event_type, event_status, available):
        point = (
            Point("status_log")
            .tag("process", self.process_name)
            .field("event_type", event_type)
            .field("event_status", event_status)
            .field("available", int(available))
            .time(datetime.datetime.now())
        )
        try:
            self.write_api.write(bucket=self.status_bucket, record=point)
            print(f"Logging status: {event_type} {event_status} {available}")
        except Exception as e:
            print(f"InfluxDB status_log error: {e}")

    # InfluxDB에 공정 로그 저장
    def logging_process(self, event_type, event_status, available):
        point = (
            Point("process_log")
            .tag("process", self.process_name)
            .field("event_type", event_type)
            .field("event_status", event_status)
            .field("available", int(available))
            .time(datetime.datetime.now())
        )
        try:
            self.write_api.write(bucket=self.process_bucket, record=point)
            print(f"Logging process: {event_type} {event_status} {available}")
        except Exception as e:
            print(f"InfluxDB process_log error: {e}")

    def should_fail(self):
        return random.random() < self.failure_prob

    def repair(self):
        self.logging_status("repair", "start", False)
        time.sleep(self.repair_time)
        self.reset()
        self.logging_status("repair", "finish", True)

    def maintenance(self):
        self.logging_status("maintenance", "start", False)
        time.sleep(self.maintain_time)
        self.reset()
        self.logging_status("maintenance", "finish", True)

    def reset(self):
        self.runtime = 0.0
        self.failure_prob = 0.0
        self.is_broken = False

    def update_failure_rate(self):
        self.failure_prob = 1 - np.exp(-self.runtime / 120)

    def check_maintenance(self):
        if self.agent_url is None:
            if self.failure_prob > 0.15:
                self.maintenance()
        try:
            res = requests.post(self.agent_url, json={"process_id": self.process_name}, timeout=5)
            res.raise_for_status()
            result = res.json()
            if result.get("need_maintenance", False):
                self.maintenance()
        except Exception as e:
            print(e)
        
    def process_step(self):
        self.logging_process("step", "start", True)
        time.sleep(self.step_time)
        self.runtime += self.step_time
        self.update_failure_rate()
        
        if self.should_fail():
            self.is_broken = True
            self.logging_status("failure", "", False)
            self.logging_process("step", "interrupt", False)
            self.repair()
            return False
        
        self.logging_process("step", "finish", True)
        return True

    def run_producer(self):
        item_id = 0
        while True:
            try:
                if not self.process_step():
                    continue
                item = f"item_{item_id}"
                self.redis_client.rpush(self.process_prev, item)
                item_id += 1

                self.check_maintenance()
            except Exception as e:
                print(e)
    
    def run_relay(self):
        while True:
            try:
                item = self._receive_item(self.process_prev)
                if item is None:
                    continue

                if not self._process_step():
                    continue

                self.redis_client.rpush(self.process_next, item)

                self._check_maintenance()
            except Exception as e:
                print(e)

    def run_consumer(self):
        while True:
            try:
                item = self._receive_item(self.process_prev)
                if item is None:
                    continue

                if not self._process_step():
                    continue

                self._check_maintenance()
            except Exception as e:
                print(e)
                
    def run(self):
        self.run_loop()
