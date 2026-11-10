-- Storage for the knowledge cards and their embeddings.
-- rag/build_index.py runs this file itself, so there is no need to run it by hand.
CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id  SERIAL PRIMARY KEY,
    source    TEXT NOT NULL,      -- which file the card came from
    title     TEXT NOT NULL,      -- the card's ## heading
    content   TEXT NOT NULL,
    embedding REAL[] NOT NULL     -- 768 numbers from nomic-embed-text
);
