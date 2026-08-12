import json
import sqlite3
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.answer_builder import build_answer
from backend.fast_planner import build_direct_plan
from backend.agent import (
    MAX_NO_PROGRESS,
    MAX_TOOL_STEPS,
    MODEL,
    TOOLS,
    build_final_answer,
    run_tool,
)
from backend.decision_engine import evaluate_decision
from backend.guards import should_skip_tool, tool_signature
from backend.llm import client
from backend.tool_evaluator import evaluate_tool_call


ACTWISE_MODEL = "openai/gpt-oss-20b"


class GraphState(TypedDict, total=False):
    user_message: str
    tool_history: list[dict]
    decision_history: list[dict]
    skipped_calls: list[dict]
    blocked_tools: list[str]
    proposed_calls: list[dict]
    seen_calls: list[tuple]
    decision: str | None
    answer: str | None
    no_progress: int
    steps: int
    made_progress: bool
    repeated_call: bool


def build_graph_answer(user_task, observations):
    answer = build_answer(
        user_task,
        observations,
    )

    if answer is not None:
        return answer

    context = {
        "task": user_task,
        "observations": observations,
    }

    response = client.chat.completions.create(
        model=ACTWISE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer using only the provided observations. "
                    "Do not invent values, units, currencies, or facts."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context),
            },
        ],
        temperature=0,
        max_tokens=300,
    )

    return response.choices[0].message.content

def planner(state: GraphState):
    direct_plan = build_direct_plan(
        state["user_message"],
        state.get("tool_history", []),
    )

    if direct_plan is not None:
        return {
            "proposed_calls": direct_plan,
            "steps": state.get("steps", 0) + 1,
        }

    blocked = set(state.get("blocked_tools", []))

    available_tools = [
        tool
        for tool in TOOLS
        if tool["function"]["name"] not in blocked
    ]

    context = {
        "task": state["user_message"],
        "completed_tools": state.get("tool_history", []),
        "skipped_tools": state.get("skipped_calls", []),
        "blocked_tools": sorted(blocked),
    }

    if not available_tools:
        return {
            "proposed_calls": [],
            "steps": state.get("steps", 0) + 1,
        }

    response = client.chat.completions.create(
        model=ACTWISE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the planner for ActWise. "
                    "Use only the tools provided. "
                    "Choose the smallest useful set of actions needed for the task. "
                    "Do not repeat skipped actions unless they have become necessary. "
                    "Do not inspect or preview data only for extra confidence when "
                    "a direct operation can answer the request. "
                    "If a discovery or preview action was already skipped, move directly "
                    "to an operation that produces one of the user's requested results."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context),
            },
        ],
        tools=available_tools,
        tool_choice="auto",
        temperature=0,
    )

    message = response.choices[0].message
    proposed_calls = []

    for tool_call in message.tool_calls or []:
        try:
            arguments = json.loads(
                tool_call.function.arguments or "{}"
            )
        except json.JSONDecodeError:
            arguments = {}

        proposed_calls.append(
            {
                "tool": tool_call.function.name,
                "arguments": arguments,
            }
        )

    return {
        "proposed_calls": proposed_calls,
        "steps": state.get("steps", 0) + 1,
    }


def execute_tools(state: GraphState):
    history = list(state.get("tool_history", []))
    skipped = list(state.get("skipped_calls", []))
    seen = set(state.get("seen_calls", []))
    blocked = set(state.get("blocked_tools", []))

    made_progress = False
    repeated_call = False

    for call in state.get("proposed_calls", []):
        tool_name = call["tool"]
        arguments = call["arguments"]

        signature = tool_signature(
            tool_name,
            arguments,
        )

        was_seen = signature in seen

        skip, reason = should_skip_tool(
            tool_name,
            arguments,
            state["user_message"],
            seen,
        )

        seen.add(signature)

        if skip:
            if was_seen:
                repeated_call = True

            blocked.add(tool_name)

            skipped.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "reason": reason,
                }
            )
            continue

        tool_decision = evaluate_tool_call(
            state["user_message"],
            tool_name,
            arguments,
            history,
        )

        if tool_decision.action == "SKIP":
            blocked.add(tool_name)

            skipped.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "reason": tool_decision.reason,
                }
            )
            continue

        result = run_tool(
            tool_name,
            arguments,
        )

        history.append(
            {
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
            }
        )

        made_progress = True

    return {
        "tool_history": history,
        "skipped_calls": skipped,
        "blocked_tools": sorted(blocked),
        "seen_calls": list(seen),
        "made_progress": made_progress,
        "repeated_call": repeated_call,
        "proposed_calls": [],
    }


