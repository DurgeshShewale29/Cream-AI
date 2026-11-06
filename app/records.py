import json
import logging
from pathlib import Path

from app.models import Record
from data.sample_records import RECORDS as SAMPLE_RECORDS

RECORDS_JSON = Path(__file__).resolve().parent.parent / "data" / "records.json"


def load_records():
    """Return all records (list of dicts). Uses data/records.json if it exists,
    otherwise falls back to the hand-collected data/sample_records.py."""
    try:
        with open(RECORDS_JSON, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("records.json not found, using sample_records.py "
                        "(run: python -m app.fetch, then python -m app.ingest)")
        return list(SAMPLE_RECORDS)


def load_record_objects():
    """Return all records as Record objects."""
    return [Record.from_dict(r) for r in load_records()]


def search(records, keyword):
    """Return records where the keyword appears in any field."""
    keyword = keyword.lower().strip()
    return [
        r for r in records
        if keyword in " ".join(str(v) for v in r.values() if v is not None).lower()
    ]


def count_by(records, field):
    """Count records per value of a field, e.g. count_by(records, 'department')."""
    counts = {}
    for r in records:
        key = r.get(field, "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def get_by_id(records, record_id):
    """Return the record with this id, or None if not found."""
    for r in records:
        if r["id"] == record_id:
            return r
    return None