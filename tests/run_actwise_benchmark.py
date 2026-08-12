import json
import time
from pathlib import Path

from backend.graph_agent import run_graph_agent


SCENARIO_FILE = Path("scenarios/evaluation_v1.json")
RESULT_FILE = Path("results/actwise_benchmark_v1.json")


def tool_names(history):
    return [
        item.get("tool")
        for item in history
        if item.get("tool")
    ]


def run():
    scenarios = json.loads(
        SCENARIO_FILE.read_text()
    )

    rows = []

    for scenario in scenarios:
        scenario_id = scenario["id"]
        task = scenario["task"]
        expected = scenario["expected_decision"]
        required_tools = scenario.get(
            "required_tools",
            [],
        )

        print(
            f"\n[{scenario_id}] {task}"
        )

        start = time.perf_counter()

        result = run_graph_agent(
            task,
            thread_id=f"actwise-{scenario_id}",
        )

        latency = time.perf_counter() - start

        executed = tool_names(
            result.get("tool_history", [])
        )

        actual = result.get("decision")

        decision_correct = (
            actual == expected
        )

        required_found = all(
            tool in executed
            for tool in required_tools
        )

        extra_tools = [
            tool
            for tool in executed
            if tool not in required_tools
        ]

        row = {
            "id": scenario_id,
            "task": task,
            "expected_decision": expected,
            "actual_decision": actual,
            "decision_correct": decision_correct,
            "executed_tools": executed,
            "required_tools": required_tools,
            "required_tools_found": required_found,
            "extra_tools": extra_tools,
            "extra_tool_count": len(extra_tools),
            "planning_steps": result.get(
                "steps",
                0,
            ),
            "latency_seconds": round(
                latency,
                4,
            ),
        }

        rows.append(row)

        print(
            "ActWise:",
            len(executed),
            executed,
            "->",
            actual,
            f"({latency:.3f}s)",
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

    correct = sum(
        row["decision_correct"]
        for row in rows
    )

    total_calls = sum(
        len(row["executed_tools"])
        for row in rows
    )

    extra_calls = sum(
        row["extra_tool_count"]
        for row in rows
    )

    required_success = sum(
        row["required_tools_found"]
        for row in rows
    )

    average_latency = (
        sum(
            row["latency_seconds"]
            for row in rows
        )
        / len(rows)
    )

    print("\n" + "=" * 60)
    print("ACTWISE BENCHMARK SUMMARY")
    print("=" * 60)

    print("Scenarios:", len(rows))

    print(
        "Decision accuracy:",
        f"{correct}/{len(rows)}",
        f"({correct / len(rows) * 100:.1f}%)",
    )

    print(
        "Required tools found:",
        f"{required_success}/{len(rows)}",
    )

    print(
        "Executed tool calls:",
        total_calls,
    )

    print(
        "Extra tool calls:",
        extra_calls,
    )

    print(
        "Average latency:",
        f"{average_latency:.3f}s",
    )

    print(
        "\nSaved:",
        RESULT_FILE,
    )


if __name__ == "__main__":
    run()
