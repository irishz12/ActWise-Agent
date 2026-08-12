import json

from backend.decision import ToolDecision
from backend.fast_planner import (
    asks_for_duplicates as task_asks_for_duplicates,
    asks_for_preview as task_asks_for_preview,
    asks_for_structure as task_asks_for_structure,
    asks_for_summary as task_asks_for_summary,
    get_duplicate_column,
    get_filter,
    get_summary_column,
)
from backend.llm import client


MODEL = "openai/gpt-oss-20b"

READ_ONLY_TOOLS = {
    "list_files",
    "inspect_csv",
    "preview_rows",
    "find_duplicates",
    "calculate_summary",
    "filter_rows",
}


def direct_tool_decision(user_task, tool_name, arguments):
    task = user_task.lower()

    if tool_name == "find_duplicates":
        duplicate_terms = (
            "duplicate",
            "duplicates",
            "repeated",
            "repeating",
            "more than once",
            "multiple times",
        )

        if any(term in task for term in duplicate_terms):
            return ToolDecision(
                action="EXECUTE",
                reason="Duplicate detection is directly requested by the user.",
            )

    if tool_name == "calculate_summary":
        summary_terms = (
            "average",
            "mean",
            "total",
            "minimum",
            "maximum",
            "highest",
            "lowest",
            "summary",
        )

        column = str(
            arguments.get("column", "")
        ).strip().lower()

        asks_for_summary = any(
            term in task
            for term in summary_terms
        )

        if asks_for_summary and column and column in task:
            return ToolDecision(
                action="EXECUTE",
                reason=f"The requested summary directly uses the '{column}' column.",
            )

        if asks_for_summary and column not in task:
            return ToolDecision(
                action="SKIP",
                reason="The proposed summary column was not specified by the user.",
            )

    if tool_name == "filter_rows":
        value = str(
            arguments.get("value", "")
        ).strip().lower()

        if value and value in task:
            return ToolDecision(
                action="EXECUTE",
                reason="The requested filter value is explicitly present in the task.",
            )

    if tool_name == "preview_rows":
        if task_asks_for_preview(user_task):
            return ToolDecision(
                action="EXECUTE",
                reason="The user directly requested example or preview rows.",
            )

        return ToolDecision(
            action="SKIP",
            reason="Previewing rows does not directly contribute to the requested result.",
        )

    if tool_name == "inspect_csv":
        inspect_terms = (
            "column",
            "columns",
            "schema",
            "structure",
            "header",
            "headers",
            "row count",
            "inspect",
            "field",
            "fields",
        )

        asks_about_structure = any(
            term in task
            for term in inspect_terms
        )

        summary_is_ambiguous = (
            task_asks_for_summary(user_task)
            and get_summary_column(user_task) is None
        )

        duplicates_are_ambiguous = (
            task_asks_for_duplicates(user_task)
            and get_duplicate_column(user_task) is None
        )

        filter_is_ambiguous = (
            any(
                term in task
                for term in (
                    "filter",
                    "matching",
                    "criteria",
                    "criterion",
                    "condition",
                    "satisfy",
                    "meet the",
                )
            )
            and get_filter(user_task) is None
        )

        if (
            asks_about_structure
            or summary_is_ambiguous
            or duplicates_are_ambiguous
            or filter_is_ambiguous
        ):
            return ToolDecision(
                action="EXECUTE",
                reason=(
                    "CSV inspection is needed to identify the "
                    "missing column or filter criteria."
                ),
            )

    if tool_name == "create_report":
        if "report" in task:
            return ToolDecision(
                action="EXECUTE",
                reason="The user explicitly requested a report.",
            )

        return ToolDecision(
            action="SKIP",
            reason="The user did not request a report.",
        )

    if tool_name == "list_files":
        if "files" in task and ".csv" not in task:
            return ToolDecision(
                action="EXECUTE",
                reason="The user is asking about files available in the workspace.",
            )

    return None


def evaluate_tool_call(
    user_task,
    tool_name,
    arguments,
    tool_history,
):
    direct_decision = direct_tool_decision(
        user_task,
        tool_name,
        arguments,
    )

    if direct_decision is not None:
        return direct_decision

    context = {
        "task": user_task,
        "proposed_tool": tool_name,
        "arguments": arguments,
        "previous_tools": tool_history,
    }

    try:
        response = client.chat.completions.create(
            model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the action controller for ActWise. "
                    "Decide whether the proposed tool should EXECUTE or SKIP. "
                    "EXECUTE only when it provides information or performs an action "
                    "needed for the user's task. "
                    "SKIP unnecessary, repeated, or unrelated work. "
                    "Consider the entire user request, including multi-part tasks."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context),
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "tool_decision",
                "strict": True,
                "schema": ToolDecision.model_json_schema(),
            },
        },
        reasoning_effort="low",
    )

        return ToolDecision.model_validate_json(
            response.choices[0].message.content
        )

    except Exception:
        if tool_name in READ_ONLY_TOOLS:
            return ToolDecision(
                action="EXECUTE",
                reason=(
                    "The proposed read-only tool passed deterministic "
                    "guards, so it can proceed without the evaluator."
                ),
            )

        return ToolDecision(
            action="SKIP",
            reason="The evaluator could not verify this action reliably.",
        )
