import json
import logging
import re
from html.parser import HTMLParser

from app.fetch import RAW_DIR, SOURCES

OUT_JSON = RAW_DIR.parent / "records.json"
NSP_FILE = "nsp_all_scholarships.html"
DTE_DEPARTMENT = "Directorate of Technical Education, Maharashtra"
STATUS_LINE = re.compile(r"^Scheme (Open|Closed|Yet)", re.I)
END_MARKERS = ("Procedure", "The method", "Sitemap", "Visitor Counter", "Terms And Conditions",
               "Last Updated On")
BENEFIT_WORDS = r"scholarship|allowance|fee|waiver|reimburs|assistance|stipend|tuition"
CATEGORY_PATTERNS = [
    ("EBC", r"\bEBC\b|Economically Backward"),
    ("EWS", r"\bEWS\b|Economically Weaker"),
    ("SEBC", r"\bSEBC\b|Socially and Educationally Backward"),
    ("OBC", r"\bOBC\b"),
    ("SC", r"\bSC\b|Scheduled Castes?"),
    ("ST", r"\bST\b|Scheduled Tribes?"),
    ("VJNT", r"\bVJNT\b|\bVJ\b|\bNT\b"),
    ("Minority", r"minorit"),
    ("Girl students", r"\bgirls?\b|\bfemale"),
    ("Students with disabilities", r"disabilit|specially.abled|divyang"),
    ("Orphans and wards", r"orphan|\bwards?\b"),
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class PageText(HTMLParser):
    """Collects the visible text lines, table rows, <h3> headings and the <title>."""

    def __init__(self):
        super().__init__()
        self.lines = []
        self.rows = []
        self.h3 = []
        self.title = ""
        self._skip = 0
        self._in_h3 = False
        self._in_title = False
        self._h3_parts = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "h3":
            self._in_h3, self._h3_parts = True, []
        elif tag == "title":
            self._in_title = True
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []

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
        elif tag in ("td", "th"):
            if self._row is not None and self._cell is not None:
                self._row.append(" ".join(self._cell).strip())
            self._cell = None
        elif tag == "tr":
            if self._row:
                self.rows.append(self._row)
            self._row = None

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
        if self._cell is not None:
            self._cell.append(text)


def tidy_name(name):
    name = " ".join(name.split()).strip(" ]\"“”'")
    return re.sub(r"^\d+[.)]\s*", "", name)


def first_sentence(text, limit=200):
    return re.split(r"(?<=[.!?])\s", text.strip())[0][:limit]


def page_content(lines, heading):
    """The lines of the scheme text: after its heading, before the 'Procedure' part."""
    clean = heading.strip(" ]")
    start = next((i for i, line in enumerate(lines) if line.strip(" ]") == clean), None)
    if start is None:
        return []
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(END_MARKERS)),
               len(lines))
    return lines[start + 1:end]


def find_category(content):
    """Who the scheme is for, from the first paragraph of the page."""
    intro = next((line for line in content if len(line) >= 60), content[0] if content else "")
    intro = re.sub(r"boys?\s*(?:and|or|&)\s*girls?", "students", intro, flags=re.I)
    labels = [label for label, pattern in CATEGORY_PATTERNS if re.search(pattern, intro, re.I)]
    return " / ".join(labels) if labels else first_sentence(intro)


def find_income(text):
    """Highest annual family income limit mentioned, in rupees (None if not stated)."""
    values = [float(x) * 100000 for x in re.findall(r"(\d+(?:\.\d+)?)\s*lakhs?", text, re.I)]
    values += [int(x.replace(",", ""))
               for x in re.findall(r"income[^.]{0,120}?(?:Rs\.?|₹)\s*([\d,]{6,})", text, re.I)]
    return int(max(values)) if values else None


BENEFIT_HEADER = r"amount|fee|allowance|benefit"
HEADING = re.compile(r"^\W*(benefits?( to (the )?students)?|scholarship amount|amount of (the )?"
                     r"(scholarship|benefit)|rate of scholarship)\W*$", re.I)


def clean_money(text):
    """Write the rupee sign the same way everywhere and tidy the spaces."""
    text = text.replace("रु.", "Rs ").replace("₹", "Rs ")
    return " ".join(text.split())


def table_benefit(rows):
    """A table with a header like 'Academic fees' or 'Lump sum Amount' -> one line per row."""
    for i, header in enumerate(rows):
        if len(header) < 3 or not any(re.search(BENEFIT_HEADER, c, re.I) for c in header):
            continue
        data = []
        for row in rows[i + 1:]:
            if len(row) != len(header):
                break
            data.append(row)
        if not data:
            continue
        value_cols = [j for j, h in enumerate(header)
                      if re.search(BENEFIT_HEADER, h, re.I)
                      and all(re.search(r"\d", row[j]) for row in data)]
        if not value_cols:
            continue
        label_cols = [j for j in range(len(header)) if j not in value_cols
                      and not any(re.search(r"\d", row[j]) for row in data)
                      and all(len(row[j]) > 3 for row in data)
                      and (len(data) == 1 or len({row[j] for row in data}) > 1)]
        parts = []
        for row in data:
            values = ", ".join(f"{header[j]} {row[j]}" for j in value_cols)
            label = " ".join(row[j] for j in label_cols)
            parts.append(f"{label}: {values}" if label else values)
        return "; ".join(parts)
    return None


