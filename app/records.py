from data.sample_records import RECORDS


def load_records():
    """Return all records as a list of dicts."""
    return list(RECORDS)


def search(records, keyword):
    """Return records where the keyword appears in any field."""
    keyword = keyword.lower().strip()
    return [
        r for r in records
        if keyword in " ".join(str(v) for v in r.values()).lower()
    ]


def count_by(records, field):
    """Count records per value of a field, e.g. count_by(records, 'level')."""
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