from fastapi import FastAPI
from pydantic import BaseModel
from typing import TypedDict
from langgraph.graph import StateGraph, END
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, initialize_agent, AgentType
import os
import json

# ========== 초기 설정 ==========
load_dotenv()

# === FastAPI 앱 ===
app = FastAPI()

# === InfluxDB 연결 ===
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")

client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
query_api = client.query_api()

# ========== 1. InfluxDB 로그 조회 함수 ==========
def query_process_logs(process_id: str) -> str:
    query = f'''
    from(bucket: "{process_id}_status")
      |> range(start: -10m)
      |> filter(fn: (r) => r._measurement == "status_log")
      |> sort(columns: ["_time"], desc: false)
    '''
    try:
        tables = query_api.query(org=INFLUXDB_ORG, query=query)
        logs = []
        for table in tables:
            for record in table.records:
                logs.append(f'{record["_time"]} | status: {record["status"]} | msg: {record["message"]}')
        return "\n".join(logs[:50])
    except Exception as e:
        return f"Influx Error: {e}"

# ========== 2. LangChain Tool 및 Agent 구성 ==========
llm = ChatOpenAI(model='gpt-4o-mini',temperature=0)

tools = [
    Tool(
        name="query_process_logs",
        func=query_process_logs,
        description="Get recent status logs from InfluxDB for the given process_id."
    )
]

agent_executor = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)

# ========== 3. LangGraph 노드 함수 정의 ==========
def llm_decide_node(state):
    process_id = state["process_id"]

    prompt = f"""
You are a factory supervisor agent.
Your job is to decide whether the process '{process_id}' needs maintenance.

Use the tool `query_process_logs` to fetch recent logs.
Analyze the logs and decide based on frequency and severity of failures.

Respond strictly in JSON format like:
{{
  "process_id": "process_x",
  "need_maintenance": true,
  "reason": "short explanation"
}}
    """

    response = agent_executor.run(prompt)

    try:
        decision = json.loads(response)
        return decision
    except json.JSONDecodeError:
        return {
            "process_id": process_id,
            "need_maintenance": False,
            "reason": "LLM response parse error"
        }

# ========== 4. LangGraph 구성 ==========
class SupervisorState(TypedDict):
    process_id: str
    need_maintenance: bool
    reason: str

graph_builder = StateGraph(state_schema=SupervisorState)
graph_builder.add_node("llm_decide", llm_decide_node)
graph_builder.set_entry_point("llm_decide")
graph_builder.add_edge("llm_decide", END)
graph = graph_builder.compile()

# ========== 5. FastAPI 요청 처리 ==========
class ProcessRequest(BaseModel):
    process_id: str

@app.post("/llm-check")
def check_with_llm(request: ProcessRequest):
    result = graph.invoke({"process_id": request.process_id})
    return result