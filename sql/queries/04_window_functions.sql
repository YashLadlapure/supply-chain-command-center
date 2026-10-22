-- Window functions: trends, rankings and shares

-- 1. Monthly order volume with month-over-month change and running total (cancelled excluded)
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', order_date)::date AS order_month,
        COUNT(*) AS orders
    FROM orders
    WHERE status <> 'Cancelled'
    GROUP BY DATE_TRUNC('month', order_date)
)
SELECT
    order_month,
    orders,
    orders - LAG(orders) OVER (ORDER BY order_month) AS change_vs_prior_month,
    SUM(orders) OVER (ORDER BY order_month) AS running_total_orders
FROM monthly
ORDER BY order_month;

-- 2. Top 3 products by shipped value within each category
WITH product_value AS (
    SELECT
        p.category,
        p.product_name,
        SUM(oi.fulfilled_qty * p.unit_price) AS shipped_value
    FROM order_items AS oi
    JOIN products AS p
        ON oi.product_id = p.product_id
    GROUP BY p.category, p.product_name
),
ranked AS (
    SELECT
        category,
        product_name,
        shipped_value,
        RANK() OVER (PARTITION BY category ORDER BY shipped_value DESC) AS value_rank
    FROM product_value
)
SELECT
    category,
    value_rank,
    product_name,
    ROUND(shipped_value, 2) AS shipped_value
FROM ranked
WHERE value_rank <= 3
ORDER BY category, value_rank;

-- 3. Forecast error (WAPE) by category with a 3-month rolling average
--    WAPE = SUM(|actual - forecast|) / SUM(actual)
WITH monthly_error AS (
    SELECT
        p.category,
        f.forecast_month,
        SUM(ABS(f.actual_qty - f.forecast_qty))::numeric
            / NULLIF(SUM(f.actual_qty), 0) * 100 AS wape_percent
    FROM forecasts AS f
    JOIN products AS p
        ON f.product_id = p.product_id
    GROUP BY p.category, f.forecast_month
)
SELECT
    category,
    forecast_month,
    ROUND(wape_percent, 2) AS wape_percent,
    ROUND(
        AVG(wape_percent) OVER (
            PARTITION BY category
            ORDER BY forecast_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS wape_3m_rolling_percent
FROM monthly_error
ORDER BY category, forecast_month;

-- 4. Supplier on-time ranking split into quartiles (1 = best)
WITH supplier_on_time AS (
    SELECT
        sp.supplier_name,
        COUNT(*) AS received_pos,
        AVG((po.actual_date <= po.expected_date)::int) * 100 AS on_time_percent
    FROM purchase_orders AS po
    JOIN suppliers AS sp
        ON po.supplier_id = sp.supplier_id
    WHERE po.status = 'Received'
    GROUP BY sp.supplier_name
)
SELECT
    supplier_name,
    received_pos,
    ROUND(on_time_percent, 2) AS on_time_percent,
    DENSE_RANK() OVER (ORDER BY on_time_percent DESC) AS on_time_rank,
    NTILE(4) OVER (ORDER BY on_time_percent DESC) AS performance_quartile
FROM supplier_on_time
ORDER BY on_time_rank, supplier_name;

-- 5. Each category's share of inventory value within its warehouse
WITH category_value AS (
    SELECT
        w.warehouse_name,
        p.category,
        SUM(i.stock_on_hand * p.unit_price) AS inventory_value
    FROM inventory AS i
    JOIN products AS p
        ON i.product_id = p.product_id
    JOIN warehouses AS w
        ON i.warehouse_id = w.warehouse_id
    GROUP BY w.warehouse_name, p.category
)
SELECT
    warehouse_name,
    category,
    ROUND(inventory_value, 2) AS inventory_value,
    ROUND(
        inventory_value / SUM(inventory_value) OVER (PARTITION BY warehouse_name) * 100,
        2
    ) AS share_of_warehouse_percent
FROM category_value
ORDER BY warehouse_name, inventory_value DESC;
