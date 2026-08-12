from backend.tool_evaluator import evaluate_tool_call


task = (
    "In customers.csv, find duplicate customer IDs "
    "and tell me the average premium."
)

cases = [
    (
        "preview_rows",
        {
            "filename": "customers.csv",
            "limit": 5,
        },
    ),
    (
        "find_duplicates",
        {
            "filename": "customers.csv",
            "column": "customer_id",
        },
    ),
    (
        "calculate_summary",
        {
            "filename": "customers.csv",
            "column": "premium",
        },
    ),
]

for tool_name, arguments in cases:
    decision = evaluate_tool_call(
        task,
        tool_name,
        arguments,
        [],
    )

    print("\nTool:", tool_name)
    print("Action:", decision.action)
    print("Reason:", decision.reason)
