import csv
from pathlib import Path


WORKSPACE = Path("workspace")


def list_files():
    files = []

    for path in WORKSPACE.iterdir():
        if path.is_file():
            files.append(path.name)

    return files


def inspect_csv(filename):
    file_path = WORKSPACE / filename

    if not file_path.exists():
        return {
            "success": False,
            "error": "file_not_found",
            "filename": filename
        }

    if file_path.suffix.lower() != ".csv":
        return {
            "success": False,
            "error": "not_a_csv",
            "filename": filename
        }

    with file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    return {
        "success": True,
        "filename": filename,
        "row_count": len(rows),
        "columns": reader.fieldnames
    }


def preview_rows(filename, limit=5):
    file_path = WORKSPACE / filename

    if not file_path.exists():
        return {
            "success": False,
            "error": "file_not_found",
            "filename": filename
        }

    if file_path.suffix.lower() != ".csv":
        return {
            "success": False,
            "error": "not_a_csv",
            "filename": filename
        }

    with file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = []

        for index, row in enumerate(reader):
            if index >= limit:
                break

            rows.append(row)

    return {
        "success": True,
        "filename": filename,
        "rows": rows
    }


def find_duplicates(filename, column):
    file_path = WORKSPACE / filename

    if not file_path.exists():
        return {
            "success": False,
            "error": "file_not_found",
            "filename": filename
        }

    if file_path.suffix.lower() != ".csv":
        return {
            "success": False,
            "error": "not_a_csv",
            "filename": filename
        }

    with file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if column not in reader.fieldnames:
            return {
                "success": False,
                "error": "column_not_found",
                "column": column
            }

        counts = {}

        for row in reader:
            value = row[column]
            counts[value] = counts.get(value, 0) + 1

    duplicates = {
        value: count
        for value, count in counts.items()
        if count > 1
    }

    return {
        "success": True,
        "filename": filename,
        "column": column,
        "duplicate_count": len(duplicates),
        "duplicates": duplicates
    }


def calculate_summary(filename, column):
    file_path = WORKSPACE / filename

    if not file_path.exists():
        return {
            "success": False,
            "error": "file_not_found",
            "filename": filename
        }

    if file_path.suffix.lower() != ".csv":
        return {
            "success": False,
            "error": "not_a_csv",
            "filename": filename
        }

    with file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if column not in reader.fieldnames:
            return {
                "success": False,
                "error": "column_not_found",
                "column": column
            }

        values = []

        for row in reader:
            value = row[column]

            try:
                values.append(float(value))
            except ValueError:
                return {
                    "success": False,
                    "error": "non_numeric_column",
                    "column": column
                }

    if not values:
        return {
            "success": False,
            "error": "no_data",
            "column": column
        }

    return {
        "success": True,
        "filename": filename,
        "column": column,
        "count": len(values),
        "average": round(sum(values) / len(values), 2),
        "total": round(sum(values), 2),
        "minimum": min(values),
        "maximum": max(values)
    }


def filter_rows(filename, column, value):
    file_path = WORKSPACE / filename

    if not file_path.exists():
        return {
            "success": False,
            "error": "file_not_found",
            "filename": filename
        }

    if file_path.suffix.lower() != ".csv":
        return {
            "success": False,
            "error": "not_a_csv",
            "filename": filename
        }

    with file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if column not in reader.fieldnames:
            return {
                "success": False,
                "error": "column_not_found",
                "column": column
            }

        matches = []

        for row in reader:
            if str(row[column]).strip().lower() == str(value).strip().lower():
                matches.append(row)

    return {
        "success": True,
        "filename": filename,
        "column": column,
        "value": value,
        "match_count": len(matches),
        "rows": matches
    }


def create_report(filename, report_name="summary_report.txt"):
    file_path = WORKSPACE / filename

    if not file_path.exists():
        return {
            "success": False,
            "error": "file_not_found",
            "filename": filename
        }

    if file_path.suffix.lower() != ".csv":
        return {
            "success": False,
            "error": "not_a_csv",
            "filename": filename
        }

    if Path(report_name).suffix.lower() != ".txt":
        return {
            "success": False,
            "error": "invalid_report_type",
            "report_name": report_name,
        }

    with file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    report_path = WORKSPACE / report_name

    with report_path.open("w", encoding="utf-8") as report:
        report.write(f"Report for: {filename}\n")
        report.write(f"Rows: {len(rows)}\n")
        report.write(f"Columns: {', '.join(reader.fieldnames or [])}\n")

    return {
        "success": True,
        "source_file": filename,
        "report_file": report_name,
        "report_path": str(report_path)
    }
