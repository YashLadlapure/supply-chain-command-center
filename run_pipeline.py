"""Rebuild the supply_chain database in one command.

Steps: create the tables, load the CSVs, create the reporting views,
then run the 12 data-quality checks. Pass --regenerate to rebuild the
CSVs with data/generate_data.py first.

Usage:
    python run_pipeline.py
    python run_pipeline.py --regenerate

The database itself must already exist (CREATE DATABASE supply_chain;).
Connection settings come from .env, the same as sql/load_csvs.py.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent
SQL_DIR = ROOT / "sql"


def get_engine():
    load_dotenv(ROOT / ".env")
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise SystemExit("DB_PASSWORD is not set. Copy .env.example to .env and fill it in.")
    user = os.getenv("DB_USER", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "supply_chain")
    return create_engine(
        f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{name}"
    )


def run_script(path):
    print(f"\n== Running {path.relative_to(ROOT)}", flush=True)
    subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)


def run_sql_file(engine, path):
    print(f"\n== Running {path.relative_to(ROOT)}", flush=True)
    with engine.begin() as conn:
        conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def run_quality_checks(engine):
    # Part 1 of kpi_checks.sql is a single query: one row per check, 0 = pass
    checks_sql = (SQL_DIR / "validation" / "kpi_checks.sql").read_text(encoding="utf-8")
    checks_sql = checks_sql.split(";")[0]
    with engine.connect() as conn:
        results = conn.exec_driver_sql(checks_sql).all()

    print("\n== Data-quality checks")
    for check_name, violations in results:
        status = "ok" if violations == 0 else f"{violations} violations"
        print(f"  {check_name}: {status}")
    return sum(violations for _, violations in results)


def main():
    parser = argparse.ArgumentParser(description="Rebuild the supply_chain database.")
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="rebuild the CSVs with data/generate_data.py before loading",
    )
    args = parser.parse_args()

    engine = get_engine()

    if args.regenerate:
        run_script(ROOT / "data" / "generate_data.py")

    # schema.sql drops the tables with CASCADE, which also drops the views,
    # so the views are created again after the data is loaded
    run_sql_file(engine, SQL_DIR / "schema.sql")
    run_script(SQL_DIR / "load_csvs.py")
    for view in sorted((SQL_DIR / "views").glob("*.sql")):
        run_sql_file(engine, view)

    failed = run_quality_checks(engine)
    if failed:
        raise SystemExit(f"\nPipeline finished, but {failed} data-quality violations were found.")
    print("\nPipeline finished: tables, data and views are ready, and all checks passed.")


if __name__ == "__main__":
    main()
