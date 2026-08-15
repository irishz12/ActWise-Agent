import json
import time
import uuid
from pathlib import Path

from backend.graph_agent import run_graph_agent


SCENARIO_FILE = Path("scenarios/agentic_holdout_v1.json")
RESULT_FILE = Path("results/agentic_holdout_v1_results.json")


def normalize(value):
    return str(value).strip().lower()


def tool_names(history):
    return [
        item.get("tool")
        for item in history
        if item.get("tool")
    ]


def required_call_satisfied(spec, history):
    """A required tool call is satisfied if some executed entry matches
    the tool name and, when arguments are specified, each specified
    argument key/value is present (case/whitespace-insensitive) on that
    entry -- extra arguments on the actual call are ignored."""
    tool = spec["tool"]
    expected_args = spec.get("arguments", {})

    for entry in history:
        if entry.get("tool") != tool:
            continue

        actual_args = entry.get("arguments", {}) or {}

        if all(
            key in actual_args
            and normalize(actual_args[key]) == normalize(value)
            for key, value in expected_args.items()
        ):
            return True

    return False


def evaluate(scenario, result, latency):
    history = result.get("tool_history", [])
    executed = tool_names(history)
    actual_decision = result.get("decision")
    expected_decision = scenario["expected_decision"]

    decision_correct = actual_decision == expected_decision

    required_specs = scenario.get("required_tool_calls", [])
    required_results = [
        required_call_satisfied(spec, history)
        for spec in required_specs
    ]
    required_met = all(required_results)

    allowed = set(scenario.get("allowed_optional_tools", []))
    required_tool_names = {spec["tool"] for spec in required_specs}
    forbidden = set(scenario.get("forbidden_tools", []))

    forbidden_hit = [
        tool
        for tool in executed
        if tool in forbidden
    ]

    unnecessary = [
        tool
        for tool in executed
        if tool not in required_tool_names
        and tool not in allowed
    ]

    passed = (
        decision_correct
        and required_met
        and not forbidden_hit
    )

    return {
        "id": scenario["id"],
        "category": scenario["category"],
        "task": scenario["task"],
        "expected_decision": expected_decision,
        "actual_decision": actual_decision,
        "decision_correct": decision_correct,
        "required_tool_calls": required_specs,
        "required_tools_met": required_met,
        "executed_tools": executed,
        "forbidden_tools_hit": forbidden_hit,
        "unnecessary_tools": unnecessary,
        "planning_steps": result.get("steps", 0),
        "latency_seconds": round(latency, 4),
        "passed": passed,
        "answer": result.get("answer"),
        "error": None,
    }


def run():
    scenarios = json.loads(SCENARIO_FILE.read_text())
    run_id = uuid.uuid4().hex[:8]
    rows = []

    for scenario in scenarios:
        scenario_id = scenario["id"]
        task = scenario["task"]

        print("\n" + "=" * 70)
        print(f"[{scenario_id}] {task}")

        start = time.perf_counter()

        try:
            result = run_graph_agent(
                task,
                thread_id=f"agentic-holdout-v1-{run_id}-{scenario_id}",
            )
            latency = time.perf_counter() - start

            row = evaluate(scenario, result, latency)

            print("Expected:", row["expected_decision"])
            print("Actual:", row["actual_decision"])
            print("Required tool calls met:", row["required_tools_met"])
            print("Executed tools:", row["executed_tools"])
            print("Forbidden tools hit:", row["forbidden_tools_hit"])
            print("Unnecessary tools:", row["unnecessary_tools"])
            print("Planning steps:", row["planning_steps"])
            print("Latency:", f"{latency:.3f}s")
            print("Result:", "PASS" if row["passed"] else "FAIL")

        except Exception as exc:
            latency = time.perf_counter() - start

            row = {
                "id": scenario_id,
                "category": scenario["category"],
                "task": task,
                "expected_decision": scenario["expected_decision"],
                "actual_decision": None,
                "decision_correct": False,
                "required_tool_calls": scenario.get("required_tool_calls", []),
                "required_tools_met": False,
                "executed_tools": [],
                "forbidden_tools_hit": [],
                "unnecessary_tools": [],
                "planning_steps": 0,
                "latency_seconds": round(latency, 4),
                "passed": False,
                "answer": None,
                "error": str(exc),
            }

            print("ERROR:", exc)
            print("Result: FAIL")

        rows.append(row)

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(json.dumps(rows, indent=2))

    total = len(rows)
    passed = sum(row["passed"] for row in rows)
    decisions_correct = sum(row["decision_correct"] for row in rows)
    required_met = sum(row["required_tools_met"] for row in rows)
    unnecessary_total = sum(len(row["unnecessary_tools"]) for row in rows)
    avg_steps = sum(row["planning_steps"] for row in rows) / total
    avg_latency = sum(row["latency_seconds"] for row in rows) / total

    def decision_accuracy(label):
        subset = [row for row in rows if row["expected_decision"] == label]
        if not subset:
            return None
        correct = sum(row["decision_correct"] for row in subset)
        return correct, len(subset)

    categories = {}
    for row in rows:
        category = row["category"]
        categories.setdefault(category, {"total": 0, "passed": 0})
        categories[category]["total"] += 1
        if row["passed"]:
            categories[category]["passed"] += 1

    print("\n" + "=" * 70)
    print("AGENTIC HOLDOUT V1 SUMMARY")
    print("=" * 70)

    print("Scenarios:", total)
    print(
        "Task success:",
        f"{passed}/{total}",
        f"({passed / total * 100:.1f}%)",
    )
    print(
        "Decision accuracy:",
        f"{decisions_correct}/{total}",
        f"({decisions_correct / total * 100:.1f}%)",
    )
    print(
        "Required-tool coverage:",
        f"{required_met}/{total}",
        f"({required_met / total * 100:.1f}%)",
    )
    print(
        "Unnecessary tool calls:",
        unnecessary_total,
        f"({unnecessary_total / total:.2f} per scenario)",
    )
    print("Average agent steps:", f"{avg_steps:.2f}")
    print("Average latency:", f"{avg_latency:.3f}s")

    for label in ("COMPLETE", "CLARIFY", "ABSTAIN"):
        stats = decision_accuracy(label)
        if stats:
            correct, count = stats
            print(
                f"{label} accuracy:",
                f"{correct}/{count}",
                f"({correct / count * 100:.1f}%)",
            )

    print("\nCATEGORY RESULTS")
    for category, stats in categories.items():
        pct = stats["passed"] / stats["total"] * 100
        print(category, f"{stats['passed']}/{stats['total']}", f"({pct:.1f}%)")

    failures = [row for row in rows if not row["passed"]]
    print("\nFAILURES:", len(failures))
    for row in failures:
        print(
            row["id"],
            "| expected:", row["expected_decision"],
            "| actual:", row["actual_decision"],
            "| required_met:", row["required_tools_met"],
            "| forbidden_hit:", row["forbidden_tools_hit"],
            "| executed:", row["executed_tools"],
        )

    print("\nSaved:", RESULT_FILE)


if __name__ == "__main__":
    run()
