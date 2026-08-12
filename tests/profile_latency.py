import time
from unittest.mock import patch

from backend.graph_agent import client, run_graph_agent


calls = []
original_create = client.chat.completions.create


def timed_create(*args, **kwargs):
    start = time.perf_counter()

    response = original_create(
        *args,
        **kwargs,
    )

    elapsed = time.perf_counter() - start

    if "tools" in kwargs:
        stage = "planner"
    elif "response_format" in kwargs:
        schema = (
            kwargs["response_format"]
            .get("json_schema", {})
            .get("name")
        )

        if schema == "tool_decision":
            stage = "tool_evaluator"
        elif schema == "agent_decision":
            stage = "decision"
        else:
            stage = "structured_output"
    else:
        stage = "final_answer"

    calls.append(
        {
            "stage": stage,
            "seconds": elapsed,
        }
    )

    return response


task = (
    "In customers.csv, find duplicate customer IDs "
    "and tell me the average premium."
)

start = time.perf_counter()

with patch.object(
    client.chat.completions,
    "create",
    side_effect=timed_create,
):
    result = run_graph_agent(
        task,
        thread_id="latency-profile-1",
    )

total = time.perf_counter() - start


print("\nFinal decision:", result["decision"])

print("\nLLM calls:")
for index, call in enumerate(calls, start=1):
    print(
        index,
        call["stage"],
        f'{call["seconds"]:.2f}s',
    )

print("\nBy stage:")

stages = {}

for call in calls:
    stages.setdefault(
        call["stage"],
        [],
    ).append(
        call["seconds"]
    )

for stage, values in stages.items():
    print(
        stage,
        "| calls:",
        len(values),
        "| total:",
        f"{sum(values):.2f}s",
    )

print("\nTotal LLM calls:", len(calls))
print("Total runtime:", f"{total:.2f}s")
