-- Joins and aggregates: fulfilment, delivery, supplier and inventory KPIs

-- 1. Shipped value and unit fill rate by product category (cancelled orders excluded)
SELECT
    p.category,
    COUNT(DISTINCT o.order_id) AS orders,
    SUM(oi.ordered_qty) AS ordered_units,
    SUM(oi.fulfilled_qty) AS fulfilled_units,
    ROUND(SUM(oi.fulfilled_qty * p.unit_price), 2) AS shipped_value,
    ROUND(
        SUM(oi.fulfilled_qty)::numeric
        / NULLIF(SUM(oi.ordered_qty), 0) * 100,
        2
    ) AS unit_fill_rate_percent
FROM orders AS o
JOIN order_items AS oi
    ON o.order_id = oi.order_id
JOIN products AS p
    ON oi.product_id = p.product_id
WHERE o.status <> 'Cancelled'
GROUP BY p.category
ORDER BY shipped_value DESC;

-- 2. Fill rate by warehouse for shipped orders (Delivered, In Transit, Delayed)
SELECT
    w.warehouse_name,
    w.region,
    COUNT(DISTINCT o.order_id) AS shipped_orders,
    SUM(oi.ordered_qty) AS ordered_units,
    SUM(oi.fulfilled_qty) AS fulfilled_units,
    ROUND(
        SUM(oi.fulfilled_qty)::numeric
        / NULLIF(SUM(oi.ordered_qty), 0) * 100,
        2
    ) AS unit_fill_rate_percent
FROM orders AS o
JOIN warehouses AS w
    ON o.warehouse_id = w.warehouse_id
JOIN order_items AS oi
    ON o.order_id = oi.order_id
WHERE o.status IN ('Delivered', 'In Transit', 'Delayed')
GROUP BY w.warehouse_name, w.region
ORDER BY unit_fill_rate_percent;

-- 3. On-time delivery rate by warehouse (delivered orders, actual date on or before promised date)
SELECT
    w.warehouse_name,
    COUNT(DISTINCT s.order_id) AS delivered_orders,
    COUNT(DISTINCT s.order_id) FILTER (WHERE s.actual_date <= s.promised_date) AS on_time_orders,
    ROUND(
        COUNT(DISTINCT s.order_id) FILTER (WHERE s.actual_date <= s.promised_date)::numeric
        / NULLIF(COUNT(DISTINCT s.order_id), 0) * 100,
        2
    ) AS on_time_delivery_percent,
    ROUND(AVG(s.delay_days), 2) AS avg_delay_days
FROM shipments AS s
JOIN orders AS o
    ON s.order_id = o.order_id
JOIN warehouses AS w
    ON o.warehouse_id = w.warehouse_id
WHERE s.status = 'Delivered'
GROUP BY w.warehouse_name
ORDER BY on_time_delivery_percent;

-- 4. Supplier delivery performance on received purchase orders
--    LEFT JOIN keeps suppliers that have no received POs yet
SELECT
    sp.supplier_id,
    sp.supplier_name,
    sp.region,
    sp.rating,
    COUNT(po.po_id) AS received_pos,
    ROUND(
        COUNT(po.po_id) FILTER (WHERE po.actual_date <= po.expected_date)::numeric
        / NULLIF(COUNT(po.po_id), 0) * 100,
        2
    ) AS on_time_percent,
    ROUND(AVG(po.actual_date - po.expected_date), 2) AS avg_days_late,
    ROUND(AVG(po.actual_date - po.order_date), 2) AS avg_actual_lead_time_days
FROM suppliers AS sp
LEFT JOIN purchase_orders AS po
    ON sp.supplier_id = po.supplier_id
    AND po.status = 'Received'
GROUP BY sp.supplier_id, sp.supplier_name, sp.region, sp.rating
ORDER BY on_time_percent NULLS LAST, sp.supplier_name;

-- 5. Inventory value and stock risk by warehouse
SELECT
    w.warehouse_name,
    SUM(i.stock_on_hand) AS stock_on_hand,
    SUM(i.stock_on_hand - i.reserved_qty) AS available_qty,
    ROUND(SUM(i.stock_on_hand * p.unit_price), 2) AS inventory_value,
    COUNT(*) FILTER (WHERE i.stock_on_hand - i.reserved_qty <= 0) AS stockout_skus,
    COUNT(*) FILTER (
        WHERE i.stock_on_hand - i.reserved_qty > 0
          AND i.stock_on_hand - i.reserved_qty < p.reorder_point
    ) AS low_stock_skus,
    ROUND(SUM(i.stock_on_hand)::numeric / w.capacity_units * 100, 2) AS capacity_used_percent
FROM inventory AS i
JOIN products AS p
    ON i.product_id = p.product_id
JOIN warehouses AS w
    ON i.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_name, w.capacity_units
ORDER BY inventory_value DESC;

-- 6. Average order value by category (value of units ordered, cancelled orders excluded)
WITH order_category_value AS (
    SELECT
        o.order_id,
        p.category,
        SUM(oi.ordered_qty * p.unit_price) AS order_value
    FROM orders AS o
    JOIN order_items AS oi
        ON o.order_id = oi.order_id
    JOIN products AS p
        ON oi.product_id = p.product_id
    WHERE o.status <> 'Cancelled'
    GROUP BY o.order_id, p.category
)
SELECT
    category,
    COUNT(*) AS orders,
    ROUND(AVG(order_value), 2) AS avg_order_value
FROM order_category_value
GROUP BY category
ORDER BY avg_order_value DESC;

-- 7. Open purchase order value by supplier (Pending and Released POs)
SELECT
    sp.supplier_name,
    COUNT(po.po_id) AS open_pos,
    SUM(po.quantity) AS open_units,
    ROUND(SUM(po.quantity * p.unit_price), 2) AS open_po_value
FROM purchase_orders AS po
JOIN suppliers AS sp
    ON po.supplier_id = sp.supplier_id
JOIN products AS p
    ON po.product_id = p.product_id
WHERE po.status IN ('Pending', 'Released')
GROUP BY sp.supplier_name
ORDER BY open_po_value DESC;

-- 8. Forecast error (MAPE) by product, worst 10
SELECT
    p.product_name,
    p.category,
    SUM(f.forecast_qty) AS forecast_units,
    SUM(f.actual_qty) AS actual_units,
    ROUND(
        AVG(ABS(f.actual_qty - f.forecast_qty)::numeric / NULLIF(f.actual_qty, 0)) * 100,
        2
    ) AS mape_percent
FROM forecasts AS f
JOIN products AS p
    ON f.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY mape_percent DESC
LIMIT 10;
