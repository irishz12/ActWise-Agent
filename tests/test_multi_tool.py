from backend.agent import run_agent


result = run_agent(
    "In customers.csv, find duplicate customer IDs and tell me the average premium."
)

print("\nTool history")

for index, step in enumerate(result["tool_history"], start=1):
    print(f"\nStep {index}")
    print("Tool:", step["tool"])
    print("Arguments:", step["arguments"])
    print("Result:", step["result"])

print("\nFinal answer:")
print(result["answer"])
