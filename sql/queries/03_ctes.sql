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
