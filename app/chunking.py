import hashlib
import logging
import re
from html.parser import HTMLParser

from app.fetch import RAW_DIR, SOURCES
from app.ingest import NSP_FILE, STATUS_LINE, PageText, tidy_name

CHUNK_WORDS = 120
OVERLAP_WORDS = 25
END_MARKERS = ("Sitemap", "Visitor Counter", "Terms And Conditions", "Last Updated On")
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "pre", "div", "section", "article", "br"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class BlockText(HTMLParser):
    """Reads a page as blocks of text: one block per paragraph, list item or heading,
    and one block per table row (cells joined with ' | ')."""

    def __init__(self):
        super().__init__()
        self.blocks = []
        self.h3 = []
        self._buf = []
        self._skip = 0
        self._row = None
        self._cell = None
        self._in_h3 = False
        self._h3_parts = []

    def _flush(self):
        text = " ".join(" ".join(self._buf).split())
        if text:
            self.blocks.append(text)
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "tr":
            self._flush()
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []
        elif tag in BLOCK_TAGS:
            self._flush()
            if tag == "h3":
                self._in_h3, self._h3_parts = True, []

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in ("td", "th"):
            if self._row is not None and self._cell is not None:
                self._row.append(" ".join(self._cell).strip())
            self._cell = None
        elif tag == "tr":
            if self._row and any(self._row):
                self.blocks.append(" | ".join(cell for cell in self._row if cell))
            self._row = None
        elif tag in BLOCK_TAGS:
            if tag == "h3":
                self._in_h3 = False
                heading = " ".join(self._h3_parts).strip()
                if heading:
                    self.h3.append(heading)
            self._flush()

    def handle_data(self, data):
        text = " ".join(data.split())
        if self._skip or not text:
            return
        if self._cell is not None:
            self._cell.append(text)
            return
        self._buf.append(text)
        if self._in_h3:
            self._h3_parts.append(text)


def split_blocks(blocks, size=CHUNK_WORDS, overlap=OVERLAP_WORDS):
    """Pack blocks into chunks of about `size` words. A short last block is repeated at the
    start of the next chunk (overlap), so a sentence at the border is not lost."""
    chunks = []
    current, count, fresh = [], 0, 0  # fresh = blocks added since the last cut

    def cut():
        nonlocal current, count, fresh
        if fresh:
            chunks.append("\n".join(current))
        carry = [current[-1]] if current and len(current[-1].split()) <= overlap else []
        current, count, fresh = carry, sum(len(b.split()) for b in carry), 0

    for block in blocks:
        words = block.split()
        if len(words) > size:  # one very long block: cut it by words
            if fresh:
                cut()
            step = size - overlap
            for i in range(0, len(words), step):
                chunks.append(" ".join(words[i:i + size]))
                if i + size >= len(words):
                    break
            current, count, fresh = [], 0, 0
            continue
        if count + len(words) > size and fresh:
            cut()
        current.append(block)
        count += len(words)
        fresh += 1
    if fresh:
        chunks.append("\n".join(current))
    return chunks


def make_chunk(source, title, index, text):
    key = f"{source}|{index}|{text}".encode("utf-8")
    return {
        "id": hashlib.sha1(key).hexdigest()[:16],
        "text": text,
        "source": source,
        "page": 1,
        "title": title,
        "chunk_index": index,
    }


def dte_chunks(html, source):
    """Chunks of one DTE scheme page: the text under the scheme heading, up to the footer."""
    page = BlockText()
    page.feed(html)
    heading = next((h for h in page.h3
                    if re.search(r"scheme|scholarship|yojna|allowance", h, re.I)), None)
    if not heading:
        raise ValueError("no scheme heading found")
    clean = heading.strip(" ]")
    start = next((i for i, block in enumerate(page.blocks) if block.strip(" ]") == clean), None)
    if start is None:
        raise ValueError("heading not found in the page text")
    end = next((i for i in range(start + 1, len(page.blocks))
                if page.blocks[i].startswith(END_MARKERS)), len(page.blocks))
    pieces = split_blocks(page.blocks[start + 1:end])
    if not pieces:
        raise ValueError("no text under the heading")
    title = tidy_name(heading)
    return [make_chunk(source, title, n, text) for n, text in enumerate(pieces)]


def nsp_chunks(lines, source):
    """One chunk per scheme on the NSP list: name, department and the open/closing dates."""
    chunks = []
    department = ""
    for i in range(len(lines) - 1):
        if not STATUS_LINE.match(lines[i + 1]):
            continue
        if i > 0 and lines[i - 1] != "FAQ":
            department = lines[i - 1]
        name = re.sub(r"\s+Cs$", "", tidy_name(lines[i]))  # the NSP page ends some names with "Cs"
        name = name.replace("( ", "(").replace(" )", ")")
        dates = []
        for line in lines[i + 1:i + 8]:
            if line in ("Specifications", "FAQ"):
                break
            dates.append(line)
        text = f"{name}. Department: {department}. " + " ".join(dates)
        chunks.append(make_chunk(source, name, len(chunks), text))
    return chunks


def build_chunks(raw_dir=RAW_DIR):
    """Chunks of every downloaded page. Pages that are missing or unreadable are skipped."""
    chunks = []
    for filename, url in SOURCES.items():
        try:
            html = (raw_dir / filename).read_text(encoding="utf-8", errors="ignore")
            if filename == NSP_FILE:
                page = PageText()
                page.feed(html)
                found = nsp_chunks(page.lines, url)
            else:
                found = dte_chunks(html, url)
        except FileNotFoundError:
            logging.warning("%s not found - run: python -m app.fetch", filename)
            continue
        except ValueError as error:
            logging.warning("%s skipped: %s", filename, error)
            continue
        logging.info("%s: %s chunks", filename, len(found))
        chunks.extend(found)
    return chunks


if __name__ == "__main__":
    all_chunks = build_chunks()
    print(f"{len(all_chunks)} chunks from {len({c['source'] for c in all_chunks})} sources")
    for chunk in all_chunks[:3]:
        print(f"- [{chunk['title'][:50]}] page {chunk['page']}, chunk {chunk['chunk_index']}: "
              f"{chunk['text'][:90]}...")