import time

from backend.graph_agent import run_graph_agent


CASES = [
    {
        "id": "F01",
        "task": "Which customer IDs occur more than once in customers.csv?",
        "expected_tool": "find_duplicates",
        "expected_decision": "COMPLETE",
    },
    {
        "id": "F02",
        "task": "Give me three sample records from customers.csv.",
        "expected_tool": "preview_rows",
        "expected_decision": "COMPLETE",
    },
    {
        "id": "F03",
        "task": "Which fields does customers.csv contain?",
        "expected_tool": "inspect_csv",
        "expected_decision": "COMPLETE",
    },
    {
        "id": "F04",
        "task": "Only show records whose city equals Kolkata in customers.csv.",
        "expected_tool": "filter_rows",
        "expected_decision": "COMPLETE",
    },
]


def run():
    passed = 0
    total_latency = 0
    total_steps = 0

    for case in CASES:
        start = time.perf_counter()

        result = run_graph_agent(
            case["task"],
            thread_id=f"fallback-benchmark-{case['id']}",
        )

        latency = time.perf_counter() - start
        total_latency += latency

        steps = result.get("steps", 0)
        total_steps += steps

        tools = [
            item.get("tool")
            for item in result.get("tool_history", [])
        ]

        tool_ok = case["expected_tool"] in tools
        decision_ok = (
            result.get("decision")
            == case["expected_decision"]
        )

        success = tool_ok and decision_ok

        if success:
            passed += 1

        print(f"\n[{case['id']}] {case['task']}")
        print("Tools:", tools)
        print("Decision:", result.get("decision"))
        print("Planning steps:", steps)
        print("Latency:", f"{latency:.3f}s")
        print("Result:", "PASS" if success else "FAIL")

    count = len(CASES)

    print("\n" + "=" * 60)
    print("FALLBACK BENCHMARK")
    print("=" * 60)

    print(
        "Success:",
        f"{passed}/{count}",
        f"({passed / count * 100:.1f}%)",
    )

    print(
        "Average planning steps:",
        f"{total_steps / count:.2f}",
    )

    print(
        "Average latency:",
        f"{total_latency / count:.3f}s",
    )


if __name__ == "__main__":
    run()
