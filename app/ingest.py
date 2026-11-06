import json
import logging
import re
from html.parser import HTMLParser

from app.fetch import RAW_DIR, SOURCES
from data.sample_records import RECORDS as HAND_RECORDS

OUT_JSON = RAW_DIR.parent / "records.json"
NSP_FILE = "nsp_all_scholarships.html"
DTE_DEPARTMENT = "Directorate of Technical Education, Maharashtra"
STATUS_LINE = re.compile(r"^Scheme (Open|Closed|Yet)", re.I)  # e.g. "Scheme Open from : 01-06-2026"
EMPTY = (None, "", "VERIFY")
ACRONYMS = {"Aicte": "AICTE", "Pm": "PM", "Obc": "OBC", "Ebc": "EBC", "Dnt": "DNT",
            "Sc": "SC", "St": "ST", "Ner": "NER", "Ugc": "UGC"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class PageText(HTMLParser):
    """Collects the visible text lines, the <h3> headings and the <title>."""

    def __init__(self):
        super().__init__()
        self.lines = []
        self.h3 = []
        self.title = ""
        self._skip = 0
        self._in_h3 = False
        self._in_title = False
        self._h3_parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "h3":
            self._in_h3, self._h3_parts = True, []
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag == "h3":
            self._in_h3 = False
            heading = " ".join(self._h3_parts).strip()
            if heading:
                self.h3.append(heading)
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title += text
            return
        self.lines.append(text)
        if self._in_h3:
            self._h3_parts.append(text)


def tidy_name(name):
    """Clean spacing and fix words the NSP page writes in lowercase."""
    name = " ".join(name.split()).strip(" ]")
    name = re.sub(r"\s+Cs$", "", name)
    name = re.sub(r"\s*\((Welfare|Merit)[^)]*\)$", "", name)  # "(Welfare Based Scheme)"
    name = name.replace("'S", "'s").replace("( ", "(").replace(" )", ")")
    return re.sub(r"\b[A-Za-z]+\b", lambda m: ACRONYMS.get(m.group(0), m.group(0)), name)


def norm(name):
    """Key used to match the same scheme in different sources."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def make_record(scheme_name, department, eligible_category, income_limit, benefit, source_url):
    """Return one clean record dict, or raise ValueError if the row is bad."""
    scheme_name = tidy_name(scheme_name or "")
    if len(scheme_name) < 5:
        raise ValueError("scheme name missing or too short")
    if not department:
        raise ValueError(f"department missing for '{scheme_name}'")
    return {
        "id": 0,
        "scheme_name": scheme_name,
        "department": department.strip(),
        "eligible_category": eligible_category or "VERIFY",
        "income_limit": income_limit,
        "benefit": benefit or "VERIFY",
        "source_url": source_url,
        "verified": False,
    }


def parse_nsp(lines, url):
    """NSP list page: a department line, then scheme lines each followed by a
    status line such as 'Scheme Open from : 01-06-2026'."""
    records = []
    department = ""
    for i in range(len(lines) - 1):
        if not STATUS_LINE.match(lines[i + 1]):
            continue
        if i > 0 and lines[i - 1] != "FAQ":
            department = lines[i - 1]
        try:
            records.append(make_record(lines[i], department, None, None, None, url))
        except ValueError as error:
            logging.warning("NSP row skipped: %s", error)
    return records


def parse_dte(lines, headings, title, url):
    """One DTE scheme page -> one record (name from <h3>, income from 'x lakh')."""
    name = next((h for h in headings if re.search(r"scheme|scholarship|yojna", h, re.I)), None)
    if not name:
        name = title.split("–")[0]
    text = " ".join(lines)
    lakhs = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*lakhs?", text, re.I)]
    income = int(max(lakhs) * 100000) if lakhs else None
    groups = [g for g in ("EBC", "EWS", "SEBC") if re.search(rf"\b{g}\b", text)]
    category = " / ".join(groups) or None
    try:
        return [make_record(name, DTE_DEPARTMENT, category, income, None, url)]
    except ValueError as error:
        logging.warning("DTE page skipped (%s): %s", url, error)
        return []


def find_hand_key(key, hand_by_key):
    """Exact match first; otherwise the longest hand name contained in this name
    (the NSP page adds suffixes such as '(Welfare Based Scheme)')."""
    if key in hand_by_key:
        return key
    contained = [k for k in hand_by_key if k in key]
    return max(contained, key=len) if contained else None


def enrich(record, hand_by_key):
    """Fill empty fields from the matching hand-collected record.
    Returns the matched hand key, or None."""
    hand_key = find_hand_key(norm(record["scheme_name"]), hand_by_key)
    if not hand_key:
        return None
    hand = hand_by_key[hand_key]
    for field in ("eligible_category", "income_limit", "benefit"):
        if record[field] in EMPTY and hand[field] not in EMPTY:
            record[field] = hand[field]
    record["verified"] = hand["verified"]
    return hand_key


def ingest(raw_dir=RAW_DIR, out_path=OUT_JSON):
    hand_by_key = {norm(r["scheme_name"]): r for r in HAND_RECORDS}
    parsed = []

    for filename, url in SOURCES.items():
        try:
            html = (raw_dir / filename).read_text(encoding="utf-8", errors="ignore")
            page = PageText()
            page.feed(html)
            if filename == NSP_FILE:
                found = parse_nsp(page.lines, url)
            else:
                found = parse_dte(page.lines, page.h3, page.title, url)
        except FileNotFoundError:
            logging.warning("%s not found - run: python -m app.fetch", filename)
            continue
        except Exception as error:  # bad file: log it and carry on
            logging.warning("Could not parse %s: %s", filename, error)
            continue
        logging.info("%s: %s records found", filename, len(found))
        parsed.extend(found)

    records, seen = [], set()
    for record in parsed:
        key = norm(record["scheme_name"])
        if key in seen:
            continue
        seen.add(key)
        matched = enrich(record, hand_by_key)
        if matched:
            seen.add(matched)
        records.append(record)

    for hand in HAND_RECORDS:  # hand rows the pages did not cover
        key = norm(hand["scheme_name"])
        if key not in seen:
            seen.add(key)
            records.append(dict(hand))

    for number, record in enumerate(records, start=1):
        record["id"] = number

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logging.info("Saved %s records to %s", len(records), out_path)
    return len(records)


if __name__ == "__main__":
    ingest()