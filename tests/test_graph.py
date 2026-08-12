from backend.graph import graph


state = {
    "user_message": (
        "In customers.csv, find duplicate customer IDs "
        "and tell me the average premium."
    ),
    "tool_history": [],
    "decision_history": [],
    "skipped_calls": [],
    "decision": None,
    "answer": None,
    "no_progress": 0,
}

result = graph.invoke(state)

print("\nDecision:", result["decision"])

print("\nExecuted tools:")
for step in result["tool_history"]:
    print("-", step["tool"], step["arguments"])

print("\nSkipped tools:")
for step in result["skipped_calls"]:
    print("-", step["tool"], "->", step["reason"])

print("\nDecision history:")
for step in result["decision_history"]:
    print("-", step["decision"], "->", step["reason"])

print("\nAnswer:")
print(result["answer"])
