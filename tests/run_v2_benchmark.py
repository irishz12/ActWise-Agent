import json
import time
import uuid
from pathlib import Path

from backend.graph_agent import run_graph_agent


SCENARIO_FILE = Path("scenarios/evaluation_v2.json")
RESULT_FILE = Path("results/benchmark_v2.json")


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

    run_id = uuid.uuid4().hex[:8]

    rows = []

    for scenario in scenarios:
        scenario_id = scenario["id"]
        task = scenario["task"]
        expected = scenario["expected_decision"]
        required_tools = scenario.get(
            "required_tools",
            [],
        )

        print("\n" + "=" * 70)
        print(f"[{scenario_id}] {task}")

        start = time.perf_counter()

        try:
            result = run_graph_agent(
                task,
                thread_id=f"v2-{run_id}-{scenario_id}",
            )

            latency = time.perf_counter() - start

            executed = tool_names(
                result.get(
                    "tool_history",
                    [],
                )
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

            passed = (
                decision_correct
                and required_found
                and len(extra_tools) == 0
            )

            row = {
                "id": scenario_id,
                "category": scenario["category"],
                "task": task,

                "expected_decision": expected,
                "actual_decision": actual,

                "decision_correct": decision_correct,

                "required_tools": required_tools,
                "executed_tools": executed,
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

                "passed": passed,

                "answer": result.get("answer"),
                "error": None,
            }

            print("Expected:", expected)
            print("Actual:", actual)
            print("Required tools:", required_tools)
            print("Executed tools:", executed)
            print("Extra tools:", extra_tools)
            print(
                "Planning steps:",
                result.get("steps"),
            )
            print(
                "Latency:",
                f"{latency:.3f}s",
            )
            print(
                "Result:",
                "PASS" if passed else "FAIL",
            )

        except Exception as exc:
            latency = time.perf_counter() - start

            row = {
                "id": scenario_id,
                "category": scenario["category"],
                "task": task,

                "expected_decision": expected,
                "actual_decision": None,

                "decision_correct": False,

                "required_tools": required_tools,
                "executed_tools": [],
                "required_tools_found": False,

                "extra_tools": [],
                "extra_tool_count": 0,

                "planning_steps": 0,

                "latency_seconds": round(
                    latency,
                    4,
                ),

                "passed": False,

                "answer": None,
                "error": str(exc),
            }

            print("ERROR:", exc)
            print("Result: FAIL")

        rows.append(row)

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

    total = len(rows)

    passed = sum(
        row["passed"]
        for row in rows
    )

    decisions = sum(
        row["decision_correct"]
        for row in rows
    )

    required_success = sum(
        row["required_tools_found"]
        for row in rows
    )

    total_tools = sum(
        len(row["executed_tools"])
        for row in rows
    )

    extra_tools = sum(
        row["extra_tool_count"]
        for row in rows
    )

    average_latency = (
        sum(
            row["latency_seconds"]
            for row in rows
        )
        / total
    )

    categories = {}

    for row in rows:
        category = row["category"]

        if category not in categories:
            categories[category] = {
                "total": 0,
                "passed": 0,
            }

        categories[category]["total"] += 1

        if row["passed"]:
            categories[category]["passed"] += 1

    print("\n" + "=" * 70)
    print("ACTWISE V2 BENCHMARK SUMMARY")
    print("=" * 70)

    print(
        "Overall success:",
        f"{passed}/{total}",
        f"({passed / total * 100:.1f}%)",
    )

    print(
        "Decision accuracy:",
        f"{decisions}/{total}",
        f"({decisions / total * 100:.1f}%)",
    )

    print(
        "Required tools found:",
        f"{required_success}/{total}",
        f"({required_success / total * 100:.1f}%)",
    )

    print(
        "Executed tool calls:",
        total_tools,
    )

    print(
        "Extra tool calls:",
        extra_tools,
    )

    print(
        "Average latency:",
        f"{average_latency:.3f}s",
    )

    print("\nCATEGORY RESULTS")

    for category, stats in categories.items():
        percentage = (
            stats["passed"]
            / stats["total"]
            * 100
        )

        print(
            category,
            f"{stats['passed']}/{stats['total']}",
            f"({percentage:.1f}%)",
        )

    failures = [
        row
        for row in rows
        if not row["passed"]
    ]

    print("\nFAILURES:", len(failures))

    for row in failures:
        print(
            row["id"],
            "| expected:",
            row["expected_decision"],
            "| actual:",
            row["actual_decision"],
            "| required:",
            row["required_tools"],
            "| executed:",
            row["executed_tools"],
        )

    print(
        "\nSaved:",
        RESULT_FILE,
    )


if __name__ == "__main__":
    run()
