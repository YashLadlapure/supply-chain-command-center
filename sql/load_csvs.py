import os
import pandas as pd
from sqlalchemy import create_engine

# ---------- Configuration ----------
CSV_DIR = os.path.join("data", "seed")
DB_USER = "postgres"
DB_PASSWORD = "Y%40sh1234"  # URL-encoded: Y@sh1234 -> Y%40sh1234
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "supply_chain"

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
for table in TABLES:
    csv_path = os.path.join(CSV_DIR, f"{table}.csv")
    print(f"Loading {table} from {csv_path}...")

    df = pd.read_csv(csv_path)

    df.to_sql(
        table,
        con=engine,
        schema="public",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    print(f"  -> {len(df)} rows inserted into {table}.")

print("All tables loaded.")