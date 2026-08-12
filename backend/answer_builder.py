def format_number(value):
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    return str(value)


def build_answer(user_task, observations):
    task = user_task.lower()
    sections = []

    for step in observations:
        tool = step.get("tool")
        result = step.get("result")

        if tool == "list_files" and isinstance(result, list):
            lines = ["**Available files**"]
            lines.extend(f"- {name}" for name in result)
            sections.append("\n".join(lines))
            continue

        if not isinstance(result, dict):
            continue

        if result.get("success") is False:
            continue

        if tool == "inspect_csv":
            columns = ", ".join(result.get("columns", []))

            sections.append(
                "\n".join(
                    [
                        f"**{result['filename']}**",
                        f"- Rows: {result['row_count']}",
                        f"- Columns: {columns}",
                    ]
                )
            )

        elif tool == "preview_rows":
            rows = result.get("rows", [])

            lines = [
                f"**First {len(rows)} rows of {result['filename']}**"
            ]

            for index, row in enumerate(rows, start=1):
                values = ", ".join(
                    f"{key}={value}"
                    for key, value in row.items()
                )
                lines.append(f"{index}. {values}")

            sections.append("\n".join(lines))

        elif tool == "find_duplicates":
            duplicates = result.get("duplicates", {})

            lines = ["**Duplicate values**"]

            if duplicates:
                for value, count in duplicates.items():
                    lines.append(
                        f"- **{value}** — {count} occurrences"
                    )
            else:
                lines.append("- No duplicates found.")

            sections.append("\n".join(lines))

        elif tool == "calculate_summary":
            column = result.get("column", "value")

            if (
                "average" in task
                or "mean" in task
            ) and "summary" not in task:
                sections.append(
                    f"**Average {column}:** "
                    f"{format_number(result['average'])}"
                )
            else:
                sections.append(
                    "\n".join(
                        [
                            f"**Summary for `{column}`**",
                            f"- Count: {format_number(result['count'])}",
                            f"- Total: {format_number(result['total'])}",
                            f"- Average: {format_number(result['average'])}",
                            f"- Minimum: {format_number(result['minimum'])}",
                            f"- Maximum: {format_number(result['maximum'])}",
                        ]
                    )
                )

        elif tool == "filter_rows":
            rows = result.get("rows", [])

            lines = [
                f"**Matches: {result.get('match_count', len(rows))}**"
            ]

            for row in rows:
                values = ", ".join(
                    f"{key}={value}"
                    for key, value in row.items()
                )
                lines.append(f"- {values}")

            sections.append("\n".join(lines))

        elif tool == "create_report":
            sections.append(
                "\n".join(
                    [
                        "**Report created**",
                        f"- File: {result['report_file']}",
                        f"- Path: {result['report_path']}",
                    ]
                )
            )

    if not sections:
        return None

    return "\n\n".join(sections)