def decide(state: GraphState):
    decision = evaluate_decision(
        state["user_message"],
        state.get("tool_history", []),
    )

    decision_history = list(
        state.get("decision_history", [])
    )
    decision_history.append(
        decision.model_dump()
    )

    no_progress = state.get("no_progress", 0)

    if state.get("made_progress"):
        no_progress = 0
    elif (
        decision.decision == "CONTINUE"
        and state.get("repeated_call")
    ):
        no_progress += 1

    if (
        decision.decision == "CONTINUE"
        and no_progress >= MAX_NO_PROGRESS
    ):
        return {
            "decision": "ABSTAIN",
            "answer": (
                "The agent could not find a useful action "
                "that moved the task forward."
            ),
            "decision_history": decision_history,
            "no_progress": no_progress,
        }

    if (
        decision.decision == "CONTINUE"
        and state.get("steps", 0) >= MAX_TOOL_STEPS
    ):
        return {
            "decision": "ABSTAIN",
            "answer": (
                "The agent reached the maximum number "
                "of planning steps."
            ),
            "decision_history": decision_history,
            "no_progress": no_progress,
        }

    if decision.decision == "COMPLETE":
        answer = build_graph_answer(
            state["user_message"],
            state.get("tool_history", []),
        )
    elif decision.decision in {"CLARIFY", "ABSTAIN"}:
        answer = decision.reason
    else:
        answer = None

    return {
        "decision": decision.decision,
        "answer": answer,
        "decision_history": decision_history,
        "no_progress": no_progress,
        "made_progress": False,
        "repeated_call": False,
    }


def clarify(state: GraphState):
    clarification = interrupt(
        {
            "type": "clarification",
            "question": state.get(
                "answer",
                "Please provide the missing information.",
            ),
            "task": state["user_message"],
        }
    )

    updated_task = (
        f'{state["user_message"]}\n'
        f'User clarification: {clarification}'
    )

    return {
        "user_message": updated_task,
        "decision": None,
        "answer": None,
        "no_progress": 0,
        "made_progress": False,
        "repeated_call": False,
        "blocked_tools": [],
        "seen_calls": [],
        "proposed_calls": [],
    }


def route_after_planner(state: GraphState):
    if state.get("proposed_calls"):
        return "tools"

    return "decision"


def route_after_tools(state: GraphState):
    if state.get("made_progress"):
        return "decision"

    if state.get("repeated_call"):
        return "decision"

    return "planner"


def route_after_decision(state: GraphState):
    decision = state.get("decision")

    if decision == "CONTINUE":
        return "planner"

    if decision == "CLARIFY":
        return "clarify"

    return END


builder = StateGraph(GraphState)

builder.add_node("planner", planner)
builder.add_node("tools", execute_tools)
builder.add_node("decision", decide)
builder.add_node("clarify", clarify)

builder.add_edge(START, "planner")

builder.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "tools": "tools",
        "decision": "decision",
    },
)

builder.add_conditional_edges(
    "tools",
    route_after_tools,
    {
        "decision": "decision",
        "planner": "planner",
    },
)

builder.add_edge(
    "clarify",
    "planner",
)

builder.add_conditional_edges(
    "decision",
    route_after_decision,
    {
        "planner": "planner",
        "clarify": "clarify",
        END: END,
    },
)

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
    initial_state: GraphState = {
        "user_message": user_message,
        "tool_history": [],
        "decision_history": [],
        "skipped_calls": [],
        "blocked_tools": [],
        "proposed_calls": [],
        "seen_calls": [],
        "decision": None,
        "answer": None,
        "no_progress": 0,
        "steps": 0,
        "made_progress": False,
        "repeated_call": False,
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
