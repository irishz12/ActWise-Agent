from backend.fast_planner import build_direct_plan


cases = [
    "In customers.csv, find duplicate customer IDs and tell me the average premium.",
    "What is the average premium in customers.csv?",
    "Show me all customers from Kolkata in customers.csv.",
    "Show me the first 3 rows of customers.csv.",
    "What columns are available in customers.csv?",
    "Calculate a summary for customers.csv.",
]

for task in cases:
    print("\nTask:", task)

    plan = build_direct_plan(task)

    for call in plan or []:
        print(
            "-",
            call["tool"],
            call["arguments"],
        )
