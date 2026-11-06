from app.records import load_records, load_record_objects

dicts = load_records()
objects = load_record_objects()

print(f"Loaded {len(dicts)} dicts and {len(objects)} Record objects")
print()
first = objects[0]
print(first)
print()
print(f"Name  : {first.name}")
print(f"Limit : Rs {first.income_limit:,}")
print(f"Type  : {type(first).__name__}")