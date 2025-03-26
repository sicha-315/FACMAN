import random
import time
import datetime
import requests
import redis
import numpy as np

class ProcessSimulator:
    def __init__(
        self,
        process_name: str,
        status_url: str = None,
        sim_speed: float = 5.0,
    ):
        self.process_name = process_name
        self.status_url = status_url
        
        self.is_broken = False
        self.runtime = 0.0
        self.failure_prob = 0.0
        
        self.step_time = max(np.random.normal(10, 2), 5) / sim_speed
        self.maintain_time = max(np.random.normal(15,5), 10) / sim_speed
        self.repair_time = max(np.random.normal(60,10), 45) / sim_speed
        
    # FastAPI가 아닌 InfluxDB에 로그를 저장하는 코드로 변경
    def logging(self, event_type, event_status, available):
        if self.status_url is None:
            return
        message = {"timestamp":str(datetime.datetime.now()),
                "event_type":event_type,
                "event_status":event_status,
                "available":available
                }
        try:
            res = requests.post(self.status_url, json=message, timeout=5)
            res.raise_for_status()
            return True
        except Exception as e:
            print(e)
            return False
    
    def should_fail(self):
        return random.random() < self.failure_prob
        
    def repair(self):
        self.logging("repair","start",False)
        time.sleep(self.repair_time)
        self.reset()
        self.logging("repair","finish",True)
    
    def maintenance(self):
        self.logging("maintenance","start",False)
        time.sleep(self.maintain_time)
        self.reset()
        self.logging("maintenance","finish",True)
        
    def reset(self):
        self.runtime = 0.0
        self.failure_prob = 0.0
        self.is_broken = False
        
    def update_failure_rate(self):
        self.failure_prob = 1 - np.exp(-self.runtime/120)
        
    def check_maintenance(self):
        return self.failure_prob > 0.15
    
    # AWS Redis를 사용하도록 코드 수정
    def run_producer(self):
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        item_id = 0
        
        while True:
            self.logging("step","start",True)
            time.sleep(self.step_time)
            self.runtime += self.step_time
            self.update_failure_rate()
            
            if self.should_fail():
                self.is_broken = True
                self.logging("failure","",False)
                self.logging("step","interrupt",False)
                self.repair()
                continue
            
            self.logging("step","finish",True)
            
            # 생산된 아이템 Redis 큐에 전송
            item = f"item_{item_id}"
            redis_client.rpush("P2_queue", item)
            item_id += 1
            
            if self.check_maintenance():
                self.maintenance()
            
    def run_consumer(self):
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        while True:
            # Redis에서 아이템 대기
            item = redis_client.blpop("P2_queue", timeout=0)  # 무한 대기
            item = item[1].decode("utf-8")  # 바이트 → 문자열
            self.logging("step", "start", True)
            time.sleep(self.step_time)
            self.runtime += self.step_time
            self.update_failure_rate()
            
            if self.should_fail():
                    self.is_broken = True
                    self.logging("failure","",False)
                    self.logging("step","interrupt",False)
                    self.repair()
                    continue
                
            self.logging("step","finish",True)
            
            if self.check_maintenance():
                self.maintenance()