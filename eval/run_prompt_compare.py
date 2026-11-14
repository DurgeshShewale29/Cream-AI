import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm import LLMError, get_model, get_provider  # noqa: E402
from app.main import answer_question  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = BASE_DIR / "docs" / "how_llms_work.md"
OUT_FILE = BASE_DIR / "eval" / "prompt_compare.md"
VERSIONS = ("v1", "v2")
PAUSE = 2  # seconds between calls, to stay inside the free rate limit


def load_questions():
    """The numbered questions under '## ScholarSetu user questions' in the notes file."""
    text = QUESTIONS_FILE.read_text(encoding="utf-8")
    section = text.split("## ScholarSetu user questions")[-1]
    questions = []
    for line in section.splitlines():
        match = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if match:
            questions.append(re.sub(r"\s*\*\(.*\)\*\s*$", "", match.group(1)).strip())
    return questions


def run(questions):
    results = {version: [] for version in VERSIONS}
    for number, question in enumerate(questions, start=1):
        for version in VERSIONS:
            try:
                reply, valid = answer_question(question, version)
                results[version].append({"reply": reply, "valid": valid, "error": None})
            except LLMError as error:
                if number == 1 and version == VERSIONS[0]:
                    raise SystemExit(f"The first call failed: {error}\n"
                                     "Fix the key or model name in .env and run again. Nothing was written.")
                results[version].append({"reply": None, "valid": False, "error": str(error)})
            print(f"Q{number} {version} done")
            time.sleep(PAUSE)
    return results


def cell(item, limit=260):
    """One table cell: short, on one line, with no pipe characters."""
    if item["error"]:
        return f"ERROR: {item['error']}"[:limit]
    text = " ".join(item["reply"]["answer"].split()).replace("|", "/")
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return f"{text} ({item['reply']['confidence']})"


def summary_rows(results, total):
    def stat(version):
        items = results[version]
        ok = [i for i in items if i["reply"]]
        words = [len(i["reply"]["answer"].split()) for i in ok]
        confidence = {c: sum(1 for i in ok if i["reply"]["confidence"] == c)
                      for c in ("high", "medium", "low")}
        return {
            "valid": f"{sum(1 for i in ok if i['valid'])}/{total}",
            "words": f"{sum(words) / len(words):.0f}" if words else "-",
            "conf": f"{confidence['high']} / {confidence['medium']} / {confidence['low']}",
            "follow": f"{sum(1 for i in ok if i['reply']['follow_up'])}/{total}",
            "errors": f"{total - len(ok)}/{total}",
        }
    a, b = stat("v1"), stat("v2")
    return [
        ("Replies that were valid JSON", a["valid"], b["valid"]),
        ("Average answer length (words)", a["words"], b["words"]),
        ("Confidence high / medium / low", a["conf"], b["conf"]),
        ("Replies with a follow-up question", a["follow"], b["follow"]),
        ("Calls that failed", a["errors"], b["errors"]),
    ]


def write_report(questions, results):
    total = len(questions)
    lines = [
        "# Prompt comparison: v1 vs v2",
        "",
        f"Run on {date.today().isoformat()} with {get_provider()} / {get_model(get_provider())}, "
        f"on the {total} ScholarSetu questions from `docs/how_llms_work.md`.",
        "",
        "## The two prompt versions",
        "- **v1** (`prompts/task_v1.txt`): a short prompt that only asks for the answer in JSON.",
        "- **v2** (`prompts/task_v2.txt`): a step by step prompt. It tells the model to note the student's "
        "details, name only schemes it is sure of, never guess amounts or dates, say so when a question is "
        "not about scholarships, and use a fixed rule for the confidence value.",
        "",
        "## Numbers counted by the script",
        "| Measure | v1 | v2 |",
        "|---|---|---|",
    ]
    lines += [f"| {name} | {a} | {b} |" for name, a, b in summary_rows(results, total)]
    lines += ["", "## Answers side by side",
              "Read both answers, then fill in the Better (v1 or v2) and Why columns.", "",
              "| # | Question | v1 answer (confidence) | v2 answer (confidence) | Better | Why |",
              "|---|---|---|---|---|---|"]
    for i, question in enumerate(questions):
        q = question.replace("|", "/")
        lines.append(f"| {i + 1} | {q} | {cell(results['v1'][i])} | {cell(results['v2'][i])} |  |  |")
    lines += ["", "## Full answers"]
    for i, question in enumerate(questions):
        lines += ["", f"### Q{i + 1}. {question}"]
        for version in VERSIONS:
            item = results[version][i]
            if item["error"]:
                lines.append(f"- **{version}:** ERROR: {item['error']}")
            else:
                reply = item["reply"]
                answer = " ".join(reply["answer"].split())
                lines.append(f"- **{version}** (confidence: {reply['confidence']}): {answer}")
                if reply["follow_up"]:
                    lines.append(f"  - follow-up: {reply['follow_up']}")
    lines += ["", "## My conclusion",
              "_Write 3 or 4 sentences here after reading the answers: which version is better, "
              "and what did you notice for Q6 (the question the data cannot answer)?_", ""]
    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main():
    questions = load_questions()
    if not questions:
        raise SystemExit("No questions found in docs/how_llms_work.md")
    results = run(questions)
    write_report(questions, results)
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()