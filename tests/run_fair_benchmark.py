import json
import time
from pathlib import Path

from backend.baseline_20b import run_baseline
from backend.graph_agent import run_graph_agent


SCENARIO_FILE = Path("scenarios/evaluation_v1.json")
RESULT_FILE = Path("results/fair_benchmark_v1.json")


def get_tools(history):
    return [
        item.get("tool")
        for item in history
        if item.get("tool")
    ]


def count_extra(tools, required):
    return sum(
        1
        for tool in tools
        if tool not in required
    )


def run():
    scenarios = json.loads(
        SCENARIO_FILE.read_text()
    )

    scenarios = [
        scenario
        for scenario in scenarios
        if scenario["expected_decision"] == "COMPLETE"
    ]

    rows = []

    for scenario in scenarios:
        scenario_id = scenario["id"]
        task = scenario["task"]
        required = scenario.get(
            "required_tools",
            [],
        )

        print(
            f"\n[{scenario_id}] {task}"
        )

        baseline_start = time.perf_counter()

        baseline = run_baseline(task)

        baseline_latency = (
            time.perf_counter()
            - baseline_start
        )

        actwise_start = time.perf_counter()

        actwise = run_graph_agent(
            task,
            thread_id=f"fair-{scenario_id}",
        )

        actwise_latency = (
            time.perf_counter()
            - actwise_start
        )

        baseline_tools = get_tools(
            baseline.get(
                "tool_history",
                [],
            )
        )

        actwise_tools = get_tools(
            actwise.get(
                "tool_history",
                [],
            )
        )

        baseline_required = all(
            tool in baseline_tools
            for tool in required
        )

        actwise_required = all(
            tool in actwise_tools
            for tool in required
        )

        row = {
            "id": scenario_id,
            "task": task,
            "required_tools": required,

            "baseline_tools": baseline_tools,
            "actwise_tools": actwise_tools,

            "baseline_tool_calls": len(
                baseline_tools
            ),
            "actwise_tool_calls": len(
                actwise_tools
            ),

            "baseline_extra_tools": count_extra(
                baseline_tools,
                required,
            ),
            "actwise_extra_tools": count_extra(
                actwise_tools,
                required,
            ),

            "baseline_required_tools_found": baseline_required,
            "actwise_required_tools_found": actwise_required,

            "baseline_latency": round(
                baseline_latency,
                4,
            ),
            "actwise_latency": round(
                actwise_latency,
                4,
            ),

            "actwise_decision": actwise.get(
                "decision"
            ),
        }

        rows.append(row)

        print(
            "Baseline:",
            baseline_tools,
            f"{baseline_latency:.3f}s",
        )

        print(
            "ActWise: ",
            actwise_tools,
            "->",
            actwise.get("decision"),
            f"{actwise_latency:.3f}s",
        )

    RESULT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_FILE.write_text(
        json.dumps(
            rows,
            indent=2,
        )
    )

    baseline_calls = sum(
        row["baseline_tool_calls"]
        for row in rows
    )

    actwise_calls = sum(
        row["actwise_tool_calls"]
        for row in rows
    )

    baseline_extra = sum(
        row["baseline_extra_tools"]
        for row in rows
    )

    actwise_extra = sum(
        row["actwise_extra_tools"]
        for row in rows
    )

    baseline_latency = sum(
        row["baseline_latency"]
        for row in rows
    ) / len(rows)

    actwise_latency = sum(
        row["actwise_latency"]
        for row in rows
    ) / len(rows)

    baseline_success = sum(
        row["baseline_required_tools_found"]
        for row in rows
    )

    actwise_success = sum(
        row["actwise_required_tools_found"]
        for row in rows
    )

    saved = baseline_calls - actwise_calls

    reduction = (
        saved / baseline_calls * 100
        if baseline_calls
        else 0
    )

    print("\n" + "=" * 60)
    print("FAIR 20B BENCHMARK")
    print("=" * 60)

    print("Scenarios:", len(rows))

    print(
        "Baseline required-tool success:",
        f"{baseline_success}/{len(rows)}",
    )

    print(
        "ActWise required-tool success:",
        f"{actwise_success}/{len(rows)}",
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
        saved,
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
        f"{baseline_latency:.3f}s",
    )

    print(
        "Average ActWise latency:",
        f"{actwise_latency:.3f}s",
    )

    print(
        "\nSaved:",
        RESULT_FILE,
    )


if __name__ == "__main__":
    run()
