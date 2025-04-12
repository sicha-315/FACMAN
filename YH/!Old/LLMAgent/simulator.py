import random
import time
import requests  # FastAPI 서버와 통신
import numpy as np
import json

class ProcessSimulator:
    def __init__(self, simulation_speed=1):
        self.runtime = 0.0              # 총 가동 시간
        self.failure_rate = 0.0       # 고장 확률 (0~1)
        self.is_broken = False
        self.total_time = 0.0           # 전체 공정 시간(초)
        self.total_failure_time = 0.0   # 전체 고장 시간(초) 비가동 시간
        self.maintenance_count = 0
        self.repair_count = 0
        self.simulation_speed = simulation_speed

    def update_failure_rate(self):
        # 고장률은 가동 시간에 따라 선형 증가 (예: 매 30초마다 10% 증가)
        self.failure_rate = min(0.01 * (self.runtime // 3), 0.9)

    def should_fail(self):
        # 현재 고장률에 따라 고장이 날지 결정
        return random.random() < self.failure_rate

    def check_maintenance(self) -> bool:
        url = "http://127.0.0.1:8000/check"
        payload = {
            "runtime": self.runtime,
            "failure_rate": self.failure_rate
        }
        try:
            res = requests.post(url, json=payload, timeout=5)
            res.raise_for_status()
            result = res.json()
            return result.get("need_maintenance", False)
        except Exception as e:
            print(f"[에러] FastAPI 서버와 통신 실패: {e}")
            return False

    def run_step(self):
        speed = max(np.random.normal(10,5),2)  # 작업 속도 (2~10초 사이)
        print(f"[작업 시작] {speed:2f}초 동안 작업 수행 중...")
        time.sleep(speed / self.simulation_speed)
        self.runtime += speed
        self.total_time += speed
        self.update_failure_rate()

        if self.should_fail():
            self.is_broken = True
            print(f"[고장 발생] 고장률: {self.failure_rate:.2f}, 총 가동시간: {self.runtime}초")
            self.repair()

        elif self.check_maintenance():
            print(f"[에이전트 판단] 점검 필요 → 점검 수행")
            self.maintenance()
        else:
            pass
            #print(f"[에이전트 판단] 점검 불필요 → 계속 진행")

    def repair(self):
        print("[수리 중] 약 60초 소요...")
        repair_time = max(np.random.normal(60, 10),10)  # 수리 시간 (30~90초 사이)
        time.sleep(repair_time / self.simulation_speed)
        self.total_time += repair_time
        self.total_failure_time += repair_time
        self.runtime = 0
        self.failure_rate = 0.0
        self.is_broken = False
        self.repair_count += 1
        print(f"[수리 완료]: {repair_time:.2f}초 소요")

    def maintenance(self):
        print("[점검 중] 약 15초 소요...")
        maintanance_time = np.random.normal(15,5)
        time.sleep(maintanance_time / self.simulation_speed)
        self.total_time += maintanance_time
        self.total_failure_time += maintanance_time
        self.runtime = 0
        self.failure_rate = 0.0
        self.maintenance_count += 1
        print(f"[점검 완료] {maintanance_time:.2f}초")

    def simulate(self, steps=30):
        print("=== 공정 시뮬레이션 시작 ===")
        for i in range(steps):
            print(f"\n--- Step {i + 1} ---")
            self.run_step()
        print("\n=== 시뮬레이션 종료 ===")
        print(f"총 공정 시간: {self.total_time:.2f}초")
        print(f"총 가동률: {(self.total_time - self.total_failure_time) / self.total_time * 100:.2f}%")
        print(f"총 점검 횟수: {self.maintenance_count}회")
        print(f"총 수리 횟수: {self.repair_count}회")


if __name__ == "__main__":
    sim = ProcessSimulator(simulation_speed=5)  # 5배 빠르게 실행
    sim.simulate(steps=20)