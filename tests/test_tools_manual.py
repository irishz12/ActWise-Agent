from pathlib import Path

from backend.tools import (
    list_files,
    inspect_csv,
    preview_rows,
    find_duplicates,
    calculate_summary,
    filter_rows,
    create_report,
)


def run():
    print("\n1. LIST FILES")
    files = list_files()
    print(files)
    assert "customers.csv" in files

    print("\n2. INSPECT CSV")
    inspected = inspect_csv("customers.csv")
    print(inspected)
    assert inspected["success"] is True
    assert inspected["row_count"] == 10
    assert set(inspected["columns"]) == {
        "customer_id",
        "name",
        "age",
        "city",
        "premium",
    }

    print("\n3. PREVIEW ROWS")
    preview = preview_rows("customers.csv", 3)
    print(preview)
    assert preview["success"] is True
    assert len(preview["rows"]) == 3

    print("\n4. FIND DUPLICATES")
    duplicates = find_duplicates("customers.csv", "customer_id")
    print(duplicates)
    assert duplicates["success"] is True
    assert duplicates["duplicate_count"] == 2
    assert duplicates["duplicates"]["CUST002"] == 2
    assert duplicates["duplicates"]["CUST003"] == 2

    print("\n5. CALCULATE AGE SUMMARY")
    summary = calculate_summary("customers.csv", "age")
    print(summary)
    assert summary["success"] is True
    assert summary["count"] == 10
    assert summary["average"] == 34.6
    assert summary["total"] == 346.0
    assert summary["minimum"] == 27.0
    assert summary["maximum"] == 45.0

    print("\n6. FILTER KOLKATA CUSTOMERS")
    filtered = filter_rows("customers.csv", "city", "Kolkata")
    print(filtered)
    assert filtered["success"] is True
    assert filtered["match_count"] == 3

    print("\n7. CREATE REPORT")
    report = None
    try:
        report = create_report(
            "customers.csv",
            "test_tools_manual_report.txt",
        )
        print(report)
        assert report["success"] is True
        assert Path(report["report_path"]).exists()
    finally:
        if report is not None:
            Path(report["report_path"]).unlink(missing_ok=True)

    print("\n8. TEST MISSING FILE")
    missing = inspect_csv("missing.csv")
    print(missing)
    assert missing["success"] is False
    assert missing["error"] == "file_not_found"

    print("\n9. TEST INVALID COLUMN")
    invalid_column = calculate_summary("customers.csv", "salary")
    print(invalid_column)
    assert invalid_column["success"] is False
    assert invalid_column["error"] == "column_not_found"

    print("\nAll tool checks passed.")


if __name__ == "__main__":
    run()
