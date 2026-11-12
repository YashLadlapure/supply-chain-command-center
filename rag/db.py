"""Database connections built from the settings in .env."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def connect(read_only=False):
    """read_only=True connects as rag_reader, the user that can only run SELECT."""
    prefix = "RAG_DB" if read_only else "DB"
    user = os.getenv(f"{prefix}_USER", "rag_reader" if read_only else "postgres")
    password = os.getenv(f"{prefix}_PASSWORD")
    if not password:
        raise SystemExit(f"{prefix}_PASSWORD is not set. Copy .env.example to .env and fill it in.")
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "supply_chain"),
        user=user,
        password=password,
    )
