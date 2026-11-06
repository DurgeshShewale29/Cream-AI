from data.sample_records import RECORDS


def print_all(records):
    for r in records:
        limit = f"Rs {r['income_limit']:,}" if r["income_limit"] else "not collected"
        print(f"{r['id']:>2}. {r['scheme_name']}")
        print(f"    {r['department']} | {r['eligible_category']} | limit: {limit}")


def search_by_keyword(records, keyword):
    keyword = keyword.lower().strip()
    results = []
    for r in records:
        text = " ".join(str(v) for v in r.values() if v is not None).lower()
        if keyword in text:
            results.append(r)
    return results


def count_by_field(records, field):
    counts = {}
    for r in records:
        counts[r[field]] = counts.get(r[field], 0) + 1
    return counts


print(f"Total records: {len(RECORDS)}")
print()
print_all(RECORDS)

print()
keyword = input("Search keyword (e.g. OBC, girls, disabilities): ")
found = search_by_keyword(RECORDS, keyword)
print(f"{len(found)} match(es)")
print_all(found)

print()
print("Records per department:")
for department, count in count_by_field(RECORDS, "department").items():
    print(f"  {department}: {count}")

print()
print("Records per eligible category:")
for category, count in count_by_field(RECORDS, "eligible_category").items():
    print(f"  {category}: {count}")

verified = sum(1 for r in RECORDS if r["verified"])
print()
print(f"Verified records: {verified} of {len(RECORDS)}")