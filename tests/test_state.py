from backend.state import AgentState


state: AgentState = {
    "user_message": "Find duplicates in customers.csv",
    "tool_history": [],
    "decision_history": [],
    "skipped_calls": [],
    "decision": None,
    "answer": None,
    "no_progress": 0,
}

print("Task:", state["user_message"])
print("Decision:", state["decision"])
print("Tool calls:", len(state["tool_history"]))
print("No progress:", state["no_progress"])
