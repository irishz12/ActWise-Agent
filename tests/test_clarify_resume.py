from backend.graph_agent import (
    resume_graph_agent,
    run_graph_agent,
)


thread_id = "clarify-resume-test-1"


print("\nTURN 1")

first = run_graph_agent(
    "Calculate a summary for customers.csv.",
    thread_id=thread_id,
)

print("Decision:", first.get("decision"))

interrupts = first.get("__interrupt__", [])

print("Paused:", bool(interrupts))

if interrupts:
    print("Question:", interrupts[0].value)


print("\nTURN 2")

second = resume_graph_agent(
    "premium",
    thread_id=thread_id,
)

print("Decision:", second.get("decision"))

print("\nExecuted tools:")
for step in second.get("tool_history", []):
    print(
        "-",
        step["tool"],
        step["arguments"],
    )

print("\nDecision history:")
for step in second.get("decision_history", []):
    print(
        "-",
        step["decision"],
        "->",
        step["reason"],
    )

print("\nAnswer:")
print(second.get("answer"))
