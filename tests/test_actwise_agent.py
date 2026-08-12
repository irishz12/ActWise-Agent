from backend.agent import run_agent


result = run_agent(
    "In customers.csv, find duplicate customer IDs "
    "and tell me the average premium."
)

print("\nFinal decision:", result["decision"])

print("\nExecuted tools:")
for index, step in enumerate(result["tool_history"], start=1):
    print(index, step["tool"], step["arguments"])

print("\nSkipped tools:")
for index, step in enumerate(result["skipped_calls"], start=1):
    print(
        index,
        step["tool"],
        "-",
        step["reason"],
    )

print("\nDecision history:")
for index, decision in enumerate(
    result["decision_history"],
    start=1,
):
    print(
        index,
        decision["decision"],
        "-",
        decision["reason"],
    )

print("\nAnswer:")
print(result["answer"])
