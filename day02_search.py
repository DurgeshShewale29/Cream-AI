from data.sample_records import RECORDS


def print_all(records):
    for r in records:
        print(f"{r['id']}. {r['name']} [{r['level']}] - {r['benefit']}")


def search_by_keyword(records, keyword):
    keyword = keyword.lower().strip()
    results = []
    for r in records:
        text = " ".join(str(value) for value in r.values()).lower()
        if keyword in text:
            results.append(r)
    return results


def count_per_category(records):
    counts = {}
    for r in records:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    return counts


print(f"Total records: {len(RECORDS)}")
print()
print_all(RECORDS)

print()
keyword = input("Search keyword (e.g. OBC, girls, MahaDBT): ")
found = search_by_keyword(RECORDS, keyword)
print(f"{len(found)} match(es)")
print_all(found)

print()
print("Records per category:")
for category, count in count_per_category(RECORDS).items():
    print(f"  {category}: {count}")