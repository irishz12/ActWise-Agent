from langgraph.graph import END, START, StateGraph

from backend.agent import run_agent
from backend.state import AgentState


def run_actwise(state: AgentState):
    return run_agent(state["user_message"])


builder = StateGraph(AgentState)

builder.add_node("actwise", run_actwise)

builder.add_edge(START, "actwise")
builder.add_edge("actwise", END)

graph = builder.compile()
