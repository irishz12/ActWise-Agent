import json
import sqlite3
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.llm import MODEL, client
from backend.tools import (
    WORKSPACE,
    calculate_summary,
    create_report,
    filter_rows,
    find_duplicates,
    inspect_csv,
    list_files,
    preview_rows,
)


MAX_AGENT_STEPS = 10

SYSTEM_PROMPT = (
    "You are ActWise, a single tool-using agent for local CSV data. "
    "Use only the tools you are given. "
    "Never invent files, columns, values, or capabilities that do not exist. "
    "Use the minimum number of tool calls needed to complete the task. "
    "Tool observations are the only source of truth — do not guess results. "
    "Call finish(decision=\"COMPLETE\", message=...) only when all requested "
    "work is done. "
    "Call finish(decision=\"CLARIFY\", message=...) when required information "
    "must come from the user. "
    "Call finish(decision=\"ABSTAIN\", message=...) when the available tools "
    "cannot perform what was requested. "
    "Do not repeat an identical tool call. "
    "Treat user-provided filenames, column names, field names and values "
    "literally. Never silently substitute a different existing field "
    "because it seems semantically similar. If a requested field does not "
    "exist and the intended replacement cannot be known with certainty, "
    "CLARIFY rather than guessing. "
    "Every turn, call either one or more business tools, or exactly one "
    "finish() call — never both, never neither."
)

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
            "description": (
                "Inspect a CSV file's columns and row count. Use this only "
                "when the file structure or required column is genuinely "
                "unknown. Do not use it to reinterpret or replace a column "
                "the user already named explicitly."
            ),
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
            "description": (
                "Preview the first few rows of a CSV file. Do not use the "
                "preview to infer a replacement for a column the user "
                "already named explicitly."
            ),
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
            "description": (
                "Find duplicate values in a CSV column. The column must be "
                "specified explicitly — it is never assumed. If the user "
                "explicitly names a column, use that exact column name; "
                "never substitute a different column because it looks "
                "semantically similar."
            ),
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
            "name": "calculate_summary",
            "description": (
                "Calculate count, average, total, minimum and maximum for a "
                "numeric CSV column. If the user explicitly names a column, "
                "pass that exact column name — never substitute a different "
                "column because it looks semantically similar. If the exact "
                "column does not exist, this returns column_not_found so "
                "you can ask the user to clarify."
            ),
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
            "description": (
                "Find CSV rows where a column matches a value. If the user "
                "explicitly names a filter column, use that exact column; "
                "never substitute a different column because it looks "
                "semantically similar."
            ),
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
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": (
                "Call this when no further tool call is needed. Use it to "
                "deliver the final answer (COMPLETE), ask the user for "
                "missing or ambiguous information (CLARIFY), or explain that "
                "the requested action is outside the available tools "
                "(ABSTAIN). Do not call this together with a business tool "
                "in the same turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": ["COMPLETE", "CLARIFY", "ABSTAIN"],
                    },
                    "message": {"type": "string"},
                },
                "required": ["decision", "message"],
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

PROTOCOL_ERROR_DETAIL = (
    "A turn must contain either one or more business tool calls, or "
    "exactly one finish() call — never both, never neither."
)


class AgentState(TypedDict, total=False):
    messages: list[dict]
    tool_history: list[dict]
    skipped_calls: list[dict]
    decision_history: list[dict]
    seen_calls: list[list]
    decision: str | None
    answer: str | None
    steps: int
    route: str | None


def tool_signature(name, arguments):
    return (
        name,
        json.dumps(arguments, sort_keys=True, default=str),
    )


def safe_path_error(arguments):
    """Reject any filename/report_name argument that would resolve outside
    the workspace directory. Returns an error dict, or None if safe."""
    workspace_root = WORKSPACE.resolve()

    for key in ("filename", "report_name"):
        value = arguments.get(key)

        if not value:
            continue

        try:
            candidate = (WORKSPACE / str(value)).resolve()
            candidate.relative_to(workspace_root)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": "unsafe_path",
                key: value,
            }

    return None


def run_tool(name, arguments):
    handler = TOOL_HANDLERS.get(name)

    if handler is None:
        return {
            "success": False,
            "error": "unknown_tool",
            "tool": name,
        }

    unsafe = safe_path_error(arguments)

    if unsafe is not None:
        return unsafe

    try:
        return handler(**arguments)
    except TypeError as error:
        return {
            "success": False,
            "error": "invalid_arguments",
            "detail": str(error),
        }
    except Exception as error:
        return {
            "success": False,
            "error": "tool_execution_error",
            "detail": str(error),
        }


