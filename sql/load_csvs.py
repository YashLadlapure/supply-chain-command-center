import os
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ---------- Configuration ----------
# Read DB settings from the .env file (never committed; see .env.example)
load_dotenv()

# Resolve the seed folder from this script's location so it runs from any directory
CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "seed")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "supply_chain")

if not DB_PASSWORD:
    raise SystemExit("DB_PASSWORD is not set. Copy .env.example to .env and fill it in.")

# URL-encode the password so special characters like @ don't break the URL
DB_PASSWORD = quote_plus(DB_PASSWORD)

# SQLAlchemy connection URL
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Table order (parent → child)
TABLES = [
    "products",
    "suppliers",
    "warehouses",
    "orders",
    "order_items",
    "inventory",
    "purchase_orders",
    "shipments",
    "forecasts",
]

# ---------- Load each CSV ----------
# One transaction: empty the tables first so the script can be re-run,
# and roll everything back if any table fails to load
with engine.begin() as conn:
    conn.execute(text(f"TRUNCATE TABLE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))

    for table in TABLES:
        csv_path = os.path.join(CSV_DIR, f"{table}.csv")
        print(f"Loading {table} from {csv_path}...")

        df = pd.read_csv(csv_path)

        df.to_sql(
            table,
            con=conn,
            schema="public",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        print(f"  -> {len(df)} rows inserted into {table}.")

print("All tables loaded.")