import json
import time
import uuid
from pathlib import Path

from backend.graph_agent import run_graph_agent


SCENARIO_FILE = Path("scenarios/holdout_v3.json")
RESULT_FILE = Path("results/holdout_v3.json")


def get_tools(history):
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
        required = scenario.get(
            "required_tools",
            [],
        )

        print("\n" + "=" * 70)
        print(f"[{scenario_id}] {task}")

        start = time.perf_counter()

        try:
            result = run_graph_agent(
                task,
                thread_id=(
                    f"holdout-v3-"
                    f"{run_id}-{scenario_id}"
                ),
            )

            latency = (
                time.perf_counter()
                - start
            )

            tools = get_tools(
                result.get(
                    "tool_history",
                    [],
                )
            )

            actual = result.get(
                "decision"
            )

            decision_ok = (
                actual == expected
            )

            required_ok = all(
                tool in tools
                for tool in required
            )

            extra = [
                tool
                for tool in tools
                if tool not in required
            ]

            passed = (
                decision_ok
                and required_ok
                and not extra
            )

            row = {
                "id": scenario_id,
                "category": scenario["category"],
                "task": task,
                "expected_decision": expected,
                "actual_decision": actual,
                "required_tools": required,
                "executed_tools": tools,
                "decision_correct": decision_ok,
                "required_tools_found": required_ok,
                "extra_tools": extra,
                "planning_steps": result.get(
                    "steps",
                    0,
                ),
                "latency_seconds": round(
                    latency,
                    4,
                ),
                "passed": passed,
            }

            print("Expected:", expected)
            print("Actual:", actual)
            print("Required:", required)
            print("Executed:", tools)
            print("Extra:", extra)
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
            latency = (
                time.perf_counter()
                - start
            )

            row = {
                "id": scenario_id,
                "category": scenario["category"],
                "task": task,
                "expected_decision": expected,
                "actual_decision": None,
                "required_tools": required,
                "executed_tools": [],
                "decision_correct": False,
                "required_tools_found": False,
                "extra_tools": [],
                "planning_steps": 0,
                "latency_seconds": round(
                    latency,
                    4,
                ),
                "passed": False,
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

    decision_ok = sum(
        row["decision_correct"]
        for row in rows
    )

    required_ok = sum(
        row["required_tools_found"]
        for row in rows
    )

    extra_calls = sum(
        len(row["extra_tools"])
        for row in rows
    )

    avg_latency = sum(
        row["latency_seconds"]
        for row in rows
    ) / total

    categories = {}

    for row in rows:
        category = row["category"]

        if category not in categories:
            categories[category] = {
                "passed": 0,
                "total": 0,
            }

        categories[category]["total"] += 1

        if row["passed"]:
            categories[category]["passed"] += 1

    print("\n" + "=" * 70)
    print("HOLDOUT V3 SUMMARY")
    print("=" * 70)

    print(
        "Overall success:",
        f"{passed}/{total}",
        f"({passed / total * 100:.1f}%)",
    )

    print(
        "Decision accuracy:",
        f"{decision_ok}/{total}",
        f"({decision_ok / total * 100:.1f}%)",
    )

    print(
        "Required tools found:",
        f"{required_ok}/{total}",
        f"({required_ok / total * 100:.1f}%)",
    )

    print(
        "Extra tool calls:",
        extra_calls,
    )

    print(
        "Average latency:",
        f"{avg_latency:.3f}s",
    )

    print("\nCATEGORY RESULTS")

    for category, stats in categories.items():
        score = (
            stats["passed"]
            / stats["total"]
            * 100
        )

        print(
            category,
            f"{stats['passed']}/{stats['total']}",
            f"({score:.1f}%)",
        )

    print("\nFAILURES")

    for row in rows:
        if not row["passed"]:
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
