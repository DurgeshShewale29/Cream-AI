import difflib
import re
import sys

from app.records import load_records

MIN_SCHEMES = 2
MAX_SCHEMES = 4
NOT_LISTED = "Not listed in our data"
MAX_CELL = 400


class ToolError(ValueError):
    """A problem with the tool's input, written so the agent (or a person) can fix it."""


def normalise(text):
    """Lowercase letters and digits only: 'Dr. Panjabrao' -> 'drpanjabrao'."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def words_match(query, name):
    """Every word of the query (3+ letters) is a word of the name, or a close spelling of one."""
    wanted = [w for w in words(query) if len(w) >= 3]
    if not wanted:
        return False
    name_words = words(name)
    return all(w in name_words or difflib.get_close_matches(w, name_words, n=1, cutoff=0.8)
               for w in wanted)


def known_names(records):
    return [r["scheme_name"] for r in records]


def find_scheme(name, records):
    """The record for a scheme name. Tries an exact match, then a part of the name,
    then the words of the name (allowing small spelling mistakes)."""
    key = normalise(name)
    if len(key) < 3:
        raise ToolError(f"'{name}' is too short to be a scheme name.")

    exact = [r for r in records if normalise(r["scheme_name"]) == key]
    if exact:
        return exact[0]
    for matches in (
        [r for r in records if key in normalise(r["scheme_name"])],
        [r for r in records if words_match(name, r["scheme_name"])],
    ):
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            options = "; ".join(r["scheme_name"] for r in matches)
            raise ToolError(f"'{name}' matches more than one scheme ({options}). Use a longer name.")
    raise ToolError(f"No scheme matches '{name}'. Known schemes: " + "; ".join(known_names(records)))


def cell(text):
    """One table cell on one line, with no pipe characters, not too long."""
    text = " ".join(str(text).split()).replace("|", "/")
    return text if len(text) <= MAX_CELL else text[:MAX_CELL].rsplit(" ", 1)[0] + "..."


def eligibility(record):
    text = record["eligible_category"]
    if record.get("income_limit"):
        text += f"; family income up to Rs {record['income_limit']:,}"
    return text


def documents(record):
    docs = record.get("documents")
    if isinstance(docs, list):
        docs = "; ".join(docs)
    return docs or NOT_LISTED


def compare_schemes(names):
    """Compare 2 to 4 schemes side by side. `names` is a list of scheme names
    (a single string with commas is accepted too). Returns a Markdown table."""
    if isinstance(names, str):
        names = [part for part in names.split(",") if part.strip()]
    if not isinstance(names, (list, tuple)):
        raise ToolError("Give a list of 2 to 4 scheme names.")
    if not MIN_SCHEMES <= len(names) <= MAX_SCHEMES:
        raise ToolError(f"Give {MIN_SCHEMES} to {MAX_SCHEMES} scheme names, not {len(names)}.")

    records = load_records()
    if not records:
        raise ToolError("No scheme data is loaded. Run: python -m app.ingest")

    found = []
    for name in names:
        record = find_scheme(str(name), records)
        if record in found:
            raise ToolError(f"'{name}' is the same scheme as another name in the list.")
        found.append(record)

    rows = [
        ("Benefit", [cell(r["benefit"]) for r in found]),
        ("Eligibility", [cell(eligibility(r)) for r in found]),
        ("Documents", [cell(documents(r)) for r in found]),
        ("Apply link", [cell(r["source_url"]) for r in found]),
    ]
    lines = ["| | " + " | ".join(cell(r["scheme_name"]) for r in found) + " |",
             "|---|" + "---|" * len(found)]
    lines += [f"| **{label}** | " + " | ".join(values) + " |" for label, values in rows]
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        print(compare_schemes(sys.argv[1:]))
    except ToolError as error:
        print(f"Error: {error}")