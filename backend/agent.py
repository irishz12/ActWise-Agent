import json

from backend.decision_engine import evaluate_decision
from backend.guards import should_skip_tool, tool_signature
from backend.llm import client
from backend.state import AgentState
from backend.tool_evaluator import evaluate_tool_call
from backend.tools import (
    calculate_summary,
    create_report,
    filter_rows,
    find_duplicates,
    inspect_csv,
    list_files,
    preview_rows,
)


MODEL = "openai/gpt-oss-120b"
MAX_TOOL_STEPS = 6
MAX_NO_PROGRESS = 2

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files available in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_csv",
            "description": "Inspect a CSV file when its columns or structure are unknown. Do not use it when the user already identifies the fields needed for the task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                },
                "required": ["filename"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preview_rows",
            "description": "Preview the first few rows of a CSV file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["filename"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_duplicates",
            "description": "Find duplicate values in a CSV column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "column": {"type": "string"},
                },
                "required": ["filename"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_summary",
            "description": "Calculate count, average, total, minimum and maximum for a numeric CSV column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "column": {"type": "string"},
                },
                "required": ["filename", "column"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_rows",
            "description": "Find CSV rows where a column matches a value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "column": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["filename", "column", "value"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_report",
            "description": "Create a simple text report for a CSV file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "report_name": {"type": "string"},
                },
                "required": ["filename"],
                "additionalProperties": False,
            },
        },
    },
]

TOOL_HANDLERS = {
    "list_files": list_files,
    "inspect_csv": inspect_csv,
    "preview_rows": preview_rows,
    "find_duplicates": find_duplicates,
    "calculate_summary": calculate_summary,
    "filter_rows": filter_rows,
    "create_report": create_report,
}


def run_tool(name, arguments):
    handler = TOOL_HANDLERS.get(name)

    if handler is None:
        return {
            "success": False,
            "error": "unknown_tool",
            "tool": name,
        }

    try:
        return handler(**arguments)
    except TypeError as error:
        return {
            "success": False,
            "error": "invalid_arguments",
            "detail": str(error),
        }


def build_final_answer(user_task, observations):
    context = {
        "task": user_task,
        "observations": observations,
    }

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the user's task using only the provided observations. "
                    "Do not invent values, units, currencies, or facts. "
                    "Keep the answer clear and concise."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context),
            },
        ],
        temperature=0,
        max_tokens=500,
    )

    return response.choices[0].message.content


def run_agent(user_message):
    state: AgentState = {
        "user_message": user_message,
        "tool_history": [],
        "decision_history": [],
        "skipped_calls": [],
        "decision": None,
        "answer": None,
        "no_progress": 0,
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are ActWise, a data assistant. "
                "Use only the tools provided to you. "
                "Choose the smallest set of tools needed to complete the task. "
                "If the user already provides a filename, do not list files first. "
                "If the user clearly identifies the fields needed for an operation, "
                "call the operation tool directly instead of inspecting the CSV first. "
                "Use inspect_csv only when the file structure or required column names "
                "are genuinely unknown. "
                "Do not invent files, columns, values, or tool names."
            ),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    seen_calls = set()

    for _ in range(MAX_TOOL_STEPS):
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
            decision = evaluate_decision(
                state["user_message"],
                state["tool_history"],
            )

            state["decision_history"].append(
                decision.model_dump()
            )

            if decision.decision == "COMPLETE":
                state["decision"] = "COMPLETE"
                state["answer"] = message.content
                return state

            if decision.decision in {"CLARIFY", "ABSTAIN"}:
                state["decision"] = decision.decision
                state["answer"] = decision.reason
                return state

            state["no_progress"] += 1

            if state["no_progress"] >= MAX_NO_PROGRESS:
                state["decision"] = "ABSTAIN"
                state["answer"] = (
                    "The agent could not find a useful next action."
                )
                return state

            continue

        ran_tool = False
        repeated_call = False

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name

            try:
                tool_args = json.loads(
                    tool_call.function.arguments or "{}"
                )
            except json.JSONDecodeError:
                tool_args = {}

            signature = tool_signature(
                tool_name,
                tool_args,
            )

            was_seen = signature in seen_calls

            skip, reason = should_skip_tool(
                tool_name,
                tool_args,
                state["user_message"],
                seen_calls,
            )

            seen_calls.add(signature)

            if skip:
                if was_seen:
                    repeated_call = True
                state["skipped_calls"].append(
                    {
                        "tool": tool_name,
                        "arguments": tool_args,
                        "reason": reason,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            {
                                "skipped": True,
                                "reason": reason,
                            }
                        ),
                    }
                )
                continue

            tool_decision = evaluate_tool_call(
                state["user_message"],
                tool_name,
                tool_args,
                state["tool_history"],
            )

            if tool_decision.action == "SKIP":
                state["skipped_calls"].append(
                    {
                        "tool": tool_name,
                        "arguments": tool_args,
                        "reason": tool_decision.reason,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            {
                                "skipped": True,
                                "reason": tool_decision.reason,
                            }
                        ),
                    }
                )
                continue

            result = run_tool(
                tool_name,
                tool_args,
            )

            ran_tool = True

            state["tool_history"].append(
                {
                    "tool": tool_name,
                    "arguments": tool_args,
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

        if not ran_tool:
            if repeated_call:
                state["no_progress"] += 1

                if state["no_progress"] >= MAX_NO_PROGRESS:
                    state["decision"] = "ABSTAIN"
                    state["answer"] = (
                        "The agent kept repeating actions that "
                        "did not make useful progress."
                    )
                    return state

            continue

        state["no_progress"] = 0

        decision = evaluate_decision(
            state["user_message"],
            state["tool_history"],
        )

        state["decision_history"].append(
            decision.model_dump()
        )

        if decision.decision == "CONTINUE":
            continue

        state["decision"] = decision.decision

        if decision.decision == "COMPLETE":
            state["answer"] = build_final_answer(
                state["user_message"],
                state["tool_history"],
            )
        else:
            state["answer"] = decision.reason

        return state

    state["decision"] = "ABSTAIN"
    state["answer"] = (
        "The agent reached the maximum number of tool steps."
    )

    return state
