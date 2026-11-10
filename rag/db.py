"""Database connection built from the settings in .env."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def connect():
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise SystemExit("DB_PASSWORD is not set. Copy .env.example to .env and fill it in.")
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "supply_chain"),
        user=os.getenv("DB_USER", "postgres"),
        password=password,
    )
