from backend.agent import run_agent


result = run_agent(
    "How many rows are in customers.csv and what columns does it have?"
)

print("Tool history:")

for step in result["tool_history"]:
    print("Tool:", step["tool"])
    print("Arguments:", step["arguments"])
    print("Result:", step["result"])

print("Answer:", result["answer"])
