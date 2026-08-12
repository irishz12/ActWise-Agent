from backend.baseline_agent import run_baseline
from backend.graph_agent import run_graph_agent


task = (
    "In customers.csv, find duplicate customer IDs "
    "and tell me the average premium."
)


print("\nBASELINE")
baseline = run_baseline(task)

for index, step in enumerate(
    baseline["tool_history"],
    start=1,
):
    print(
        index,
        step["tool"],
        step["arguments"],
    )

print("Executed calls:", len(baseline["tool_history"]))


print("\nACTWISE")
actwise = run_graph_agent(
    task,
    thread_id="comparison-test-1",
)

for index, step in enumerate(
    actwise["tool_history"],
    start=1,
):
    print(
        index,
        step["tool"],
        step["arguments"],
    )

print("Executed calls:", len(actwise["tool_history"]))
print("Final decision:", actwise["decision"])
