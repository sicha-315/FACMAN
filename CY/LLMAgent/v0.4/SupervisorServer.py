from fastapi import FastAPI
from pydantic import BaseModel
from typing import TypedDict
from langgraph.graph import StateGraph, END
from influxdb_client import InfluxDBClient
import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# Supervisor FastAPI 앱
app = FastAPI()

# === InfluxDB 설정 ===
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")

client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
query_api = client.query_api()

# === 상태 수집 ===
def fetch_failure_rate(process_id: str):
    query = f'''
    from(bucket: "{process_id}_status")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "status_log" and r["process"] == "{process_id}")
      |> last()
    '''
    try:
        tables = query_api.query(org=INFLUXDB_ORG, query=query)
        # 간단하게 로그가 있는지만 확인
        if not tables or len(tables[0].records) == 0:
            return 0.0  # 기본값
        # 공정 시뮬레이터에서는 failure_prob를 직접 Influx에 쓰지는 않지만, 향후 쓰도록 할 수 있음
        # 지금은 supervisor 측에서 간단하게 추정해서 판단해도 OK
        return 0.8  # 테스트용 고정값
    except Exception as e:
        print("Influx Error:", e)
        return 0.0

# === LangGraph 판단 로직 ===
def supervisor_decision(state):
    process_id = state["process_id"]
    failure_rate = fetch_failure_rate(process_id)
    print(f"🔍 {process_id} failure_rate = {failure_rate}")
    need = failure_rate > 0.7
    return {"need_maintenance": need}

class SupervisorState(TypedDict):
    process_id: str

graph_builder = StateGraph(state_schema=SupervisorState)
graph_builder.add_node("decide", supervisor_decision)
graph_builder.set_entry_point("decide")
graph_builder.add_edge("decide", END)
graph = graph_builder.compile()

# === POST 요청을 받을 엔드포인트 ===
class ProcessRequest(BaseModel):
    process_id: str

@app.post("/")
def check_maintenance(request: ProcessRequest):
    result = graph.invoke({"process_id": request.process_id})
    return result