def agent(state: AgentState):
    steps = state.get("steps", 0)

    if steps >= MAX_AGENT_STEPS:
        reason = "The agent reached the maximum number of steps."

        return {
            "decision": "ABSTAIN",
            "answer": reason,
            "decision_history": state.get("decision_history", [])
            + [{"decision": "ABSTAIN", "reason": reason}],
            "route": None,
        }

    messages = list(state["messages"])

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
        )
    except Exception as error:
        reason = f"The agent could not reach the model: {error}"

        return {
            "decision": "ABSTAIN",
            "answer": reason,
            "decision_history": state.get("decision_history", [])
            + [{"decision": "ABSTAIN", "reason": reason}],
            "steps": steps + 1,
            "route": None,
        }

    message = response.choices[0].message
    tool_calls = message.tool_calls or []

    assistant_entry = {
        "role": "assistant",
        "content": message.content,
    }

    if tool_calls:
        assistant_entry["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in tool_calls
        ]

    messages.append(assistant_entry)

    business_calls = [
        call for call in tool_calls if call.function.name != "finish"
    ]
    finish_calls = [
        call for call in tool_calls if call.function.name == "finish"
    ]

    if business_calls and not finish_calls:
        return {
            "messages": messages,
            "steps": steps + 1,
            "route": "tools",
            "decision": None,
        }

    if finish_calls and not business_calls and len(finish_calls) == 1:
        call = finish_calls[0]

        try:
            arguments = json.loads(call.function.arguments or "{}")
            decision = arguments["decision"]
            answer = arguments["message"]

            if decision not in {"COMPLETE", "CLARIFY", "ABSTAIN"}:
                raise ValueError("invalid decision value")

        except Exception:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(
                        {
                            "error": "invalid_finish_call",
                            "detail": (
                                "finish() requires decision "
                                "(COMPLETE|CLARIFY|ABSTAIN) and message."
                            ),
                        }
                    ),
                }
            )

            return {
                "messages": messages,
                "steps": steps + 1,
                "route": "agent",
                "decision": None,
            }

        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps({"acknowledged": True}),
            }
        )

        return {
            "messages": messages,
            "steps": steps + 1,
            "decision": decision,
            "answer": answer,
            "decision_history": state.get("decision_history", [])
            + [{"decision": decision, "reason": answer}],
            "route": None,
        }

    # Protocol error: mixed business + finish calls, multiple finish
    # calls, or a turn with no tool calls at all. Nudge the model to
    # correct itself on the next turn.
    for call in tool_calls:
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(
                    {
                        "error": "protocol_error",
                        "detail": PROTOCOL_ERROR_DETAIL,
                    }
                ),
            }
        )

    if not tool_calls:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Reminder: call a business tool or "
                    "finish(decision, message). Do not reply with plain text."
                ),
            }
        )

    return {
        "messages": messages,
        "steps": steps + 1,
        "route": "agent",
        "decision": None,
    }


def execute_tools(state: AgentState):
    messages = list(state["messages"])
    tool_history = list(state.get("tool_history", []))
    skipped_calls = list(state.get("skipped_calls", []))
    seen_calls = {tuple(sig) for sig in state.get("seen_calls", [])}

    last_message = messages[-1]
    executed_names = []

    for call in last_message.get("tool_calls", []):
        name = call["function"]["name"]

        try:
            arguments = json.loads(
                call["function"]["arguments"] or "{}"
            )
        except json.JSONDecodeError:
            arguments = {}

        signature = tool_signature(name, arguments)

        if signature in seen_calls:
            reason = "This exact tool call has already been executed."

            skipped_calls.append(
                {
                    "tool": name,
                    "arguments": arguments,
                    "reason": reason,
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(
                        {"skipped": True, "reason": reason}
                    ),
                }
            )
            continue

        seen_calls.add(signature)

        result = run_tool(name, arguments)

        tool_history.append(
            {
                "tool": name,
                "arguments": arguments,
                "result": result,
            }
        )
        executed_names.append(name)

        messages.append(
            {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result),
            }
        )

    decision_history = list(state.get("decision_history", []))

    if executed_names:
        decision_history.append(
            {
                "decision": "CONTINUE",
                "reason": f"Executed: {', '.join(executed_names)}",
            }
        )

    return {
        "messages": messages,
        "tool_history": tool_history,
        "skipped_calls": skipped_calls,
        "seen_calls": [list(sig) for sig in seen_calls],
        "decision_history": decision_history,
    }


def clarify(state: AgentState):
    question = state.get("answer") or "Please provide the missing information."

    clarification = interrupt(
        {
            "type": "clarification",
            "question": question,
        }
    )

    messages = list(state["messages"])
    messages.append(
        {
            "role": "user",
            "content": clarification,
        }
    )

    return {
        "messages": messages,
        "decision": None,
        "answer": None,
        "route": None,
    }


def route_after_agent(state: AgentState):
    decision = state.get("decision")

    if decision in {"COMPLETE", "ABSTAIN"}:
        return END

    if decision == "CLARIFY":
        return "clarify"

    return state.get("route") or "agent"


builder = StateGraph(AgentState)

builder.add_node("agent", agent)
builder.add_node("tools", execute_tools)
builder.add_node("clarify", clarify)

builder.add_edge(START, "agent")

builder.add_conditional_edges(
    "agent",
    route_after_agent,
    {
        "tools": "tools",
        "clarify": "clarify",
        "agent": "agent",
        END: END,
    },
)

builder.add_edge("tools", "agent")
builder.add_edge("clarify", "agent")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

db_connection = sqlite3.connect(
    DATA_DIR / "actwise.db",
    check_same_thread=False,
)

checkpointer = SqliteSaver(db_connection)

graph = builder.compile(
    checkpointer=checkpointer,
)


def run_graph_agent(user_message, thread_id="default"):
    initial_state: AgentState = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "tool_history": [],
        "skipped_calls": [],
        "decision_history": [],
        "seen_calls": [],
        "decision": None,
        "answer": None,
        "steps": 0,
        "route": None,
    }

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    return graph.invoke(
        initial_state,
        config=config,
    )


def resume_graph_agent(clarification, thread_id):
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    return graph.invoke(
        Command(resume=clarification),
        config=config,
    )
