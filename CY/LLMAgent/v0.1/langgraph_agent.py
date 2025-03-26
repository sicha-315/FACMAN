from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

# 상태 정의
class ProcessState(TypedDict):
    runtime: float
    failure_rate: float
    need_maintenance: bool
    
# LLM 준비
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini",
                 api_key=api_key)

# 프롬프트 정의
prompt = ChatPromptTemplate.from_template("""
당신은 공정 점검 AI입니다.
해당 공정은 제품 1개 생산하는데 평균 10초 소요됩니다.
고장 전 점검할 경우 평균 15초가 소요되며, 고장 시 수리하는 데 평균 60초가 소요됩니다.
현재 공정의 상태는 다음과 같습니다:
- 가동 시간: {runtime:.2f}초
- 추정된 고장 확률: {failure_rate:.2f}

이 공정을 지금 점검해야 하나요? 가동률이 최대가 되도록 결정해주세요.
"예" 또는 "아니오"로 먼저 대답한 후, 그 이유를 간단히 설명해주세요.
""")

# LangGraph 노드 함수: LLM으로 판단
def llm_judgment(state: ProcessState) -> ProcessState:
    chain = prompt | llm
    response = chain.invoke(state)
    content = response.content.strip()

    # 첫 줄이 "예" or "아니오", 그 이후는 설명이라고 가정
    lines = content.split("\n", 1)
    first_line = lines[0].strip()
    reason = lines[1].strip() if len(lines) > 1 else "설명 없음"

    state["need_maintenance"] = "예" in first_line
    print("🧠 [LLM 판단]")
    print("→ 판단 결과:", first_line)
    print("→ 판단 근거:", reason)
    return state


# LangGraph 컴파일 함수
def build_langgraph():
    builder = StateGraph(ProcessState)
    builder.add_node("판단", RunnableLambda(llm_judgment))
    builder.set_entry_point("판단")
    builder.set_finish_point("판단")
    return builder.compile()