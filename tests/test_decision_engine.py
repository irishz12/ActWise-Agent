from backend.decision_engine import evaluate_decision


task = "Send customers.csv to my manager by email."

observations = [
    {
        "tool": "list_files",
        "result": [
            "customers.csv",
            "customer_report.txt",
        ],
    }
]

decision = evaluate_decision(task, observations)

print("Decision:", decision.decision)
print("Reason:", decision.reason)
