from backend.agent import run_agent


result = run_agent(
    "What files are available in my workspace?"
)

print("Tool called:", result["tool_called"])
print("Tool result:", result["tool_result"])
print("Answer:", result["answer"])
