import json

from backend.agent import (
    MODEL,
    TOOLS,
    run_tool,
)
from backend.llm import client


MAX_STEPS = 6


def run_baseline(user_message):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a data assistant. "
                "Use the available tools to complete the user's task. "
                "Do not invent files, columns, values, or tools."
            ),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    tool_history = []

    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return {
                "tool_history": tool_history,
                "answer": message.content,
                "steps": len(tool_history),
            }

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments or "{}"
                )
            except json.JSONDecodeError:
                arguments = {}

            result = run_tool(
                tool_name,
                arguments,
            )

            tool_history.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result,
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

    return {
        "tool_history": tool_history,
        "answer": "Maximum tool steps reached.",
        "steps": len(tool_history),
    }
