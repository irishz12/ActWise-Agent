from backend.graph_agent import graph, run_graph_agent


thread_id = "checkpoint-test-1"

result = run_graph_agent(
    "In customers.csv, find duplicate customer IDs.",
    thread_id=thread_id,
)

config = {
    "configurable": {
        "thread_id": thread_id,
    }
}

saved_state = graph.get_state(config)

print("Decision:", result["decision"])
print("Thread ID:", thread_id)
print("Saved decision:", saved_state.values.get("decision"))
print(
    "Saved tool calls:",
    len(saved_state.values.get("tool_history", [])),
)
print("Checkpoint exists:", saved_state.config is not None)
