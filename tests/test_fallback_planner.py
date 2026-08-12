from backend.graph_agent import run_graph_agent


cases = [
    {
        "task": "Which customer IDs occur more than once in customers.csv?",
        "expected_tool": "find_duplicates",
    },
    {
        "task": "Give me three sample records from customers.csv.",
        "expected_tool": "preview_rows",
    },
    {
        "task": "Which fields does customers.csv contain?",
        "expected_tool": "inspect_csv",
    },
    {
        "task": "Only show records whose city equals Kolkata in customers.csv.",
        "expected_tool": "filter_rows",
    },
]


for index, case in enumerate(cases, start=1):
    print("\n" + "=" * 60)
    print("Task:", case["task"])

    result = run_graph_agent(
        case["task"],
        thread_id=f"fallback-test-{index}",
    )

    tools = [
        item.get("tool")
        for item in result.get("tool_history", [])
    ]

    print("Expected tool:", case["expected_tool"])
    print("Executed tools:", tools)
    print("Decision:", result.get("decision"))
    print("Planning steps:", result.get("steps"))
    print("Answer:")
    print(result.get("answer"))

    passed = case["expected_tool"] in tools

    print(
        "Result:",
        "PASS" if passed else "FAIL",
    )
