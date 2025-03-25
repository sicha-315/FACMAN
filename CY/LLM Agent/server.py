from fastapi import FastAPI
from pydantic import BaseModel  # ✅ 최신 방식으로 import
from langgraph_agent import build_langgraph  # LangGraph 정의한 파일

app = FastAPI()
graph = build_langgraph()  # LangGraph 컴파일

# ✅ 클라이언트로부터 받을 데이터 구조 정의
class ProcessInput(BaseModel):
    runtime: float
    failure_rate: float

@app.post("/check")
def check_process(data: ProcessInput):
    state = {
        "runtime": data.runtime,
        "failure_rate": data.failure_rate,
        "need_maintenance": False
    }

    result = graph.invoke(state)
    print(f"[서버 응답] 점검 필요: {result['need_maintenance']}")
    return {"need_maintenance": result["need_maintenance"]}