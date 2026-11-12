"""Score the question set two ways and save the results.

    python rag/eval/run_eval.py

For every test question it runs the ask tool twice:
  baseline   - the model sees only the table schema
  retrieval  - the model also sees the matching knowledge cards

A question is correct when:
  value   - the answer returns a number within `tolerance` of `expected`
  list    - the answer returns exactly these names, in this order
  refuse  - the answer refuses, because the data cannot cover it

Results are written to rag/eval/results/ as JSON, and a summary is printed.
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

import yaml

RAG_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAG_DIR))

from ask import ask  # noqa: E402  (needs rag/ on sys.path first)

QUESTIONS = RAG_DIR / "eval" / "questions.yaml"
RESULTS_DIR = RAG_DIR / "eval" / "results"


def numbers_in_first_row(rows):
    """Every numeric cell in the first row. A value answer may also carry
    label or breakdown columns, so the metric is not always the first cell."""
    if not rows:
        return []
    return [float(cell) for cell in rows[0]
            if isinstance(cell, (int, float, Decimal)) and not isinstance(cell, bool)]


def names_in_order(rows, how_many):
    """The first text cell of each row, in row order, up to how_many."""
    out = []
    for row in rows[:how_many]:
        for cell in row:
            if isinstance(cell, str):
                out.append(cell.strip())
                break
    return out


def grade(question, answer):
    """True when the answer matches the expected result for this question type."""
    kind = question["type"]
    if kind == "refuse":
        return bool(answer["refused"])
    if answer["refused"]:
        return False  # a value/list question that the model refused is wrong
    if kind == "value":
        want, tol = float(question["expected"]), float(question["tolerance"])
        return any(abs(got - want) <= tol for got in numbers_in_first_row(answer["rows"]))
    if kind == "list":
        want = [str(name) for name in question["expected"]]
        return names_in_order(answer["rows"], len(want)) == want
    return False


def cards_found(question, answer):
    """How many of the expected cards the retrieval actually surfaced."""
    expected = question.get("expected_cards", [])
    sources = set(answer["sources"])
    hit = sum(1 for card in expected if card in sources)
    return hit, len(expected)


def run_mode(questions, use_retrieval):
    rows = []
    for q in questions:
        try:
            answer = ask(q["question"], use_retrieval=use_retrieval)
            error = None
        except Exception as exc:  # keep going; one bad question should not stop the run
            answer = {"refused": True, "reason": str(exc), "sources": [], "rows": [],
                      "columns": [], "sql": None, "seconds": 0}
            error = str(exc)
        correct = grade(q, answer)
        hit, total = cards_found(q, answer)
        rows.append({
            "id": q["id"], "type": q["type"], "question": q["question"],
            "correct": correct, "refused": answer["refused"],
            "cards_hit": hit, "cards_expected": total,
            "sql": answer.get("sql"), "sources": answer["sources"],
            "result_rows": answer["rows"][:5], "seconds": answer.get("seconds"),
            "error": error,
        })
        mark = "ok " if correct else "BAD"
        print(f"  {mark} [{q['type']:6}] {q['id']}", flush=True)
    return rows


def totals(rows):
    answerable = [r for r in rows if r["type"] != "refuse"]
    refusals = [r for r in rows if r["type"] == "refuse"]
    secs = [r["seconds"] for r in rows if r["seconds"]]
    return {
        "answerable_correct": sum(r["correct"] for r in answerable),
        "answerable_total": len(answerable),
        "refuse_correct": sum(r["correct"] for r in refusals),
        "refuse_total": len(refusals),
        "avg_seconds": round(sum(secs) / len(secs), 1) if secs else 0,
    }


def main():
    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Baseline (schema only):")
    baseline = run_mode(questions, use_retrieval=False)
    print("Retrieval (schema + cards):")
    retrieval = run_mode(questions, use_retrieval=True)

    (RESULTS_DIR / "baseline.json").write_text(
        json.dumps(baseline, indent=2, default=str), encoding="utf-8")
    (RESULTS_DIR / "retrieval.json").write_text(
        json.dumps(retrieval, indent=2, default=str), encoding="utf-8")

    card_rows = [r for r in retrieval if r["cards_expected"]]
    summary = {
        "baseline": totals(baseline),
        "retrieval": totals(retrieval),
        "cards_all_found": sum(r["cards_hit"] == r["cards_expected"] for r in card_rows),
        "cards_questions": len(card_rows),
    }
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    b, r = summary["baseline"], summary["retrieval"]
    print("\n=== SUMMARY ===")
    print(f"Answerable correct:  baseline {b['answerable_correct']}/{b['answerable_total']}"
          f"   retrieval {r['answerable_correct']}/{r['answerable_total']}")
    print(f"Refusals correct:    baseline {b['refuse_correct']}/{b['refuse_total']}"
          f"   retrieval {r['refuse_correct']}/{r['refuse_total']}")
    print(f"Expected cards found: {summary['cards_all_found']}/{summary['cards_questions']}")
    print(f"Avg seconds/question: baseline {b['avg_seconds']}   retrieval {r['avg_seconds']}")


if __name__ == "__main__":
    main()
