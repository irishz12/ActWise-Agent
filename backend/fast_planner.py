import re


FILE_PATTERN = re.compile(
    r"\b[\w.-]+\.csv\b",
    re.IGNORECASE,
)

REPORT_PATTERN = re.compile(
    r"\b[\w.-]+\.txt\b",
    re.IGNORECASE,
)

FIRST_ROWS_PATTERN = re.compile(
    r"\bfirst\s+(\d+)\s+rows?\b",
    re.IGNORECASE,
)

EXAMPLE_ROWS_PATTERN = re.compile(
    r"\b(?:show|give(?: me)?|return|display)\s+"
    r"(?:(\d+|one|two|three|four|five)\s+)?"
    r"(?:example|sample)\s+"
    r"(?:rows?|records?|entries)\b",
    re.IGNORECASE,
)

FILTER_PATTERN = re.compile(
    r"\bwhere\s+([\w_]+)\s+(?:is|equals?|=)\s+([^,.?]+)",
    re.IGNORECASE,
)

FROM_PATTERN = re.compile(
    r"\bfrom\s+([A-Za-z][A-Za-z .'-]*?)"
    r"(?=\s+and\b|\s+in\s+[\w.-]+\.csv\b)",
    re.IGNORECASE,
)

ENTITY_FILTER_PATTERN = re.compile(
    r"\b(?:get|show(?: me)?|return|list|pull out|fetch|retrieve)\s+"
    r"(?:the\s+)?"
    r"([A-Za-z][A-Za-z .'-]{0,40}?)\s+"
    r"(?:customers|entries|records|rows)\b",
    re.IGNORECASE,
)

FOR_CUSTOMERS_PATTERN = re.compile(
    r"\bfor\s+([A-Za-z][A-Za-z .'-]{0,40}?)\s+customers\b",
    re.IGNORECASE,
)

SUMMARY_COLUMN_PATTERN = re.compile(
    r"\b(?:average|mean|total|minimum|maximum|highest|lowest)\s+"
    r"(?:of\s+)?(?:the\s+)?([\w_]+)",
    re.IGNORECASE,
)


SUMMARY_TERMS = {
    "summary",
    "average",
    "mean",
    "total",
    "minimum",
    "maximum",
    "highest",
    "lowest",
}

DUPLICATE_TERMS = {
    "duplicate",
    "duplicates",
    "repeated",
    "repeating",
    "more than once",
    "multiple times",
}

UNSUPPORTED_TERMS = {
    "delete",
    "remove",
    "change",
    "update",
    "upload",
    "bar chart",
    "pie chart",
    "chart",
    "plot",
    "graph",
    "histogram",
    "visualize",
    "visualise",
    "join",
    "merge",
    "combine",
    "append",
    "sort",
    "rename",
}

COLUMN_STOPWORDS = {
    "in",
    "from",
    "for",
    "of",
    "the",
    "a",
    "an",
    "column",
    "columns",
    "value",
    "values",
    "either",
}

