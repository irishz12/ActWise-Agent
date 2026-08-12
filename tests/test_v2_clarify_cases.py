import uuid

from backend.graph_agent import run_graph_agent


run_id = uuid.uuid4().hex[:8]


cases = [
    "What is the average in customers.csv?",
    "Calculate the total in customers.csv.",
    "Filter customers.csv.",
    "Find duplicates in customers.csv.",
]


for index, task in enumerate(cases, start=1):
    print("\n" + "=" * 60)
    print("Task:", task)

    result = run_graph_agent(
        task,
        thread_id=f"v2-clarify-fix-{run_id}-{index}",
    )

    tools = [
        item.get("tool")
        for item in result.get(
            "tool_history",
            [],
        )
    ]

    print("Decision:", result.get("decision"))
    print("Tools:", tools)
    print("Answer:", result.get("answer"))
