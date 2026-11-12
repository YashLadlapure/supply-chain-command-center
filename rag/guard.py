"""Reject any SQL that is not a single read-only query on known tables.

The SQL is parsed with sqlglot, the way a database would read it, instead of
searching the text for words like "DELETE". The query that runs is the one
rebuilt from the parsed tree, so what was checked is what is executed.
"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.scope import traverse_scope

ALLOWED_TABLES = {
    "products", "suppliers", "warehouses", "orders", "order_items", "inventory",
    "purchase_orders", "shipments", "forecasts",
    "vw_order_performance", "vw_inventory_health", "vw_forecast_details",
}

# Statements that change or lock data can hide inside a SELECT (for example in a WITH block)
BLOCKED = (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Into, exp.Lock)

MAX_ROWS = 200


class UnsafeQuery(ValueError):
    """The SQL was rejected before it reached the database."""


def check(sql):
    """Return the cleaned SQL if it is safe to run, otherwise raise UnsafeQuery."""
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
        if len(statements) != 1:
            raise UnsafeQuery("Exactly one statement is allowed.")
        tree = statements[0]
        if not isinstance(tree, (exp.Select, exp.SetOperation)):
            raise UnsafeQuery("Only SELECT queries are allowed.")
        if tree.find(*BLOCKED):
            raise UnsafeQuery("The query tries to change data.")

        # A name defined in a WITH block is not a real table, but only where that block is visible
        with_names = {
            id(table)
            for scope in traverse_scope(tree)
            for table in scope.tables
            if not table.db and table.name in scope.cte_sources
        }
    except SqlglotError as error:
        raise UnsafeQuery(f"Could not read the SQL: {error}") from error

    unknown = set()
    for table in tree.find_all(exp.Table):
        if id(table) in with_names:
            continue
        in_public_schema = table.db in ("", "public") and not table.catalog
        if not (in_public_schema and table.name in ALLOWED_TABLES):
            parts = (table.catalog, table.db, table.name)
            unknown.add(".".join(part for part in parts if part) or table.sql(dialect="postgres"))
    if unknown:
        raise UnsafeQuery(f"Unknown tables: {', '.join(sorted(unknown))}")

    return tree.sql(dialect="postgres")
