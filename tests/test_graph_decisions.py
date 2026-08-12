from backend.graph_agent import run_graph_agent


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
    print("\n" + "=" * 55)
    print("Task:", task)

    result = run_graph_agent(task)

    print("Expected:", expected)
    print("Actual:", result["decision"])
    print("Planning steps:", result["steps"])

    print("\nExecuted tools:")
    for step in result["tool_history"]:
        print("-", step["tool"], step["arguments"])

    print("\nSkipped tools:")
    for step in result["skipped_calls"]:
        print("-", step["tool"], "->", step["reason"])

    print("\nDecision history:")
    for step in result["decision_history"]:
        print(
            "-",
            step["decision"],
            "->",
            step["reason"],
        )

    print("\nAnswer:")
    print(result["answer"])
