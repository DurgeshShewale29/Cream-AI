import csv
import json
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_CSV = BASE_DIR / "data" / "scholarships_raw.csv"
OUT_JSON = BASE_DIR / "data" / "records.json"

REQUIRED = ["name", "level", "category", "apply_at"]
VALID_LEVELS = {"State", "Central"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_income(text):
    """Turn '8 lakh', 'Rs 8,00,000' or '800000' into the integer 800000."""
    cleaned = text.lower().replace("rs.", "").replace("rs", "").replace("₹", "")
    cleaned = cleaned.replace(",", "").strip()
    if "lakh" in cleaned:
        return int(float(cleaned.replace("lakh", "").strip()) * 100000)
    return int(float(cleaned))


def clean_row(row, new_id):
    """Return a clean record dict, or raise ValueError if the row is bad."""
    row = {key.strip(): (value or "").strip() for key, value in row.items()}

    for field in REQUIRED:
        if not row.get(field):
            raise ValueError(f"missing field '{field}'")

    level = row["level"].title()
    if level not in VALID_LEVELS:
        raise ValueError(f"level must be State or Central, got '{row['level']}'")

    return {
        "id": new_id,
        "name": row["name"],
        "level": level,
        "category": row["category"],
        "income_limit": parse_income(row.get("income_limit", "")),
        "benefit": row.get("benefit", ""),
        "deadline": row.get("deadline", "") or "verify on official portal",
        "apply_at": row["apply_at"],
        "source_url": row.get("source_url", ""),
        "verified": row.get("verified", "").lower() in ("yes", "true", "1"),
    }


def ingest(csv_path=RAW_CSV, out_path=OUT_JSON):
    records = []
    skipped = 0
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for line_number, row in enumerate(csv.DictReader(f), start=2):
                try:
                    records.append(clean_row(row, new_id=len(records) + 1))
                except ValueError as error:
                    skipped += 1
                    logging.warning("Row %s skipped: %s", line_number, error)
    except FileNotFoundError:
        logging.error("Raw file not found: %s", csv_path)
        return 0

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    logging.info("Saved %s records to %s (%s skipped)", len(records), out_path, skipped)
    return len(records)


if __name__ == "__main__":
    ingest()