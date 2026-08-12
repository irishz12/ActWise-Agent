from backend.guards import should_skip_tool


cases = [
    (
        "inspect_csv",
        {"filename": "customers.csv"},
        "Find duplicate customer IDs and average premium in customers.csv",
    ),
    (
        "inspect_csv",
        {"filename": "customers.csv"},
        "What columns are in customers.csv?",
    ),
]

for tool, arguments, message in cases:
    skip, reason = should_skip_tool(
        tool,
        arguments,
        message,
    )

    print(message)
    print("Skip:", skip)
    print("Reason:", reason)
    print()
