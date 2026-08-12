from backend.agent import run_agent


cases = [
    (
        "CLARIFY",
        "Calculate a summary for customers.csv.",
    ),
    (
        "ABSTAIN",
        "Send customers.csv to my manager by email.",
    ),
]


for expected, task in cases:
    print("\n" + "=" * 50)
    print("Task:", task)

    result = run_agent(task)

    print("Expected:", expected)
    print("Actual:", result["decision"])

    print("\nExecuted tools:")
    for step in result["tool_history"]:
        print("-", step["tool"], step["arguments"])

    print("\nSkipped tools:")
    for step in result["skipped_calls"]:
        print("-", step["tool"], "->", step["reason"])

    print("\nDecision history:")
    for decision in result["decision_history"]:
        print(
            "-",
            decision["decision"],
            "->",
            decision["reason"],
        )

    print("\nAnswer:")
    print(result["answer"])
