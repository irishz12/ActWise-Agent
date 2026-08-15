import json

from backend.llm import MODEL, client


def chat_smoke_test():
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Reply with only this exact text: "
                    "ActWise Mantle chat is working"
                ),
            }
        ],
        temperature=0,
        max_tokens=50,
    )

    content = response.choices[0].message.content
    print("CHAT RESPONSE:", content)

    assert content, "chat completion returned empty content"
    print("chat smoke test: PASS")


TEST_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}


def tool_call_smoke_test():
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": "What is the weather in Mumbai?",
            }
        ],
        tools=[TEST_TOOL],
        tool_choice="auto",
        temperature=0,
    )

    message = response.choices[0].message
    tool_calls = message.tool_calls or []

    print("TOOL CALLS:", tool_calls)

    assert tool_calls, "model did not request the tool call"

    call = tool_calls[0]
    assert call.function.name == "get_weather"

    arguments = json.loads(call.function.arguments or "{}")
    assert "city" in arguments

    print("tool-calling smoke test: PASS")


if __name__ == "__main__":
    chat_smoke_test()
    tool_call_smoke_test()
