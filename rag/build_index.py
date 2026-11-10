"""Split the knowledge cards, embed them and store them in rag_chunks.

Run it again every time a card changes:
    python rag/build_index.py

Ollama must be running, with the embedding model pulled once:
    ollama pull nomic-embed-text
"""

import os
from pathlib import Path

import requests

from db import connect

RAG_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = RAG_DIR / "knowledge"
# 127.0.0.1, not localhost: on Windows, localhost tries IPv6 first and adds about 2 seconds per call
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = "nomic-embed-text"


def split_cards(path):
    """Each '## ' heading starts a new card. Returns (title, content) pairs."""
    cards, title, lines = [], None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if title:
                cards.append((title, "\n".join(lines).strip()))
            title, lines = line[3:].strip(), []
        elif title:
            lines.append(line)
    if title:
        cards.append((title, "\n".join(lines).strip()))
    return cards


def embed(texts):
    """Return one embedding (a list of numbers) per text."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": texts},
            timeout=300,
        )
    except requests.ConnectionError:
        raise SystemExit(f"Ollama is not running at {OLLAMA_URL}. Start the Ollama app and try again.")
    if response.status_code == 404:
        raise SystemExit(f"The embedding model is missing. Run: ollama pull {EMBED_MODEL}")
    response.raise_for_status()
    return response.json()["embeddings"]


def main():
    rows = [
        (path.name, title, content)
        for path in sorted(KNOWLEDGE_DIR.glob("*.md"))
        for title, content in split_cards(path)
    ]
    # nomic-embed-text expects this prefix on stored documents
    vectors = embed([f"search_document: {title}\n{content}" for _, title, content in rows])

    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute((RAG_DIR / "schema.sql").read_text(encoding="utf-8"))
        cur.execute("TRUNCATE rag_chunks RESTART IDENTITY")
        for (source, title, content), vector in zip(rows, vectors):
            cur.execute(
                "INSERT INTO rag_chunks (source, title, content, embedding) VALUES (%s, %s, %s, %s)",
                (source, title, content, vector),
            )
    conn.close()
    print(f"Indexed {len(rows)} cards")


if __name__ == "__main__":
    main()
