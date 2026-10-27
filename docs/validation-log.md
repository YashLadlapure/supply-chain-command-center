# Validation Log: SQL vs DAX

Each KPI is calculated twice: once in SQL against PostgreSQL, and once as a DAX measure in Power BI (see [`powerbi/dax-measures.md`](../powerbi/dax-measures.md)). The two must agree on the overall value and on at least two filtered slices.

**Status:** complete. All 18 slices match. SQL values come from PostgreSQL loaded with the committed seed data. DAX values come from the Power BI model (`powerbi/SupplyChainCommandCenter.pbip`) after a refresh from the same database, evaluated with the same filter applied as a DAX query.

**How to read a row:**
- **Slice** is the filter applied. In Power BI, set the same filter with a slicer or filter pane, and clear every other filter.
- Percentages are shown to 2 decimals. DAX values match when they agree to within 0.01.
- Dates use the order date (`Date` table) unless stated otherwise.

## Data-quality checks

Before any KPI is compared, [`sql/validation/kpi_checks.sql`](../sql/validation/kpi_checks.sql) runs 12 consistency checks, such as "cancelled orders have no shipments" and "shipped quantity equals fulfilled quantity". All 12 return 0 violations on the committed data.

## 1. OTIF %

Measure: `OTIF %`. A delivered order counts when it arrived by the promised date and every line shipped in full.

| Slice | Power BI filter | SQL | DAX | Match |
|---|---|---:|---:|:---:|
| Overall | none | 43.97% | 43.97% | ✅ |
| Region = North | `warehouses[region]` = North | 40.54% | 40.54% | ✅ |
| Order month = Jun 2025 | `Date[Month]` = Jun 2025 | 23.08% | 23.08% | ✅ |

OTIF has no category or supplier slice: an order can contain products from several categories, and customer orders are not linked to suppliers.

```sql
WITH order_lines AS (
    SELECT order_id, SUM(ordered_qty) AS ordered_units, SUM(fulfilled_qty) AS fulfilled_units
    FROM order_items
    GROUP BY order_id
),
order_delivery AS (
    SELECT order_id, MIN(promised_date) AS promised_date, MAX(actual_date) AS delivered_date
    FROM shipments
    WHERE status = 'Delivered'
    GROUP BY order_id
),
base AS (
    SELECT
        w.region,
        DATE_TRUNC('month', o.order_date)::date AS order_month,
        (d.delivered_date <= d.promised_date AND l.fulfilled_units = l.ordered_units)::int AS is_otif
    FROM orders AS o
    JOIN warehouses AS w ON o.warehouse_id = w.warehouse_id
    JOIN order_delivery AS d ON o.order_id = d.order_id
    JOIN order_lines AS l ON o.order_id = l.order_id
)
SELECT 'Overall' AS slice, ROUND(AVG(is_otif) * 100, 2) AS otif_percent FROM base
UNION ALL
SELECT 'Region = North', ROUND(AVG(is_otif) * 100, 2) FROM base WHERE region = 'North'
UNION ALL
SELECT 'Order month = Jun 2025', ROUND(AVG(is_otif) * 100, 2) FROM base WHERE order_month = '2025-06-01';
```

## 2. Fill Rate %

Measure: `Fill Rate %`. Units shipped ÷ units ordered, for shipped orders only.

| Slice | Power BI filter | SQL | DAX | Match |
|---|---|---:|---:|:---:|
| Overall | none | 92.68% | 92.68% | ✅ |
| Region = North | `warehouses[region]` = North | 91.62% | 91.62% | ✅ |
| Category = Electrical | `products[category]` = Electrical | 90.90% | 90.90% | ✅ |

```sql
WITH base AS (
    SELECT oi.ordered_qty, oi.fulfilled_qty, w.region, p.category
    FROM order_items AS oi
    JOIN orders AS o ON oi.order_id = o.order_id
    JOIN warehouses AS w ON o.warehouse_id = w.warehouse_id
    JOIN products AS p ON oi.product_id = p.product_id
    WHERE o.status IN ('Delivered', 'In Transit', 'Delayed')
)
SELECT 'Overall' AS slice, ROUND(SUM(fulfilled_qty)::numeric / SUM(ordered_qty) * 100, 2) AS fill_rate_percent FROM base
UNION ALL
SELECT 'Region = North', ROUND(SUM(fulfilled_qty)::numeric / SUM(ordered_qty) * 100, 2) FROM base WHERE region = 'North'
UNION ALL
SELECT 'Category = Electrical', ROUND(SUM(fulfilled_qty)::numeric / SUM(ordered_qty) * 100, 2) FROM base WHERE category = 'Electrical';
```

## 3. Inventory Value

Measure: `Inventory Value`. Stock on hand × unit price.

| Slice | Power BI filter | SQL | DAX | Match |
|---|---|---:|---:|:---:|
| Overall | none | 62,427,937.91 | 62,427,937.91 | ✅ |
| Region = Central | `warehouses[region]` = Central | 25,477,106.14 | 25,477,106.14 | ✅ |
| Category = Electrical | `products[category]` = Electrical | 14,646,786.16 | 14,646,786.16 | ✅ |

