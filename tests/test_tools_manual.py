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
    print(list_files())

    print("\n2. INSPECT CSV")
    print(inspect_csv("customers.csv"))

    print("\n3. PREVIEW ROWS")
    print(preview_rows("customers.csv", 3))

    print("\n4. FIND DUPLICATES")
    print(find_duplicates("customers.csv"))

    print("\n5. CALCULATE AGE SUMMARY")
    print(calculate_summary("customers.csv", "age"))

    print("\n6. FILTER KOLKATA CUSTOMERS")
    print(filter_rows("customers.csv", "city", "Kolkata"))

    print("\n7. CREATE REPORT")
    print(create_report("customers.csv", "customer_report.txt"))

    print("\n8. TEST MISSING FILE")
    print(inspect_csv("missing.csv"))

    print("\n9. TEST INVALID COLUMN")
    print(calculate_summary("customers.csv", "salary"))


if __name__ == "__main__":
    run()
