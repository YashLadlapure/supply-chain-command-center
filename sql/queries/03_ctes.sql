-- CTEs: multi-step KPI logic

-- 1. OTIF (on time, in full) by month for orders delivered so far
--    An order is OTIF when every line shipped in full and it arrived by the promised date
WITH order_lines AS (
    SELECT
        order_id,
        SUM(ordered_qty) AS ordered_units,
        SUM(fulfilled_qty) AS fulfilled_units
    FROM order_items
    GROUP BY order_id
),
order_delivery AS (
    SELECT
        order_id,
        MIN(promised_date) AS promised_date,
        MAX(actual_date) AS delivered_date
    FROM shipments
    WHERE status = 'Delivered'
    GROUP BY order_id
),
order_flags AS (
    SELECT
        o.order_id,
        DATE_TRUNC('month', o.order_date)::date AS order_month,
        d.delivered_date <= d.promised_date AS is_on_time,
        l.fulfilled_units = l.ordered_units AS is_in_full
    FROM orders AS o
    JOIN order_delivery AS d
        ON o.order_id = d.order_id
    JOIN order_lines AS l
        ON o.order_id = l.order_id
)
SELECT
    order_month,
    COUNT(*) AS delivered_orders,
    ROUND(AVG(is_on_time::int) * 100, 2) AS on_time_percent,
    ROUND(AVG(is_in_full::int) * 100, 2) AS in_full_percent,
    ROUND(AVG((is_on_time AND is_in_full)::int) * 100, 2) AS otif_percent
FROM order_flags
GROUP BY order_month
ORDER BY order_month;

-- 2. Supplier scorecard: classify suppliers by on-time rate and average lateness
WITH supplier_stats AS (
    SELECT
        supplier_id,
        COUNT(*) AS received_pos,
        AVG((actual_date <= expected_date)::int) * 100 AS on_time_percent,
        AVG(GREATEST(actual_date - expected_date, 0)) AS avg_days_late
    FROM purchase_orders
    WHERE status = 'Received'
    GROUP BY supplier_id
)
SELECT
    sp.supplier_name,
    sp.rating,
    ss.received_pos,
    ROUND(ss.on_time_percent, 2) AS on_time_percent,
    ROUND(ss.avg_days_late, 2) AS avg_days_late,
    CASE
        WHEN ss.on_time_percent >= 85 THEN 'Preferred'
        WHEN ss.on_time_percent >= 65 THEN 'Watch'
        ELSE 'At Risk'
    END AS supplier_tier
FROM supplier_stats AS ss
JOIN suppliers AS sp
    ON ss.supplier_id = sp.supplier_id
ORDER BY ss.on_time_percent, ss.avg_days_late DESC;

-- 3. Replenishment gap: locations below reorder point and how much open PO supply covers
WITH low_stock AS (
    SELECT
        i.product_id,
        i.warehouse_id,
        i.stock_on_hand - i.reserved_qty AS available_qty,
        p.reorder_point
    FROM inventory AS i
    JOIN products AS p
        ON i.product_id = p.product_id
    WHERE i.stock_on_hand - i.reserved_qty < p.reorder_point
),
open_supply AS (
    SELECT
        product_id,
        warehouse_id,
        SUM(quantity) AS open_po_qty
    FROM purchase_orders
    WHERE status IN ('Pending', 'Released')
    GROUP BY product_id, warehouse_id
)
SELECT
    p.product_name,
    w.warehouse_name,
    ls.available_qty,
    ls.reorder_point,
    COALESCE(os.open_po_qty, 0) AS open_po_qty,
    GREATEST(ls.reorder_point - ls.available_qty - COALESCE(os.open_po_qty, 0), 0) AS uncovered_gap
FROM low_stock AS ls
JOIN products AS p
    ON ls.product_id = p.product_id
JOIN warehouses AS w
    ON ls.warehouse_id = w.warehouse_id
LEFT JOIN open_supply AS os
    ON ls.product_id = os.product_id
    AND ls.warehouse_id = os.warehouse_id
ORDER BY uncovered_gap DESC, p.product_name
LIMIT 20;

-- 4. OTIF by region (region of the shipping warehouse), delivered orders
WITH order_lines AS (
    SELECT
        order_id,
        SUM(ordered_qty) AS ordered_units,
        SUM(fulfilled_qty) AS fulfilled_units
    FROM order_items
    GROUP BY order_id
),
order_delivery AS (
    SELECT
        order_id,
        MIN(promised_date) AS promised_date,
        MAX(actual_date) AS delivered_date
    FROM shipments
    WHERE status = 'Delivered'
    GROUP BY order_id
)
SELECT
    w.region,
    COUNT(*) AS delivered_orders,
    ROUND(AVG((d.delivered_date <= d.promised_date)::int) * 100, 2) AS on_time_percent,
    ROUND(AVG((l.fulfilled_units = l.ordered_units)::int) * 100, 2) AS in_full_percent,
    ROUND(
        AVG((d.delivered_date <= d.promised_date AND l.fulfilled_units = l.ordered_units)::int) * 100,
        2
    ) AS otif_percent
