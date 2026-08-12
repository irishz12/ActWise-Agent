from backend.guards import (
    should_skip_tool,
    tool_signature,
)


first = tool_signature(
    "filter_rows",
    {
        "filename": "customers.csv",
        "column": "city",
        "value": "Kolkata",
    },
)

second = tool_signature(
    "filter_rows",
    {
        "filename": "customers.csv",
        "column": "city",
        "value": "kolkata",
    },
)

print("Equivalent filter calls:", first == second)


cases = [
    (
        "calculate_summary",
        {
            "filename": "customers.csv",
            "column": "premium",
        },
        "What is the average premium in customers.csv?",
    ),
    (
        "calculate_summary",
        {
            "filename": "customers.csv",
            "column": "premium",
        },
        "Calculate a summary for customers.csv.",
    ),
    (
        "create_report",
        {
            "filename": "customers.csv",
        },
        "Calculate a summary for customers.csv.",
    ),
    (
        "create_report",
        {
            "filename": "customers.csv",
        },
        "Create a report for customers.csv.",
    ),
]


for tool, arguments, task in cases:
    skip, reason = should_skip_tool(
        tool,
        arguments,
        task,
    )

    print()
    print("Task:", task)
    print("Tool:", tool)
    print("Skip:", skip)
    print("Reason:", reason)
