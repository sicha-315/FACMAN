import simpy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 공정 코드 정의
PROCESS_CODES = {
    1: "INSP",  # 원재료 입고 및 검사
    2: "PREP",  # 전처리 공정
    3: "CAST",  # 주조 및 성형 공정
    4: "QC01",  # 비파괴 검사 및 품질 관리
    5: "COAT",  # 도장 및 표면 마감
    6: "ASSE",  # 조립 공정
    7: "QC02",  # 최종 품질 검사(QC)
    8: "PACK",  # 포장 및 출하
}

# 시뮬레이션 매개변수
params = {
    1: {'process_id': 1, 'mean_service_time': 2,  'servers': 2},
    2: {'process_id': 2, 'mean_service_time': 10, 'servers': 1},
    3: {'process_id': 3, 'mean_service_time': 15, 'servers': 2},
    4: {'process_id': 4, 'mean_service_time': 5,  'servers': 2},
    5: {'process_id': 5, 'mean_service_time': 20, 'servers': 1},
    6: {'process_id': 6, 'mean_service_time': 12, 'servers': 1},
    7: {'process_id': 7, 'mean_service_time': 3,  'servers': 2},
    8: {'process_id': 8, 'mean_service_time': 15, 'servers': 1},
}

# 시뮬레이션 시작 및 종료 시간
start_date = datetime(2024, 1, 1, 9, 0, 0)
duration_days = 30
end_date = start_date + timedelta(days=duration_days)

# 근무 시간 정의
working_hours = [(9, 17), (20, 5)]

def is_working_time(current_time):
    """현재 시간이 근무 시간 내인지 확인"""
    hour = current_time.hour
    return any(start <= hour < end if start < end else start <= hour or hour < end for start, end in working_hours)

# 시뮬레이션 환경 및 데이터 저장
class FactorySimulation:
    def __init__(self, env, params):
        self.env = env
        self.params = params
        self.resources = {p['process_id']: simpy.Resource(env, capacity=p['servers']) for p in params.values()}
        self.data = []
    
    def process_product(self, product_id, process_id):
        process_info = self.params[process_id]
        resource = self.resources[process_id]
        
        arrival_time = self.env.now
        with resource.request() as request:
            yield request
            start_time = self.env.now
            service_time = np.random.exponential(process_info['mean_service_time'])
            yield self.env.timeout(service_time)
            finish_time = self.env.now
            
            server_number = (hash(product_id) % resource.capacity) + 1  # 서버 번호 할당
            server_id = f"{PROCESS_CODES[process_id]}{str(server_number).zfill(3)}"
            self.data.append([product_id, process_id, server_id, arrival_time, start_time, finish_time])

# 제품 흐름 정의
class Product:
    def __init__(self, env, sim, product_id):
        self.env = env
        self.sim = sim
        self.product_id = product_id
        self.process_chain()
    
    def process_chain(self):
        for process_id in params.keys():
            yield self.env.process(self.sim.process_product(self.product_id, process_id))

# 시뮬레이션 실행
def run_simulation():
    env = simpy.Environment()
    factory_sim = FactorySimulation(env, params)
    
    product_id = 1
    current_time = start_date
    
    while current_time < end_date:
        if is_working_time(current_time):
            env.process(Product(env, factory_sim, product_id).process_chain())
            product_id += 1
        current_time += timedelta(minutes=1)
    
    env.run()
    
    # 데이터프레임 생성 및 포맷팅
    df = pd.DataFrame(factory_sim.data, columns=["product_id", "process_id", "server_id", "arrival_time", "start_time", "finish_time"])
    df["arrival_time"] = start_date + pd.to_timedelta(df["arrival_time"], unit="m")
    df["start_time"] = start_date + pd.to_timedelta(df["start_time"], unit="m")
    df["finish_time"] = start_date + pd.to_timedelta(df["finish_time"], unit="m")
    df["arrival_time"] = df["arrival_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["start_time"] = df["start_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["finish_time"] = df["finish_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    df_result['process_id'] = df_result['process_id'].map(PROCESS_CODES)
    
    return df

if __name__ == "__main__":
    df_result = run_simulation()
    df_result.to_csv('simulation_result.csv', index=False)