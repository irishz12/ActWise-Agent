from backend.llm import ask_model


response = ask_model(
    "Reply with only this exact text: ActWise API is working"
)

print(response)