FROM orders AS o
JOIN warehouses AS w
    ON o.warehouse_id = w.warehouse_id
JOIN order_delivery AS d
    ON o.order_id = d.order_id
JOIN order_lines AS l
    ON o.order_id = l.order_id
GROUP BY w.region
ORDER BY otif_percent;

-- 5. Fill rate by product for shipped orders, lowest 10 (products with at least 20 units ordered)
WITH product_fill AS (
    SELECT
        oi.product_id,
        SUM(oi.ordered_qty) AS ordered_units,
        SUM(oi.fulfilled_qty) AS fulfilled_units
    FROM order_items AS oi
    JOIN orders AS o
        ON oi.order_id = o.order_id
    WHERE o.status IN ('Delivered', 'In Transit', 'Delayed')
    GROUP BY oi.product_id
)
SELECT
    p.product_name,
    p.category,
    pf.ordered_units,
    pf.fulfilled_units,
    ROUND(pf.fulfilled_units::numeric / NULLIF(pf.ordered_units, 0) * 100, 2) AS fill_rate_percent
FROM product_fill AS pf
JOIN products AS p
    ON pf.product_id = p.product_id
WHERE pf.ordered_units >= 20
ORDER BY fill_rate_percent, pf.ordered_units DESC
LIMIT 10;

-- 6. Supplier composite score (0-100) on received POs
--    50% on-time rate, 30% supplier rating (quality proxy: the schema has no defect data),
--    20% lateness score (1 = never late, 0 = 7+ days late on average)
WITH supplier_stats AS (
    SELECT
        supplier_id,
        COUNT(*) AS received_pos,
        AVG((actual_date <= expected_date)::int) AS on_time_rate,
        AVG(GREATEST(actual_date - expected_date, 0)) AS avg_days_late
    FROM purchase_orders
    WHERE status = 'Received'
    GROUP BY supplier_id
),
scored AS (
    SELECT
        sp.supplier_name,
        ss.received_pos,
        ss.on_time_rate,
        sp.rating / 5.0 AS quality_score,
        1 - LEAST(ss.avg_days_late / 7.0, 1) AS lateness_score
    FROM supplier_stats AS ss
    JOIN suppliers AS sp
        ON ss.supplier_id = sp.supplier_id
)
SELECT
    supplier_name,
    received_pos,
    ROUND(on_time_rate * 100, 2) AS on_time_percent,
    ROUND(quality_score * 100, 2) AS quality_score,
    ROUND(lateness_score * 100, 2) AS lateness_score,
    ROUND((0.5 * on_time_rate + 0.3 * quality_score + 0.2 * lateness_score) * 100, 2) AS composite_score
FROM scored
ORDER BY composite_score DESC;

-- 7. Stockout risk: locations whose available stock covers less than 7 days of demand
--    Daily demand = average actual monthly demand over the last 3 forecast months / 30,
--    split evenly across the warehouses that stock the product
WITH recent_demand AS (
    SELECT
        product_id,
        AVG(actual_qty) / 30.0 AS daily_demand
    FROM forecasts
    WHERE forecast_month > (SELECT MAX(forecast_month) FROM forecasts) - INTERVAL '3 months'
    GROUP BY product_id
),
location_cover AS (
    SELECT
        i.product_id,
        i.warehouse_id,
        i.stock_on_hand - i.reserved_qty AS available_qty,
        rd.daily_demand / COUNT(*) OVER (PARTITION BY i.product_id) AS location_daily_demand
    FROM inventory AS i
    JOIN recent_demand AS rd
        ON i.product_id = rd.product_id
)
SELECT
    p.product_name,
    w.warehouse_name,
    lc.available_qty,
    ROUND(lc.location_daily_demand, 2) AS daily_demand,
    ROUND(lc.available_qty / NULLIF(lc.location_daily_demand, 0), 1) AS days_of_cover
FROM location_cover AS lc
JOIN products AS p
    ON lc.product_id = p.product_id
JOIN warehouses AS w
    ON lc.warehouse_id = w.warehouse_id
WHERE lc.available_qty / NULLIF(lc.location_daily_demand, 0) < 7
ORDER BY days_of_cover, p.product_name;
