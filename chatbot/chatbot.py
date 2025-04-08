from typing import Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from influxdb_client import InfluxDBClient
from langchain.agents import Tool
from dotenv import load_dotenv
import os
import re

class State(TypedDict):
    # 메시지 목록에 주석 추가
    messages: Annotated[list, add_messages]

def load_environment_variables():
    """환경 변수를 로드합니다."""
    load_dotenv()
    return {
        "INFLUXDB_URL": os.getenv("INFLUXDB_URL"),
        "INFLUXDB_TOKEN": os.getenv("INFLUXDB_TOKEN"),
        "INFLUXDB_ORG": os.getenv("INFLUXDB_ORG")
    }

def init_influxdb_client(config):
    """InfluxDB 클라이언트를 초기화합니다."""
    client = InfluxDBClient(
        url=config["INFLUXDB_URL"],
        token=config["INFLUXDB_TOKEN"],
        org=config["INFLUXDB_ORG"]
    )
    return client

def influxdb_flux_query_tool(process_id):
    """InfluxDB에서 프로세스 로그를 조회하는 도구입니다.
    
    Args:
        process_id (str): 조회할 프로세스 ID 또는 라인 ID (예: 'P1' 또는 'P1-A')
        
    Returns:
        str: 로그 결과 또는 오류 메시지
    """
    # 프로세스 ID가 유효한지 확인
    if not process_id or not isinstance(process_id, str):
        return "유효한 프로세스 ID 또는 라인 ID를 입력해주세요 (예: 'P1' 또는 'P1-A')"
    
    # 하이픈을 포함한 형식인지 확인 (P1-A와 같은 라인 ID)
    if "-" in process_id:
        # 라인 ID로 검색할 경우
        query = f'''
        from(bucket: "process")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "process_log")
        |> filter(fn: (r) => r.line_id == "{process_id}")
        '''
    else:
        # 프로세스 ID로 검색할 경우
        query = f'''
        from(bucket: "process")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "process_log")
        |> filter(fn: (r) => r.process_id == "{process_id}")
        '''
    
    try:
        tables = query_api.query(query)
        logs = []
        for table in tables:
            for record in table.records:
                logs.append(f"{record.get_time()}: {record.get_value()}")
        
        if not logs:
            # 검색 결과가 없는 경우
            if "-" in process_id:
                return f"라인 ID '{process_id}'에 대한 로그가 없습니다."
            else:
                return f"프로세스 ID '{process_id}'에 대한 로그가 없습니다."
            
        return "\n".join(logs)
    except Exception as e:
        return f"로그 조회 중 오류 발생: {e}"

def create_tools(query_tool):
    """도구 목록을 생성합니다."""
    tool = Tool(
        name="query_process_logs",
        func=query_tool,
        description="""Get recent status logs from InfluxDB for the given process_id or line_id.
        The function returns the most recent status logs from the last hour.
        Input should be a process ID (e.g., 'P1') or a line ID (e.g., 'P1-A').
        Process ID is used to query by process_id field, while input with hyphen like 'P1-A' is used to query by line_id field.
        """
    )
    return [tool]

def create_chatbot_node(llm_with_tools):
    """챗봇 노드 함수를 생성합니다."""
    def chatbot(state: State):
        # 메시지를 LLM을 통해 처리하며, 내부에서 도구(tool)가 호출될 수 있음.
        return {"messages": [llm_with_tools.invoke(state["messages"])]}
    return chatbot

def build_graph(tools):
    """LangGraph 상태 그래프를 구성합니다."""
    # LLM 초기화 - 도구 사용 능력을 향상시키기 위해 더 강력한 모델 사용
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # 도구와 LLM 결합
    llm_with_tools = llm.bind_tools(tools)
    
    # 상태 그래프 생성
    graph_builder = StateGraph(State)
    
    # 챗봇 노드 추가
    chatbot = create_chatbot_node(llm_with_tools)
    graph_builder.add_node("chatbot", chatbot)
    
    # 도구 노드 생성 및 추가
    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)
    
    # 조건부 엣지 추가 (도구 사용 조건에 따른 연결)
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    
    # 엣지 추가
    graph_builder.add_edge("tools", "chatbot")  # tools > chatbot
    graph_builder.add_edge(START, "chatbot")    # START > chatbot
    graph_builder.add_edge("chatbot", END)      # chatbot > END
    
    memory = MemorySaver()
    
    return graph_builder.compile(checkpointer=memory)

def stream_graph_updates(graph, user_input: str):
    config = RunnableConfig(
    recursion_limit=10,  # 최대 10개의 노드까지 방문. 그 이상은 RecursionError 발생
    configurable={"thread_id": "1"},  # 스레드 ID 설정
    )
    """그래프 업데이트를 스트리밍합니다."""
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]},config=config):
        for value in event.values():
            if "messages" in value and value["messages"]:
                print("Assistant:", value["messages"][-1].content)

def run_chat_loop(graph):
    """사용자 입력을 받아 대화를 진행하는 루프를 실행합니다."""
    print("프로세스 모니터링 시스템에 오신 것을 환영합니다.")
    print("프로세스 ID를 입력하여 상태를 확인하세요 (예: 'P1-A의 상태는 어때?')")
    print("종료하려면 'exit' 또는 'q'를 입력하세요.")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            stream_graph_updates(graph, user_input)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            # 에러 발생 시에도 계속 진행
            continue

def main():
    """메인 함수로, 애플리케이션을 실행합니다."""
    # 환경 변수 로드
    env_vars = load_environment_variables()
    
    # InfluxDB 클라이언트 초기화
    global client, query_api
    client = init_influxdb_client(env_vars)
    query_api = client.query_api()
    
    # 도구 생성
    tools = create_tools(influxdb_flux_query_tool)
    
    # 상태 그래프 빌드
    graph = build_graph(tools)
    
    # 대화 루프 실행
    run_chat_loop(graph)

if __name__ == "__main__":
    main()