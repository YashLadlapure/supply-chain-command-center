"""Find the knowledge cards that best match a question.

Two rankings are combined: one by meaning (embedding similarity) and one by
keywords (PostgreSQL full-text search). A card that either ranking puts near
the top ends up near the top overall.

Try it:
    python rag/retrieve.py "otif north region"
"""

import sys

import numpy as np

from build_index import embed
from db import connect

RRF_K = 60  # the usual constant for reciprocal rank fusion

CARDS_SQL = """
    SELECT title, content, embedding,
           ts_rank(
               to_tsvector('english', title || ' ' || content),
               -- match cards that contain any of the question's words, not all of them
               replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery
           ) AS keyword_score
    FROM rag_chunks
    ORDER BY chunk_id
"""


def search(question, k=5):
    """Return the k best cards for a question, best first."""
    query = np.array(embed([f"search_query: {question}"])[0])

    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute(CARDS_SQL, (question,))
        rows = cur.fetchall()
    conn.close()
    if not rows:
        raise SystemExit("The index is empty. Run: python rag/build_index.py")

    vectors = np.array([row[2] for row in rows])
    meaning = vectors @ query / (np.linalg.norm(vectors, axis=1) * np.linalg.norm(query))
    keyword = np.array([row[3] for row in rows])

    # Reciprocal rank fusion: each ranking gives a card 1 / (60 + its rank).
    # A card with no keyword match gets nothing from the keyword ranking.
    meaning_rank = (-meaning).argsort().argsort()
    keyword_rank = (-keyword).argsort().argsort()
    fused = 1 / (RRF_K + meaning_rank) + np.where(keyword > 0, 1 / (RRF_K + keyword_rank), 0)

    best = fused.argsort()[::-1][:k]
    return [
        {"title": rows[i][0], "content": rows[i][1], "similarity": float(meaning[i])}
        for i in best
    ]


if __name__ == "__main__":
    for card in search(" ".join(sys.argv[1:]) or "otif north region"):
        print(f"{card['similarity']:.3f}  {card['title']}")
