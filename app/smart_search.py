import re
from functools import lru_cache

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.records import load_records

SEARCH_FIELDS = ("scheme_name", "department", "eligible_category", "benefit")


def record_text(record):
    """The text of one record that gets searched ('VERIFY' placeholders are left out)."""
    parts = []
    for field in SEARCH_FIELDS:
        value = record.get(field)
        if value and value != "VERIFY":
            parts.append(str(value))
    return " ".join(parts)


def tokenize(text):
    """Lowercase words without stop words; 'girls' and 'girl' become the same word."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    words = [w for w in words if w not in ENGLISH_STOP_WORDS]
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in words]


class SmartSearch:
    def __init__(self, records):
        self.records = records
        self.vectorizer = TfidfVectorizer(
            tokenizer=tokenize, lowercase=False, token_pattern=None, ngram_range=(1, 2)
        )
        texts = [record_text(r) for r in records]
        self.matrix = self.vectorizer.fit_transform(texts) if texts else None

    def search(self, query, top_k=5):
        """Return up to top_k records, best match first, each with a 'score' (0 to 1)."""
        if self.matrix is None or not query.strip():
            return []
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        results = []
        for index in (-scores).argsort(kind="stable")[:top_k]:
            if scores[index] <= 0:
                break
            results.append({**self.records[index], "score": round(float(scores[index]), 4)})
        return results


@lru_cache(maxsize=1)
def get_index():
    """Build the TF-IDF index once, from the current records."""
    return SmartSearch(load_records())


def smart_search(query, top_k=5):
    return get_index().search(query, top_k)