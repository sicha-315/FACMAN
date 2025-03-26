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
        influxdb_url: str,
        influxdb_token: str,
        influxdb_org: str,
        influxdb_status_bucket: str,
        influxdb_process_bucket: str,
        redis_host: str,
        redis_port: int,
        redis_password: str = None,
        agent_url: str = None,
        sim_speed: float = 5.0,
    ):
        self.process_name = process_name
        
        # InfluxDB 설정
        self.influxdb_client = InfluxDBClient(
            url=influxdb_url,
            token=influxdb_token,
            org=influxdb_org
        )
        self.write_api=self.influxdb_client.write_api(write_options=SYNCHRONOUS)
        self.status_bucket=influxdb_status_bucket
        self.process_bucket=influxdb_process_bucket

        # Redis 설정 (AWS Redis 포함)
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=0,
            decode_responses=True
        )
        
        # Agent 설정
        self.agent_url = agent_url

        # 공정 상태
        self.is_broken = False
        self.runtime = 0.0
        self.failure_prob = 0.0

        self.step_time = max(np.random.normal(10, 2), 5) / sim_speed
        self.maintain_time = max(np.random.normal(15, 5), 10) / sim_speed
        self.repair_time = max(np.random.normal(60, 10), 45) / sim_speed

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
            return self.failure_prob > 0.15
        payload = {
            "runtime": self.runtime,
            "failure_rate": self.failure_prob
        }
        try:
            res = requests.post(self.agent_url, json=payload, timeout=5)
            res.raise_for_status()
            result = res.json()
            return result.get("need_maintenance", False)
        except Exception as e:
            print(e)
            return False

    def run_producer(self):
        item_id = 0

        while True:
            self.logging_process("step", "start", True)
            time.sleep(self.step_time)
            self.runtime += self.step_time
            self.update_failure_rate()

            if self.should_fail():
                self.is_broken = True
                self.logging_status("failure", "", False)
                self.logging_process("step", "interrupt", False)
                self.repair()
                continue

            self.logging_process("step", "finish", True)

            item = f"item_{item_id}"
            self.redis_client.rpush("P2_queue", item)
            item_id += 1

            if self.check_maintenance():
                self.maintenance()

    def run_consumer(self):
        while True:
            item = self.redis_client.blpop("P2_queue", timeout=0)
            if not item:
                continue
            item = item[1]
            self.logging_process("step", "start", True)
            time.sleep(self.step_time)
            self.runtime += self.step_time
            self.update_failure_rate()

            if self.should_fail():
                self.is_broken = True
                self.logging_status("failure", "", False)
                self.logging_process("step", "interrupt", False)
                self.repair()
                continue

            self.logging_process("step", "finish", True)

            if self.check_maintenance():
                self.maintenance()