GENERIC_FILTER_VALUES = {
    "all",
    "matching",
    "the matching",
    "only the matching",
    "example",
    "sample",
    "first",
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


def get_filename(task):
    match = FILE_PATTERN.search(task)
    return match.group(0) if match else None


def asks_for_summary(task):
    text = task.lower()

    return any(
        term in text
        for term in SUMMARY_TERMS
    )


def asks_for_duplicates(task):
    text = task.lower()

    return any(
        term in text
        for term in DUPLICATE_TERMS
    )


def asks_for_preview(task):
    text = task.lower()

    return bool(
        FIRST_ROWS_PATTERN.search(task)
        or EXAMPLE_ROWS_PATTERN.search(task)
        or (
            any(
                term in text
                for term in (
                    "preview",
                    "sample",
                    "example",
                )
            )
            and any(
                term in text
                for term in (
                    "row",
                    "rows",
                    "record",
                    "records",
                    "entry",
                    "entries",
                )
            )
        )
    )


def asks_for_structure(task):
    text = task.lower()

    return any(
        term in text
        for term in (
            "what columns",
            "which columns",
            "row count",
            "record count",
            "how many records",
            "how many rows",
            "how many entries",
            "number of records",
            "number of rows",
            "number of entries",
            "entries are there",
            "schema",
            "headers",
            "structure",
            "field",
            "fields",
            "attribute",
            "attributes",
        )
    )


def is_unsupported(task):
    text = task.lower()

    if "email" in text:
        return True

    storage_target = (
        "s3" in text
        or "cloud storage" in text
        or "cloud bucket" in text
    )

    storage_action = any(
        verb in text
        for verb in (
            "upload",
            "put",
            "place",
            "store",
            "copy",
            "move",
        )
    )

    if storage_target and storage_action:
        return True

    return any(
        term in text
        for term in UNSUPPORTED_TERMS
    )


def get_summary_column(task):
    match = SUMMARY_COLUMN_PATTERN.search(task)

    if not match:
        return None

    column = match.group(1).strip().lower()

    if column in COLUMN_STOPWORDS:
        return None

    return column


def get_duplicate_column(task):
    text = task.lower()

    if any(
        term in text
        for term in (
            "customer id",
            "customer ids",
            "customer_id",
        )
    ):
        return "customer_id"

    return None


def clean_filter_value(value):
    value = value.strip()

    if value.lower() in GENERIC_FILTER_VALUES:
        return None

    words = set(value.lower().split())

    if words.intersection(
        {
            "matching",
            "example",
            "sample",
            "first",
            "criteria",
            "criterion",
            "condition",
            "conditions",
            "meet",
            "meets",
            "satisfy",
            "satisfies",
        }
    ):
        return None

    return value


def get_filter(task):
    match = FILTER_PATTERN.search(task)

    if match:
        return (
            match.group(1).strip(),
            match.group(2).strip(),
        )

    match = FROM_PATTERN.search(task)

    if match:
        value = clean_filter_value(
            match.group(1)
        )

        if value:
            return "city", value

    match = ENTITY_FILTER_PATTERN.search(task)

    if match:
        value = clean_filter_value(
            match.group(1)
        )

        if value:
            return "city", value

    match = FOR_CUSTOMERS_PATTERN.search(task)

    if match:
        value = clean_filter_value(
            match.group(1)
        )

        if value:
            return "city", value

    return None


def asks_for_filter(task):
    text = task.lower()

    return (
        get_filter(task) is not None
        or "filter" in text
        or "matching" in text
        or "criteria" in text
        or "criterion" in text
        or "condition" in text
        or "satisfy" in text
        or "meet the" in text
    )


def get_preview_limit(task):
    match = FIRST_ROWS_PATTERN.search(task)

    if match:
        return int(match.group(1))

    match = EXAMPLE_ROWS_PATTERN.search(task)

    if not match:
        return 5

    value = match.group(1)

    if not value:
        return 5

    if value.isdigit():
        return int(value)

    return NUMBER_WORDS.get(
        value.lower(),
        5,
    )


def needs_file_context(task):
    text = task.lower()

    return any(
        (
            asks_for_summary(task),
            asks_for_duplicates(task),
            asks_for_preview(task),
            asks_for_structure(task),
            asks_for_filter(task),
            "report" in text,
        )
    )


def build_direct_plan(task, tool_history=None):
    text = task.lower()

    if any(
        phrase in text
        for phrase in (
            "list files",
            "what files",
            "available files",
        )
    ):
        return [
            {
                "tool": "list_files",
                "arguments": {},
            }
        ]

    if is_unsupported(task):
        return []

    filename = get_filename(task)

    if not filename:
        if needs_file_context(task):
            return []

        return None

    if "report" in text:
        report_match = REPORT_PATTERN.search(task)

        arguments = {
            "filename": filename,
        }

        if report_match:
            arguments["report_name"] = report_match.group(0)

        return [
            {
                "tool": "create_report",
                "arguments": arguments,
            }
        ]

    if asks_for_structure(task):
        return [
            {
                "tool": "inspect_csv",
                "arguments": {
                    "filename": filename,
                },
            }
        ]

    if asks_for_preview(task):
        return [
            {
                "tool": "preview_rows",
                "arguments": {
                    "filename": filename,
                    "limit": get_preview_limit(task),
                },
            }
        ]

    filter_request = get_filter(task)
    summary_requested = asks_for_summary(task)

    if filter_request and summary_requested:
        column, value = filter_request

        return [
            {
                "tool": "filter_rows",
                "arguments": {
                    "filename": filename,
                    "column": column,
                    "value": value,
                },
            }
        ]

    calls = []

    if asks_for_duplicates(task):
        column = get_duplicate_column(task)

        if column:
            calls.append(
                {
                    "tool": "find_duplicates",
                    "arguments": {
                        "filename": filename,
                        "column": column,
                    },
                }
            )
        else:
            return [
                {
                    "tool": "inspect_csv",
                    "arguments": {
                        "filename": filename,
                    },
                }
            ]

    if summary_requested:
        if "either" in text and " or " in text:
            return [
                {
                    "tool": "inspect_csv",
                    "arguments": {
                        "filename": filename,
                    },
                }
            ]

        column = get_summary_column(task)

        if column:
            calls.append(
                {
                    "tool": "calculate_summary",
                    "arguments": {
                        "filename": filename,
                        "column": column,
                    },
                }
            )
        elif not calls:
            return [
                {
                    "tool": "inspect_csv",
                    "arguments": {
                        "filename": filename,
                    },
                }
            ]

    if filter_request and not calls:
        column, value = filter_request

        return [
            {
                "tool": "filter_rows",
                "arguments": {
                    "filename": filename,
                    "column": column,
                    "value": value,
                },
            }
        ]

    if asks_for_filter(task) and not calls:
        return [
            {
                "tool": "inspect_csv",
                "arguments": {
                    "filename": filename,
                },
            }
        ]

    return calls or None
