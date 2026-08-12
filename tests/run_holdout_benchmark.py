import json
import time
import uuid
from pathlib import Path

from backend.graph_agent import run_graph_agent


SCENARIO_FILE = Path("scenarios/holdout_v1.json")
RESULT_FILE = Path("results/holdout_v1.json")


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
        print("\n" + "=" * 70)
        print(
            f"[{scenario['id']}]",
            scenario["task"],
        )

        start = time.perf_counter()

        try:
            result = run_graph_agent(
                scenario["task"],
                thread_id=(
                    f"holdout-{run_id}-"
                    f"{scenario['id']}"
                ),
            )

            latency = time.perf_counter() - start

            tools = get_tools(
                result.get("tool_history", [])
            )

            actual = result.get("decision")
            expected = scenario["expected_decision"]
            required = scenario.get(
                "required_tools",
                [],
            )

            decision_ok = actual == expected

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
                "id": scenario["id"],
                "category": scenario["category"],
                "task": scenario["task"],
                "expected_decision": expected,
                "actual_decision": actual,
                "required_tools": required,
                "executed_tools": tools,
                "decision_correct": decision_ok,
                "required_tools_found": required_ok,
                "extra_tools": extra,
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
            print("Latency:", f"{latency:.3f}s")
            print(
                "Result:",
                "PASS" if passed else "FAIL",
            )

        except Exception as exc:
            row = {
                "id": scenario["id"],
                "category": scenario["category"],
                "task": scenario["task"],
                "expected_decision": scenario[
                    "expected_decision"
                ],
                "actual_decision": None,
                "required_tools": scenario.get(
                    "required_tools",
                    [],
                ),
                "executed_tools": [],
                "decision_correct": False,
                "required_tools_found": False,
                "extra_tools": [],
                "latency_seconds": round(
                    time.perf_counter() - start,
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
    passed = sum(x["passed"] for x in rows)
    decision_ok = sum(
        x["decision_correct"]
        for x in rows
    )
    required_ok = sum(
        x["required_tools_found"]
        for x in rows
    )
    extra = sum(
        len(x["extra_tools"])
        for x in rows
    )
    avg_latency = sum(
        x["latency_seconds"]
        for x in rows
    ) / total

    print("\n" + "=" * 70)
    print("HOLDOUT V1 SUMMARY")
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

    print("Extra tool calls:", extra)

    print(
        "Average latency:",
        f"{avg_latency:.3f}s",
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

    print("\nSaved:", RESULT_FILE)


if __name__ == "__main__":
    run()
