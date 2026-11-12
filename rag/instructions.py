"""The instructions sent with every question, and the schema-only note for the baseline."""

from pathlib import Path

INSTRUCTIONS = """You write one PostgreSQL query that answers a question about a supply-chain database.

Rules:
1. Use only the tables, columns, KPI formulas and business rules in the reference notes.
2. When a KPI is named, follow its formula exactly, including its grain and filters.
3. Write a single SELECT statement. Never change data.
4. If the notes do not contain the data the question needs, set "sql" to null and say why.

Reply with JSON only, in this shape:
{{"sql": "SELECT ...", "explanation": "what the query calculates, in one plain sentence"}}

Reference notes:
{notes}

Question: {question}
"""

# Used for the baseline run: the model sees the table definitions but none of the cards
SCHEMA_ONLY_NOTE = {
    "title": "Database schema",
    "content": (Path(__file__).resolve().parents[1] / "sql" / "schema.sql").read_text(encoding="utf-8"),
    "similarity": 1.0,
}
