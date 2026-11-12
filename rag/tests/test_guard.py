"""Tests for the SQL guard.

The guard must let through exactly one read-only SELECT on known tables, and
reject everything else. These tests check both sides, including writes hidden
inside a WITH block, where a plain text search for "DELETE" would be fooled.

    python -m pytest
"""

import pytest

from guard import MAX_ROWS, UnsafeQuery, check

SAFE = [
    "SELECT * FROM orders",
    "SELECT o.order_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id",
    "SELECT category, COUNT(*) FROM products GROUP BY category",
    "SELECT * FROM vw_order_performance WHERE region = 'North'",
    "WITH recent AS (SELECT * FROM orders) SELECT COUNT(*) FROM recent",
    "SELECT * FROM public.inventory",
    "SELECT supplier_name FROM suppliers UNION SELECT supplier_name FROM suppliers",
]

UNSAFE = [
    "DELETE FROM orders",
    "UPDATE orders SET status = 'x'",
    "INSERT INTO orders (order_id) VALUES (1)",
    "DROP TABLE orders",
    "TRUNCATE orders",
    "SELECT * FROM users",                                 # unknown table
    "SELECT * FROM pg_catalog.pg_tables",                  # unknown schema
    "SELECT * FROM orders; SELECT * FROM products",        # two statements
    "SELECT * FROM orders FOR UPDATE",                     # locks rows
    "SELECT * INTO backup FROM orders",                    # writes a new table
    "WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x",  # write hidden in a CTE
    "UPDATE orders SET status = (SELECT status FROM orders LIMIT 1)",
    "not sql at all",
]


@pytest.mark.parametrize("sql", SAFE)
def test_safe_queries_pass(sql):
    assert isinstance(check(sql), str)


@pytest.mark.parametrize("sql", UNSAFE)
def test_unsafe_queries_rejected(sql):
    with pytest.raises(UnsafeQuery):
        check(sql)


def test_checked_sql_is_still_a_select():
    """The guard returns the query rebuilt from the parsed tree, so what runs
    is what was checked. That rebuilt query must still read as a SELECT."""
    out = check("SELECT COUNT(*) FROM orders WHERE status = 'Open'")
    assert out.lower().startswith("select")
    assert check(out)  # passing it back through the guard is still safe


def test_row_cap_is_set():
    assert MAX_ROWS == 200
