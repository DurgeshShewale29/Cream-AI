import json
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import rag, vectorstore  # noqa: E402
from app.llm import LLMError  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
EVAL_SET = BASE_DIR / "eval" / "eval_set.json"
OUT_FILE = BASE_DIR / "eval" / "eval_results.md"
CONFIGS = [
    {"name": "A", "chunk_words": 120, "top_k": 3},
    {"name": "B", "chunk_words": 60, "top_k": 5},
]
PAUSE = 5  # seconds between calls, to stay inside the free rate limit


def clean(text):
    """Lowercase text with the odd characters some models write (no-break spaces, special
    hyphens, zero-width characters) turned into plain ones, so keywords can be matched."""
    text = unicodedata.normalize("NFKC", text)
    for dash in "\u2010\u2011\u2012\u2013\u2014":
        text = text.replace(dash, "-")
    for hidden in "\u200b\u200c\u200d\ufeff":
        text = text.replace(hidden, "")
    return " ".join(text.split()).lower()


def judge(row, result):
    """(retrieval hit, answer correct) for one question.
    Answerable question: correct = the model answered, cited a source and the answer holds
    one of the expected keywords. Unanswerable question: correct = it said "I don't know"."""
    if row["answerable"]:
        sources = {item["source"] for item in result["retrieved"]}
        hit = bool(sources & set(row["expected_sources"]))
        answer = clean(result["answer"])
        correct = (result["answerable"] and bool(result["citations"])
                   and any(clean(k) in answer for k in row["expected_keywords"]))
        return hit, correct
    return None, not result["answerable"]


def evaluate(config, rows):
    vectorstore.build_index(config["chunk_words"])  # a fresh index for this chunk size
    records = []
    for row in rows:
        started = time.time()
        try:
            result = rag.answer_question(row["question"], config["top_k"], config["chunk_words"])
            error = None
        except LLMError as problem:  # a failed call counts as a wrong answer
            result = {"answer": "", "answerable": False, "citations": [], "retrieved": []}
            error = str(problem)
        seconds = time.time() - started
        hit, correct = judge(row, result)
        if error:
            correct = False
        records.append({"row": row, "result": result, "hit": hit, "correct": correct,
                        "seconds": seconds, "error": error})
        print(f"Config {config['name']} - question {row['id']} done")
        time.sleep(PAUSE)
    return records


def summarise(config, records):
    answerable = [r for r in records if r["row"]["answerable"]]
    unanswerable = [r for r in records if not r["row"]["answerable"]]
    return {
        "config": config,
        "hits": sum(1 for r in answerable if r["hit"]),
        "answers": sum(1 for r in answerable if r["correct"]),
        "idk": sum(1 for r in unanswerable if r["correct"]),
        "overall": sum(1 for r in records if r["correct"]),
        "answerable_n": len(answerable),
        "unanswerable_n": len(unanswerable),
        "total": len(records),
        "avg_seconds": sum(r["seconds"] for r in records) / len(records),
    }


def pick_winner(summaries):
    """Most correct answers; then the better retrieval hit-rate; then the faster one."""
    return max(summaries, key=lambda s: (s["overall"], s["hits"], -s["avg_seconds"]))


def readme_section(summaries):
    first = summaries[0]
    winner = pick_winner(summaries)
    lines = [
        "## RAG evaluation",
        f"{first['total']} questions from `eval/eval_set.json` ({first['answerable_n']} that the sources "
        f"can answer, {first['unanswerable_n']} that they cannot). Two configurations were run on the "
        "same questions with `python eval/run_eval.py`.",
        "",
        "| Config | Chunk size | Top-k | Retrieval hit-rate | Answers correct | \"I don't know\" correct | Overall | Avg time per question |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        c = s["config"]
        lines.append(f"| {c['name']} | {c['chunk_words']} words | {c['top_k']} | "
                     f"{s['hits']}/{s['answerable_n']} | {s['answers']}/{s['answerable_n']} | "
                     f"{s['idk']}/{s['unanswerable_n']} | {s['overall']}/{s['total']} | "
                     f"{s['avg_seconds']:.1f} s |")
    c = winner["config"]
    lines += ["", f"**Winner: config {c['name']}** (chunk size {c['chunk_words']} words, top-k {c['top_k']}) "
                  f"with {winner['overall']}/{winner['total']} correct answers."]
    return "\n".join(lines)


def snippet(record, limit=110):
    if record["error"]:
        return f"ERROR: {record['error']}"[:limit]
    text = " ".join(record["result"]["answer"].split()).replace("|", "/")
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def write_details(summaries, all_records):
    lines = [readme_section(summaries), "", "## Every question",
             "| # | Question | Expected | " + " | ".join(
                 f"Config {s['config']['name']}: answer (correct / retrieval hit)" for s in summaries) + " |",
             "|---|---|---|" + "---|" * len(summaries)]
    for index, row in enumerate(all_records[0]):
        cells = []
        for records in all_records:
            r = records[index]
            hit = "-" if r["hit"] is None else ("yes" if r["hit"] else "no")
            cells.append(f"{snippet(r)} ({'yes' if r['correct'] else 'no'} / {hit})")
        expected = row["row"]["expected_answer"].replace("|", "/")
        question = row["row"]["question"].replace("|", "/")
        lines.append(f"| {row['row']['id']} | {question} | {expected} | " + " | ".join(cells) + " |")
    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_model():
    """One small call before the long run, so a wrong key or model name stops it at once."""
    try:
        rag.ask_llm("Reply with JSON only.", 'Reply with {"ok": true}',
                    temperature=0.0, max_tokens=300, json_mode=True)
    except LLMError as problem:
        raise SystemExit(f"The model check failed: {problem}\n"
                         "Fix the key or model name in .env and run again. Nothing was written.")


def main():
    rows = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    check_model()
    try:
        all_records = [evaluate(config, rows) for config in CONFIGS]
    except RuntimeError as error:  # includes EmbeddingError and a missing index
        raise SystemExit(f"{error}\nNothing was written.")
    summaries = [summarise(config, records) for config, records in zip(CONFIGS, all_records)]
    write_details(summaries, all_records)
    print()
    print("Copy this into README.md:")
    print()
    print(readme_section(summaries))
    print()
    print(f"Details saved in {OUT_FILE}")


if __name__ == "__main__":
    main()