def total_row_benefit(rows):
    """A row such as 'Total amount | 60,000/- | 51,000/-' (rupees only, not seat counts)."""
    for row in rows:
        for i, cell in enumerate(row):
            if not re.match(r"total", cell, re.I):
                continue
            rest = row[i + 1:]
            if not any(re.search(r"/-|,|Rs|₹|रु", c) for c in rest):
                continue
            amounts = [int(n.replace(",", "")) for c in rest
                       for n in re.findall(r"[0-9][0-9,]*", c) if n.replace(",", "")]
            if amounts:
                low, high = min(amounts), max(amounts)
                return f"Total amount Rs {low:,}" if low == high else f"Total amount Rs {low:,} to Rs {high:,}"
    return None


def heading_benefit(lines):
    """The few lines under a heading such as 'Benefits to students:'."""
    for i, line in enumerate(lines):
        if not HEADING.match(line):
            continue
        picked = []
        for nxt in lines[i + 1:]:
            if re.match(r"(helpline|eligibility|procedure|how to)", nxt, re.I) or HEADING.match(nxt):
                break
            if len(nxt) > 3:
                picked.append(nxt.strip(" •-–"))
            if len(picked) == 4:
                break
        if picked:
            joined = "; ".join(picked)
            if len(joined) > 300:  # cut between items, not in the middle of one
                joined = joined[:300].rsplit(";", 1)[0]
            return joined
    return None


def find_benefit(rows, content):
    """What the student gets, trying the most reliable layouts first."""
    benefit = table_benefit(rows) or total_row_benefit(rows)
    if benefit:
        return clean_money(benefit)

    cells = {cell for row in rows for cell in row}
    lines = [line for line in content if line not in cells]  # text outside the tables
    benefit = heading_benefit(lines)
    if benefit:
        return clean_money(benefit)

    text = clean_money(" ".join(lines))
    text = re.sub(r"\bRs\.\s*", "Rs ", text)  # so "Rs. 50,000" is not cut in two
    sentences = [s.strip() for s in re.split(r"(?<=[.;])\s+|•", text) if s.strip()]
    for sentence in sentences:  # an amount or percentage next to a benefit word
        if (re.search(r"Rs\s*[\d,]+|\d+\s*%|per (annum|year|month)", sentence, re.I)
                and re.search(BENEFIT_WORDS, sentence, re.I)):
            return sentence[:220]
    for sentence in sentences[1:]:  # first sentence about the benefit after the intro
        if re.search(BENEFIT_WORDS, sentence, re.I):
            return sentence[:220]
    return None


def make_record(scheme_name, eligible_category, income_limit, benefit, source_url):
    """Return one clean record dict, or raise ValueError if the page is incomplete."""
    scheme_name = tidy_name(scheme_name or "")
    if len(scheme_name) < 5:
        raise ValueError("scheme name missing or too short")
    if not eligible_category:
        raise ValueError(f"no eligible category found for '{scheme_name}'")
    if not benefit:
        raise ValueError(f"no benefit found for '{scheme_name}'")
    return {
        "id": 0,
        "scheme_name": scheme_name,
        "department": DTE_DEPARTMENT,
        "eligible_category": eligible_category,
        "income_limit": income_limit,
        "benefit": benefit,
        "source_url": source_url,
        "verified": True,  # read from the official DTE page
    }


def parse_dte(page, url):
    """One DTE scheme page -> one record."""
    name = next((h for h in page.h3
                 if re.search(r"scheme|scholarship|yojna|allowance", h, re.I)), None)
    if not name:
        raise ValueError("no scheme heading found")
    content = page_content(page.lines, name)
    if not content:
        raise ValueError("no page text found under the heading")
    return make_record(
        name,
        find_category(content),
        find_income(" ".join(content)),
        find_benefit(page.rows, content),
        url,
    )


def count_nsp_schemes(lines):
    """Number of schemes listed on the NSP page (a scheme line is followed by a status line)."""
    return sum(1 for i in range(len(lines) - 1) if STATUS_LINE.match(lines[i + 1]))


def ingest(raw_dir=RAW_DIR, out_path=OUT_JSON):
    records = []
    for filename, url in SOURCES.items():
        try:
            html = (raw_dir / filename).read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            logging.warning("%s not found - run: python -m app.fetch", filename)
            continue
        page = PageText()
        try:
            page.feed(html)
            if filename == NSP_FILE:
                logging.info("%s: %s schemes listed. Skipped: the list has only names and "
                             "dates; benefits are in guideline PDFs that NSP does not allow "
                             "scripts to download", filename, count_nsp_schemes(page.lines))
                continue
            record = parse_dte(page, url)
        except ValueError as error:  # incomplete page: skip it
            logging.warning("%s skipped: %s", filename, error)
            continue
        except Exception as error:  # broken file: log it and carry on
            logging.warning("Could not parse %s: %s", filename, error)
            continue
        if record["income_limit"] is None:
            logging.warning("%s: no income limit stated on the page", filename)
        records.append(record)

    for number, record in enumerate(records, start=1):
        record["id"] = number

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logging.info("Saved %s records to %s", len(records), out_path)
    return records


if __name__ == "__main__":
    for r in ingest():
        limit = f"Rs {r['income_limit']:,}" if r["income_limit"] else "none stated"
        print(f"{r['id']:>2}. {r['scheme_name'][:60]}")
        print(f"     for: {r['eligible_category'][:70]} | limit: {limit}")
        print(f"     benefit: {r['benefit'][:100]}")