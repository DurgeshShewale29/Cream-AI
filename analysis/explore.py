from pathlib import Path

import pandas as pd

RECORDS_JSON = Path(__file__).resolve().parent.parent / "data" / "records.json"

if not RECORDS_JSON.exists():
    raise SystemExit("data/records.json not found. Run: python -m app.ingest")

df = pd.read_json(RECORDS_JSON)

# Fact 1: how many schemes, and how complete is the data?
total = len(df)
verified = int(df["verified"].sum())
no_benefit = int((df["benefit"] == "VERIFY").sum())
no_category = int((df["eligible_category"] == "VERIFY").sum())
print("FACT 1 - Data completeness")
print(f"  {total} schemes, {verified} verified on the official page")
print(f"  {no_benefit} still need a benefit, {no_category} still need an eligible category")

# Fact 2: which departments have the most schemes?
print()
print("FACT 2 - Departments with the most schemes")
for department, count in df["department"].value_counts().head(5).items():
    print(f"  {count:>2}  {department}")

# Fact 3: what do the collected income limits look like?
print()
print("FACT 3 - Income limits")
limits = df["income_limit"].dropna()
print(f"  {len(limits)} of {total} schemes have an income limit collected")
if len(limits):
    print(f"  lowest Rs {int(limits.min()):,} | median Rs {int(limits.median()):,} | highest Rs {int(limits.max()):,}")