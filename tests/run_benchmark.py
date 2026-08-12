import csv
import json
import time
from pathlib import Path
from uuid import uuid4

from backend.baseline_agent import run_baseline
from backend.graph_agent import run_graph_agent


SCENARIO_FILE = Path("scenarios/evaluation_v1.json")
RESULTS_DIR = Path("results")


def tool_names(history):
    return [
        step["tool"]
        for step in history
    ]


def required_tools_found(history, required_tools):
    actual = set(tool_names(history))
    return all(
        tool in actual
        for tool in required_tools
    )


def extra_tool_count(history, required_tools):
    required = set(required_tools)

    return sum(
        1
        for tool in tool_names(history)
        if tool not in required
    )


def run():
    scenarios = json.loads(
        SCENARIO_FILE.read_text()
    )

    RESULTS_DIR.mkdir(exist_ok=True)

    rows = []

    for scenario in scenarios:
        print(
            f'\n[{scenario["id"]}] '
            f'{scenario["task"]}'
        )

        start = time.perf_counter()
        baseline = run_baseline(
            scenario["task"]
        )
        baseline_latency = time.perf_counter() - start

        start = time.perf_counter()
        actwise = run_graph_agent(
            scenario["task"],
            thread_id=f'benchmark-{scenario["id"]}-{uuid4()}',
        )
        actwise_latency = time.perf_counter() - start

        baseline_tools = baseline["tool_history"]
        actwise_tools = actwise.get(
            "tool_history",
            [],
        )

        row = {
            "id": scenario["id"],
            "task": scenario["task"],
            "expected_decision": scenario["expected_decision"],
            "actwise_decision": actwise.get("decision"),
            "decision_correct": (
                actwise.get("decision")
                == scenario["expected_decision"]
            ),
            "baseline_tool_calls": len(baseline_tools),
            "actwise_tool_calls": len(actwise_tools),
            "tool_calls_saved": (
                len(baseline_tools)
                - len(actwise_tools)
            ),
            "baseline_extra_tools": extra_tool_count(
                baseline_tools,
                scenario["required_tools"],
            ),
            "actwise_extra_tools": extra_tool_count(
                actwise_tools,
                scenario["required_tools"],
            ),
            "baseline_required_tools_found": required_tools_found(
                baseline_tools,
                scenario["required_tools"],
            ),
            "actwise_required_tools_found": required_tools_found(
                actwise_tools,
                scenario["required_tools"],
            ),
            "baseline_latency_seconds": round(
                baseline_latency,
                3,
            ),
            "actwise_latency_seconds": round(
                actwise_latency,
                3,
            ),
            "baseline_tools": tool_names(
                baseline_tools
            ),
            "actwise_tools": tool_names(
                actwise_tools
            ),
            "skipped_calls": len(
                actwise.get(
                    "skipped_calls",
                    [],
                )
            ),
        }

        rows.append(row)

        print(
            "Baseline:",
            row["baseline_tool_calls"],
            row["baseline_tools"],
        )

        print(
            "ActWise: ",
            row["actwise_tool_calls"],
            row["actwise_tools"],
            "->",
            row["actwise_decision"],
        )

    json_path = RESULTS_DIR / "benchmark_v1.json"
    json_path.write_text(
        json.dumps(
            rows,
            indent=2,
        )
    )

    csv_path = RESULTS_DIR / "benchmark_v1.csv"

    csv_fields = [
        "id",
        "task",
        "expected_decision",
        "actwise_decision",
        "decision_correct",
        "baseline_tool_calls",
        "actwise_tool_calls",
        "tool_calls_saved",
        "baseline_extra_tools",
        "actwise_extra_tools",
        "baseline_required_tools_found",
        "actwise_required_tools_found",
        "baseline_latency_seconds",
        "actwise_latency_seconds",
        "skipped_calls",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=csv_fields,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    field: row[field]
                    for field in csv_fields
                }
            )

    total = len(rows)

    correct_decisions = sum(
        row["decision_correct"]
        for row in rows
    )

    baseline_calls = sum(
        row["baseline_tool_calls"]
        for row in rows
    )

    actwise_calls = sum(
        row["actwise_tool_calls"]
        for row in rows
    )

    saved_calls = baseline_calls - actwise_calls

    if baseline_calls:
        reduction = (
            saved_calls
            / baseline_calls
            * 100
        )
    else:
        reduction = 0

    baseline_extra = sum(
        row["baseline_extra_tools"]
        for row in rows
    )

    actwise_extra = sum(
        row["actwise_extra_tools"]
        for row in rows
    )

    baseline_latency = sum(
        row["baseline_latency_seconds"]
        for row in rows
    ) / total

    actwise_latency = sum(
        row["actwise_latency_seconds"]
        for row in rows
    ) / total

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    print(
        f"Scenarios: {total}"
    )

    print(
        "Decision accuracy:",
        f"{correct_decisions}/{total}",
        f"({correct_decisions / total * 100:.1f}%)",
    )

    print(
        "Baseline tool calls:",
        baseline_calls,
    )

    print(
        "ActWise tool calls:",
        actwise_calls,
    )

    print(
        "Tool calls saved:",
        saved_calls,
    )

    print(
        "Tool-call reduction:",
        f"{reduction:.1f}%",
    )

    print(
        "Baseline extra tools:",
        baseline_extra,
    )

    print(
        "ActWise extra tools:",
        actwise_extra,
    )

    print(
        "Average baseline latency:",
        f"{baseline_latency:.2f}s",
    )

    print(
        "Average ActWise latency:",
        f"{actwise_latency:.2f}s",
    )

    print("\nSaved:")
    print("-", json_path)
    print("-", csv_path)


if __name__ == "__main__":
    run()
