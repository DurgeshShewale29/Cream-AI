from app.records import load_records, search, count_by, get_by_id


def show(record):
    limit = f"Rs {record['income_limit']:,}" if record["income_limit"] else "not collected"
    print(f"{record['id']}. {record['scheme_name']}")
    print(f"   Department: {record['department']}")
    print(f"   For: {record['eligible_category']} | Income limit: {limit}")
    print(f"   Benefit: {record['benefit']}")
    print(f"   Source: {record['source_url']}")


def main():
    records = load_records()
    print(f"Loaded {len(records)} scholarships")
    while True:
        print()
        print("--- ScholarSetu ---")
        print("1. List all scholarships")
        print("2. Search by keyword")
        print("3. Count by field (department / eligible_category)")
        print("4. Get scholarship by id")
        print("0. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            for r in records:
                show(r)
        elif choice == "2":
            for r in search(records, input("Keyword: ")):
                show(r)
        elif choice == "3":
            field = input("Field: ").strip()
            print(count_by(records, field))
        elif choice == "4":
            try:
                record = get_by_id(records, int(input("Id: ")))
            except ValueError:
                print("Please enter a number.")
                continue
            if record:
                show(record)
            else:
                print("Not found.")
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()