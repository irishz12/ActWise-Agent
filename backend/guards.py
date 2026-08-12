import json
import re

from backend.fast_planner import (
    asks_for_duplicates as task_asks_for_duplicates,
    asks_for_summary as task_asks_for_summary,
    get_duplicate_column,
    get_filter,
    get_summary_column,
)


FILE_PATTERN = re.compile(
    r"\b[\w.-]+\.(?:csv|txt)\b",
    re.IGNORECASE,
)

STRUCTURE_TERMS = {
    "column",
    "columns",
    "schema",
    "structure",
    "header",
    "headers",
    "fields",
    "field",
    "inspect",
    "row count",
}

DIRECT_OPERATION_TERMS = {
    "duplicate",
    "duplicates",
    "repeated",
    "repeating",
    "more than once",
    "multiple times",
    "average",
    "mean",
    "minimum",
    "maximum",
    "highest",
    "lowest",
    "total",
    "filter",
    "report",
}

SUMMARY_TERMS = {
    "summary",
    "average",
    "mean",
    "minimum",
    "maximum",
    "highest",
    "lowest",
    "total",
}


def normalize_value(value):
    if isinstance(value, str):
        return value.strip().lower()

    if isinstance(value, dict):
        return {
            key: normalize_value(item)
            for key, item in sorted(value.items())
        }

    if isinstance(value, list):
        return [
            normalize_value(item)
            for item in value
        ]

    return value


def tool_signature(tool_name, arguments):
    normalized = normalize_value(arguments)

    return (
        tool_name.lower(),
        json.dumps(
            normalized,
            sort_keys=True,
            default=str,
        ),
    )


def inspect_is_needed(user_message):
    task = user_message.lower()

    asks_about_structure = any(
        term in task
        for term in STRUCTURE_TERMS
    )

    summary_is_ambiguous = (
        task_asks_for_summary(user_message)
        and get_summary_column(user_message) is None
    )

    duplicates_are_ambiguous = (
        task_asks_for_duplicates(user_message)
        and get_duplicate_column(user_message) is None
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
        and get_filter(user_message) is None
    )

    return any(
        (
            asks_about_structure,
            summary_is_ambiguous,
            duplicates_are_ambiguous,
            filter_is_ambiguous,
        )
    )


def should_skip_tool(
    tool_name,
    arguments,
    user_message,
    seen_calls=None,
):
    task = user_message.lower()

    has_filename = (
        FILE_PATTERN.search(user_message)
        is not None
    )

    if seen_calls is not None:
        signature = tool_signature(
            tool_name,
            arguments,
        )

        if signature in seen_calls:
            return (
                True,
                "The same tool call has already been proposed.",
            )

    if tool_name == "list_files" and has_filename:
        return (
            True,
            "The filename is already known.",
        )

    if tool_name == "inspect_csv" and has_filename:
        if inspect_is_needed(user_message):
            return False, None

        asks_for_operation = any(
            term in task
            for term in DIRECT_OPERATION_TERMS
        )

        if asks_for_operation:
            return (
                True,
                "The task can use the requested data operation directly.",
            )

    if tool_name == "calculate_summary":
        column = str(
            arguments.get("column", "")
        ).strip().lower()

        asks_for_summary = any(
            term in task
            for term in SUMMARY_TERMS
        )

        if (
            asks_for_summary
            and column
            and column not in task
        ):
            return (
                True,
                f"The user did not specify the '{column}' column.",
            )

    if tool_name == "create_report":
        asks_for_summary = any(
            term in task
            for term in SUMMARY_TERMS
        )

        if (
            asks_for_summary
            and "report" not in task
        ):
            return (
                True,
                "Creating a report does not resolve the requested numeric summary.",
            )

    return False, None
