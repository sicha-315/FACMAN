from typing_extensions import TypedDict
from typing import Annotated
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
import json
import os
from dotenv import load_dotenv

# .env에서 OPENAI_API_KEY 로드
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

######################
# 1. 도구 (Tools)
######################
class AddTool:
    """
    두 숫자를 더하는 도구 예시
    """
    name = "add"

    def invoke(self, args: dict):
        a = args.get("a", 0)
        b = args.get("b", 0)
        result = a + b
        return {
            "description": "두 숫자를 더했습니다.",
            "input": args,
            "result": result
        }

class MultiplyTool:
    """
    두 숫자를 곱하는 도구 예시
    """
    name = "multiply"

    def invoke(self, args: dict):
        a = args.get("a", 1)
        b = args.get("b", 1)
        result = a * b
        return {
            "description": "두 숫자를 곱했습니다.",
            "input": args,
            "result": result
        }

######################
# 2. LLM 및 Tools 초기화
######################
tools = [AddTool(), MultiplyTool()]
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)

######################
# 3. 상태 (State) 정의
######################
class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

######################
# 4. Chatbot 노드
######################
def chatbot(state: State):
    """
    LLM에게 메시지를 전달해 답변을 생성하는 노드
    """
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)

######################
# 5. BasicToolNode
######################
class BasicToolNode:
    """
    마지막 AIMessage에서 요청된 도구를 실제로 실행하고 그 결과를 ToolMessage로 반환
    """
    def __init__(self, tools: list):
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")

        outputs = []
        # AI 메시지에서 tool_calls가 있으면 해당 도구 실행
        for tool_call in getattr(message, "tool_calls", []):
            tool_instance = self.tools_by_name[tool_call["name"]]
            tool_result = tool_instance.invoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                )
            )

        return {"messages": outputs}

tool_node = BasicToolNode(tools)
graph_builder.add_node("tools", tool_node)

######################
# 6. 도구 호출 분기 (route_tools)
######################
def route_tools(state: State):
    """
    마지막 메시지에 tool_calls가 있으면 'tools' 노드로,
    아니면 END로 라우팅
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError("No messages found in input state to tool_edge")

    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

# 라우팅 정의
graph_builder.add_conditional_edges(
    "chatbot",
    route_tools,
    {"tools": "tools", END: END},
)

# 노드 간 연결
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

######################
# 7. 그래프 컴파일 및 실행 루프
######################
graph = graph_builder.compile()

def stream_graph_updates(user_input: str):
    """
    사용자 입력을 받아 Graph를 수행하고
    매 스텝에서 발생하는 메시지를 출력
    """
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

if __name__ == "__main__":
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input)