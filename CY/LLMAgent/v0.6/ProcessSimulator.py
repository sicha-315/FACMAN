import random
import time
import threading
from datetime import datetime, timezone
import redis
import requests
import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class ItemIDGenerator:
    def __init__(self):
        self.last_minute = None
        self.counter = 0

    def generate(self):
        current_minute = datetime.now(timezone.utc).strftime("%y%m%d%H%M")  # 년도를 두 자리로 표시

        if current_minute != self.last_minute:
            self.last_minute = current_minute
            self.counter = 0
        
        item_id = f"{current_minute}{self.counter}"
        self.counter += 1
        return item_id

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

        self._redis_client = redis.from_url(
            redis_url,
            decode_responses=True
        )
        
        self._agent_url = agent_url

        self._is_broken = False
        self._runtime = 0.0
        self._failure_prob = 0.0
        self._is_maintenance = False
        
        self.sim_speed = sim_speed        
        self._mode = mode
        self._item_id_generator = ItemIDGenerator()
        
        if self._mode == "producer":
            self._run_loop = self._run_producer
        elif self._mode == "relay":
            self._run_loop = self._run_relay
        elif self._mode == "consumer":
            self._run_loop = self._run_consumer
        else:
            raise ValueError("Invalid mode")
        
        threading.Thread(target=self._check_maintenance, daemon=True).start()
        
    @property
    def _step_time(self):
        return max(np.random.normal(10, 2), 5) / self.sim_speed
    @property
    def _maintain_time(self):
        return max(np.random.normal(100, 5), 10) / self.sim_speed
    @property
    def _repair_time(self):
        return max(np.random.normal(60, 10), 45) / self.sim_speed

    def _logging_status(self, event_type, event_status, available):
        point = (
            Point("status_log")
            .tag("process", self._process_name)
            .field("event_type", event_type)
            .field("event_status", event_status)
            .field("available", int(available))
            .time(datetime.now(timezone.utc))
        )
        try:
            self._write_api.write(bucket=f'{self._process_name}_status', record=point)
            print(f"Logging status: {event_type} {event_status} {available}")
        except Exception as e:
            print(f"InfluxDB status_log error: {e}")

    def _logging_process(self, product_id, process_id, line_id, status):
        point = (
            Point("process_log")
            .tag("product_id", product_id)
            .tag("process_id", process_id)
            .tag("line_id", line_id)
            .field("status", status)
            .time(datetime.now(timezone.utc))
        )
        try:
            self._write_api.write(bucket="process", record=point)
            print(f"Logging process: process {product_id} {process_id} {line_id} {status}")
        except Exception as e:
            print(f"InfluxDB process_log error: {e}")

    def _should_fail(self):
        return random.random() < self._failure_prob

    def _repair(self):
        self._logging_status("repair", "start", False)
        time.sleep(self._repair_time)
        self._reset()
        self._logging_status("repair", "finish", True)
        self._logging_status("processing", "", True)

    def _maintenance(self):
        self._logging_status("maintenance", "start", False)
        time.sleep(self._maintain_time)
        self._reset()
        self._logging_status("maintenance", "finish", True)
        self._logging_status("processing", "", True)

    def _reset(self):
        self._runtime = 0.0
        self._failure_prob = 0.0
        self._is_broken = False
        self._is_maintenance = False

    def _update_failure_rate(self):
        self._failure_prob = 1 - np.exp(-self._runtime / 120)

    def _check_maintenance(self):
        pubsub = self._redis_client.pubsub()
        pubsub.subscribe(f"{self._process_name}_maintenance")
        for message in pubsub.listen():
            if message['type'] == 'message':
                print(f"Received maintenance command: {message['data']}")
                self._is_maintenance = True

    def _receive_item(self, process_name):
        item = self._redis_client.blpop(process_name)
        if item is None:
            return None
        return item[1]

    def _process_step(self, item):
        self._logging_process(item, self._process_name[:-2], self._process_name, "start")
        time.sleep(self._step_time)
        self._runtime += self._step_time
        self._update_failure_rate()
        if self._should_fail():
            self._is_broken = True
            self._logging_status("failure", "", False)
            self._logging_process(item, self._process_name[:-2], self._process_name, "interrupt")
            time.sleep(5)
            self._repair()
            return False
        self._logging_process(item, self._process_name[:-2], self._process_name, "finish")
        return True

    def _run_producer(self):
        item_id = 0
        while True:
            try:
                item = self._item_id_generator.generate() + self._process_next[-1]
                self._redis_client.rpush(self._process_next, item)
                self._logging_process(item, self._process_name, "", "input")
                print(f"Produced: {item}")
                item_id += 1
                time.sleep(self._step_time)
                self._logging_process(item, self._process_next[:-2], self._process_next, "arrival")
            except Exception as e:
                print(e)

    def _run_relay(self):
        while True:
            try:
                if self._is_maintenance:
                    self._maintenance()
                    continue
                
                item = self._receive_item(self._process_name)
                if item is None:
                    continue
                if not self._process_step(item):
                    continue
                self._redis_client.rpush(self._process_next, item)
                self._logging_process(item, self._process_next[:-2], self._process_next, "arrival")
                
                if self._is_maintenance:
                    self._maintenance()
                    continue
                    
            except Exception as e:
                print(e)

    def _run_consumer(self):
        while True:
            try:
                item = self._receive_item(self._process_name)
                if item is None:
                    continue
                self._logging_process(item, self._process_name, "", "arrival")
            except Exception as e:
                print(e)

    def run(self):
        print(f"Running {self._process_name} in {self._mode} mode")
        self._run_loop()
