"""Answer a question about the supply-chain data with a checked, read-only SQL query.

    python rag/ask.py "What was OTIF for orders from North region warehouses?"

The model only writes SQL. The guard checks it, and a read-only database user runs it.
"""

import json
import os
import sys
import time

import psycopg2
import requests
import sqlglot
from sqlglot import exp

from db import connect
from guard import MAX_ROWS, UnsafeQuery, check
from instructions import INSTRUCTIONS, SCHEMA_ONLY_NOTE
from retrieve import search

# 127.0.0.1, not localhost: on Windows, localhost tries IPv6 first and adds about 2 seconds per call
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
CHAT_MODEL = "qwen2.5:7b"
MIN_SIMILARITY = 0.45  # below this, no card is close enough; tune it with the test set


def generate(question, cards, error=None):
    """Ask the model for SQL. Returns the parsed JSON reply."""
    notes = "\n\n".join(f"### {card['title']}\n{card['content']}" for card in cards)
    message = INSTRUCTIONS.format(notes=notes, question=question)
    if error:
        message += f"\n\nYour last SQL failed with this error:\n{error}\nWrite a corrected query."
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": [{"role": "user", "content": message}],
                "format": "json",
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=180,
        )
    except requests.ConnectionError:
        raise SystemExit(f"Ollama is not running at {OLLAMA_URL}. Start the Ollama app and try again.")
    response.raise_for_status()
    return json.loads(response.json()["message"]["content"])


def is_nonanswer(sql):
    """A weak model sometimes writes its refusal as 'SELECT NULL' instead of setting sql to null.
    Spot a query that reads no table and only returns NULL or literal text, so it reads as a refusal."""
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return False
    if not isinstance(tree, exp.Select) or tree.args.get("from"):
        return False
    return all(isinstance(p.unalias() if isinstance(p, exp.Alias) else p, (exp.Null, exp.Literal))
               for p in tree.expressions)


def run_sql(sql):
    """Run the checked SQL as the read-only user, capped at MAX_ROWS rows."""
    conn = connect(read_only=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM ({sql}) AS result LIMIT {MAX_ROWS}")
            return [column.name for column in cur.description], cur.fetchall()
    finally:
        conn.close()


def ask(question, use_retrieval=True):
    started = time.time()
    cards = search(question) if use_retrieval else [SCHEMA_ONLY_NOTE]
    answer = {
        "question": question, "sources": [card["title"] for card in cards],
        "refused": False, "reason": None, "sql": None, "explanation": None,
        "columns": [], "rows": [],
    }

    def finish(**changes):
        answer.update(changes, seconds=round(time.time() - started, 1))
        return answer

    if use_retrieval and cards[0]["similarity"] < MIN_SIMILARITY:
        return finish(refused=True, reason="Nothing in the knowledge base covers this question.")

    error = None
    for _ in range(2):  # first try, then one retry that shows the model its own error
        reply = generate(question, cards, error)
        if not reply.get("sql") or is_nonanswer(reply["sql"]):
            return finish(refused=True, reason=reply.get("explanation") or "The data does not cover this.")
        try:
            safe_sql = check(reply["sql"])
            columns, rows = run_sql(safe_sql)
            return finish(sql=safe_sql, explanation=reply.get("explanation"), columns=columns, rows=rows)
        except (UnsafeQuery, psycopg2.Error) as exc:
            error = str(exc)
    return finish(refused=True, reason=f"Could not build a working query: {error}")


if __name__ == "__main__":
    print(json.dumps(ask(" ".join(sys.argv[1:]) or "What is our OTIF?"), indent=2, default=str))