```sql
WITH base AS (
    SELECT i.stock_on_hand * p.unit_price AS stock_value, w.region, p.category
    FROM inventory AS i
    JOIN products AS p ON i.product_id = p.product_id
    JOIN warehouses AS w ON i.warehouse_id = w.warehouse_id
)
SELECT 'Overall' AS slice, ROUND(SUM(stock_value), 2) AS inventory_value FROM base
UNION ALL
SELECT 'Region = Central', ROUND(SUM(stock_value), 2) FROM base WHERE region = 'Central'
UNION ALL
SELECT 'Category = Electrical', ROUND(SUM(stock_value), 2) FROM base WHERE category = 'Electrical';
```

## 4. Average Lead Time

Measures: `Avg Planned Lead Time (days)` (all POs) and `Avg Actual Lead Time (days)` (received POs). Region here is the **supplier's** region.

| Slice | Power BI filter | SQL planned | DAX planned | SQL actual | DAX actual | Match |
|---|---|---:|---:|---:|---:|:---:|
| Overall | none | 15.74 | 15.74 | 15.89 | 15.89 | ✅ |
| Supplier region = West | `suppliers[region]` = West | 15.19 | 15.19 | 15.26 | 15.26 | ✅ |
| Category = Electrical | `products[category]` = Electrical | 15.66 | 15.66 | 15.37 | 15.37 | ✅ |

```sql
WITH base AS (
    SELECT
        po.lead_time_days,
        CASE WHEN po.status = 'Received' THEN po.actual_date - po.order_date END AS actual_lead_time,
        sp.region,
        p.category
    FROM purchase_orders AS po
    JOIN suppliers AS sp ON po.supplier_id = sp.supplier_id
    JOIN products AS p ON po.product_id = p.product_id
)
SELECT 'Overall' AS slice, ROUND(AVG(lead_time_days), 2) AS planned_days, ROUND(AVG(actual_lead_time), 2) AS actual_days FROM base
UNION ALL
SELECT 'Supplier region = West', ROUND(AVG(lead_time_days), 2), ROUND(AVG(actual_lead_time), 2) FROM base WHERE region = 'West'
UNION ALL
SELECT 'Category = Electrical', ROUND(AVG(lead_time_days), 2), ROUND(AVG(actual_lead_time), 2) FROM base WHERE category = 'Electrical';
```

## 5. Forecast Accuracy %

Measure: `Forecast Accuracy %` (1 − MAPE). Month here is the forecast month.

| Slice | Power BI filter | SQL | DAX | Match |
|---|---|---:|---:|:---:|
| Overall | none | 85.07% | 85.07% | ✅ |
| Category = Electrical | `products[category]` = Electrical | 86.05% | 86.05% | ✅ |
| Forecast month = Jun 2025 | `Date[Month]` = Jun 2025 | 82.84% | 82.84% | ✅ |

```sql
WITH base AS (
    SELECT
        ABS(f.actual_qty - f.forecast_qty)::numeric / NULLIF(f.actual_qty, 0) AS abs_pct_error,
        f.forecast_month,
        p.category
    FROM forecasts AS f
    JOIN products AS p ON f.product_id = p.product_id
)
SELECT 'Overall' AS slice, ROUND((1 - AVG(abs_pct_error)) * 100, 2) AS forecast_accuracy_percent FROM base
UNION ALL
SELECT 'Category = Electrical', ROUND((1 - AVG(abs_pct_error)) * 100, 2) FROM base WHERE category = 'Electrical'
UNION ALL
SELECT 'Forecast month = Jun 2025', ROUND((1 - AVG(abs_pct_error)) * 100, 2) FROM base WHERE forecast_month = '2025-06-01';
```

## 6. Supplier Score

Measure: `Supplier Score` (0–100). It only makes sense per supplier, so the three slices are a high, a middle and the lowest-scoring supplier.

| Slice | Power BI filter | SQL | DAX | Match |
|---|---|---:|---:|:---:|
| Carlson Montgomery and Rowe | `suppliers[supplier_name]` | 95.44 | 95.44 | ✅ |
| Johnson-Rosales | `suppliers[supplier_name]` | 82.93 | 82.93 | ✅ |
| Hardy-Bray | `suppliers[supplier_name]` | 42.03 | 42.03 | ✅ |

```sql
WITH supplier_stats AS (
    SELECT
        supplier_id,
        AVG((actual_date <= expected_date)::int) AS on_time_rate,
        AVG(GREATEST(actual_date - expected_date, 0)) AS avg_days_late
    FROM purchase_orders
    WHERE status = 'Received'
    GROUP BY supplier_id
)
SELECT
    sp.supplier_name AS slice,
    ROUND((0.5 * ss.on_time_rate
         + 0.3 * sp.rating / 5.0
         + 0.2 * (1 - LEAST(ss.avg_days_late / 7.0, 1))) * 100, 2) AS supplier_score
FROM supplier_stats AS ss
JOIN suppliers AS sp ON ss.supplier_id = sp.supplier_id
WHERE sp.supplier_name IN ('Carlson Montgomery and Rowe', 'Johnson-Rosales', 'Hardy-Bray')
ORDER BY supplier_score DESC;
```

## Result

| KPI | Slices checked | Result |
|---|---:|---|
| OTIF % | 3 | ✅ All match |
| Fill Rate % | 3 | ✅ All match |
| Inventory Value | 3 | ✅ All match |
| Average Lead Time | 3 | ✅ All match |
| Forecast Accuracy % | 3 | ✅ All match |
| Supplier Score | 3 | ✅ All match |

Besides these 18 slices, all 23 measures that return an overall value were compared with SQL at overall level and matched.
