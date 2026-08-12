import json

from backend.decision import AgentDecision
from backend.llm import client
from backend.fast_planner import (
    asks_for_duplicates,
    asks_for_filter as planner_asks_for_filter,
    asks_for_preview as planner_asks_for_preview,
    asks_for_structure as planner_asks_for_structure,
    asks_for_summary,
    get_duplicate_column,
    get_filename,
    get_filter,
    get_summary_column,
    is_unsupported,
    needs_file_context,
)


MODEL = "openai/gpt-oss-20b"

AVAILABLE_TOOLS = [
    "list_files",
    "inspect_csv",
    "preview_rows",
    "find_duplicates",
    "calculate_summary",
    "filter_rows",
    "create_report",
]


def get_result(observations, tool_name):
    for observation in reversed(observations):
        if observation.get("tool") != tool_name:
            continue

        result = observation.get("result")

        if isinstance(result, dict):
            if result.get("success") is not False:
                return result

        elif result is not None:
            return result

    return None


def check_failed_tools(observations):
    for observation in reversed(observations):
        result = observation.get("result")

        if not isinstance(result, dict):
            continue

        if result.get("success") is not False:
            continue

        error = result.get("error")

        if error == "file_not_found":
            return AgentDecision(
                decision="ABSTAIN",
                reason=(
                    "The requested file does not exist "
                    "in the workspace."
                ),
            )

        if error == "not_a_csv":
            return AgentDecision(
                decision="ABSTAIN",
                reason="The requested file is not a CSV file.",
            )

        if error == "column_not_found":
            return AgentDecision(
                decision="CLARIFY",
                reason=(
                    "The requested column was not found "
                    "in the CSV."
                ),
            )

    return None


def mentioned_columns(task, columns):
    text = task.lower()

    return [
        str(column)
        for column in columns
        if str(column).lower() in text
    ]


def asks_for_preview(task):
    text = task.lower()

    terms = (
        "preview",
        "sample row",
        "sample rows",
        "sample record",
        "sample records",
        "first row",
        "first rows",
        "first 1",
        "first 2",
        "first 3",
        "first 4",
        "first 5",
    )

    return any(
        term in text
        for term in terms
    )


def asks_for_filter(task):
    text = task.lower()

    return (
        get_filter(task) is not None
        or "filter" in text
        or "matching" in text
    )


def deterministic_decision(user_task, observations):
    task = user_task.lower()

    if is_unsupported(user_task):
        return AgentDecision(
            decision="ABSTAIN",
            reason=(
                "The requested action is not supported "
                "by the available ActWise tools."
            ),
        )

    if (
        get_filename(user_task) is None
        and needs_file_context(user_task)
    ):
        return AgentDecision(
            decision="CLARIFY",
            reason=(
                "The user needs to specify which CSV file "
                "should be used."
            ),
        )

    failed = check_failed_tools(observations)

    if failed:
        return failed

    inspect_result = get_result(
        observations,
        "inspect_csv",
    )

    duplicate_result = get_result(
        observations,
        "find_duplicates",
    )

    summary_result = get_result(
        observations,
        "calculate_summary",
    )

    filter_result = get_result(
        observations,
        "filter_rows",
    )

    preview_result = get_result(
        observations,
        "preview_rows",
    )

    report_result = get_result(
        observations,
        "create_report",
    )

    file_result = get_result(
        observations,
        "list_files",
    )

    # Filtering is supported, but an aggregate over the
    # filtered subset is not supported by the current tools.
    if (
        get_filter(user_task) is not None
        and asks_for_summary(user_task)
        and filter_result is not None
    ):
        return AgentDecision(
            decision="ABSTAIN",
            reason=(
                "ActWise can filter the rows, but the current "
                "tools cannot calculate an aggregate only over "
                "that filtered subset."
            ),
        )

    if inspect_result:
        columns = inspect_result.get(
            "columns",
            [],
        )

        if asks_for_summary(user_task):
            selected = mentioned_columns(
                user_task,
                columns,
            )

            explicit_column = get_summary_column(
                user_task
            )

            if (
                len(selected) != 1
                or explicit_column is None
            ):
                return AgentDecision(
                    decision="CLARIFY",
                    reason=(
                        "The user needs to specify one column "
                        "to summarize."
                    ),
                )

        if asks_for_duplicates(user_task):
            if get_duplicate_column(user_task) is None:
                return AgentDecision(
                    decision="CLARIFY",
                    reason=(
                        "The user needs to specify which column "
                        "should be checked for duplicates."
                    ),
                )

        if planner_asks_for_filter(user_task):
            if get_filter(user_task) is None:
                return AgentDecision(
                    decision="CLARIFY",
                    reason=(
                        "The user needs to specify the filter "
                        "column and value."
                    ),
                )

    needs_duplicates = asks_for_duplicates(
        user_task
    )

    needs_summary = asks_for_summary(
        user_task
    )

    needs_preview = planner_asks_for_preview(
        user_task
    )

    needs_structure = planner_asks_for_structure(
        user_task
    )

    needs_report = "report" in task

    needs_file_list = any(
        term in task
        for term in (
            "list files",
            "what files",
            "available files",
        )
    )

    required = []

    if needs_duplicates:
        required.append(
            duplicate_result is not None
        )

    if needs_summary:
        required.append(
            summary_result is not None
        )

    if needs_preview:
        required.append(
            preview_result is not None
        )

    if needs_structure:
        required.append(
            inspect_result is not None
        )

    if needs_report:
        required.append(
            report_result is not None
        )

    if needs_file_list:
        required.append(
            file_result is not None
        )

    if required:
        if all(required):
            return AgentDecision(
                decision="COMPLETE",
                reason=(
                    "All information required by the "
                    "user's task is available."
                ),
            )

        return AgentDecision(
            decision="CONTINUE",
            reason=(
                "At least one requested result "
                "is still missing."
            ),
        )

    if filter_result is not None:
        return AgentDecision(
            decision="COMPLETE",
            reason=(
                "The requested matching rows are available."
            ),
        )

    return None


def llm_fallback(user_task, observations):
    context = {
        "task": user_task,
        "observations": observations,
        "available_tools": AVAILABLE_TOOLS,
    }

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the ActWise decision controller. "
                        "Return JSON only. "
                        "Use decision CONTINUE, COMPLETE, CLARIFY, "
                        "or ABSTAIN. "
                        "CONTINUE means another available action can help. "
                        "COMPLETE means the task is finished. "
                        "CLARIFY means information must come from the user. "
                        "ABSTAIN means the task cannot be completed reliably. "
                        "Return keys decision and reason only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context),
                },
            ],
            response_format={
                "type": "json_object",
            },
            temperature=0,
            max_tokens=120,
            reasoning_effort="low",
        )

        return AgentDecision.model_validate_json(
            response.choices[0].message.content
        )

    except Exception:
        return AgentDecision(
            decision="ABSTAIN",
            reason=(
                "ActWise could not determine "
                "a reliable next action."
            ),
        )


def evaluate_decision(user_task, observations):
    decision = deterministic_decision(
        user_task,
        observations,
    )

    if decision is not None:
        return decision

    return llm_fallback(
        user_task,
        observations,
    )
