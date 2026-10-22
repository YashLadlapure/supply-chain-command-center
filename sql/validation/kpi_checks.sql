-- Data-quality checks and reference KPI values
-- Part 1: every check should return violations = 0
-- Part 2: headline KPI values to compare against the Power BI cards (no filters applied)

-- ---------- Part 1: data-quality checks ----------
SELECT 'Orders without order lines' AS check_name, COUNT(*) AS violations
FROM orders AS o
WHERE NOT EXISTS (SELECT 1 FROM order_items AS oi WHERE oi.order_id = o.order_id)

UNION ALL
SELECT 'Fulfilled quantity outside 0..ordered', COUNT(*)
FROM order_items
WHERE fulfilled_qty < 0 OR fulfilled_qty > ordered_qty

UNION ALL
SELECT 'Cancelled or Processing orders with shipments', COUNT(DISTINCT s.order_id)
FROM shipments AS s
JOIN orders AS o ON s.order_id = o.order_id
WHERE o.status IN ('Cancelled', 'Processing')

UNION ALL
SELECT 'Shipment status differs from order status', COUNT(*)
FROM shipments AS s
JOIN orders AS o ON s.order_id = o.order_id
WHERE s.status <> o.status

UNION ALL
SELECT 'Shipped orders without shipments', COUNT(*)
FROM orders AS o
WHERE o.status IN ('Delivered', 'In Transit', 'Delayed')
  AND NOT EXISTS (SELECT 1 FROM shipments AS s WHERE s.order_id = o.order_id)

UNION ALL
SELECT 'Shipment product not on the order', COUNT(*)
FROM shipments AS s
WHERE NOT EXISTS (
    SELECT 1 FROM order_items AS oi
    WHERE oi.order_id = s.order_id AND oi.product_id = s.product_id
)

UNION ALL
SELECT 'Shipped qty differs from fulfilled qty', COUNT(*)
FROM shipments AS s
JOIN order_items AS oi
    ON s.order_id = oi.order_id AND s.product_id = oi.product_id
WHERE s.shipped_qty <> oi.fulfilled_qty

UNION ALL
SELECT 'Promised date before order date', COUNT(*)
FROM shipments AS s
JOIN orders AS o ON s.order_id = o.order_id
WHERE s.promised_date < o.order_date

UNION ALL
SELECT 'Delivered shipments missing actual date (or others having one)', COUNT(*)
FROM shipments
WHERE (status = 'Delivered') <> (actual_date IS NOT NULL)

UNION ALL
SELECT 'Received POs missing actual date (or others having one)', COUNT(*)
FROM purchase_orders
WHERE (status = 'Received') <> (actual_date IS NOT NULL)

UNION ALL
SELECT 'Reserved qty above stock on hand', COUNT(*)
FROM inventory
WHERE reserved_qty > stock_on_hand

UNION ALL
SELECT 'Forecast month not first of month', COUNT(*)
FROM forecasts
WHERE EXTRACT(DAY FROM forecast_month) <> 1;

-- ---------- Part 2: reference KPI values ----------
SELECT 'Total Orders' AS kpi, COUNT(*)::numeric AS sql_value
FROM orders

UNION ALL
SELECT 'Total Stock on Hand', SUM(stock_on_hand)
FROM inventory

UNION ALL
SELECT 'Total Reserved Quantity', SUM(reserved_qty)
FROM inventory

UNION ALL
SELECT 'Available Stock', SUM(stock_on_hand - reserved_qty)
FROM inventory

UNION ALL
SELECT 'Low-Stock Records (available < reorder point)', COUNT(*)
FROM inventory AS i
JOIN products AS p ON i.product_id = p.product_id
WHERE i.stock_on_hand - i.reserved_qty < p.reorder_point

UNION ALL
SELECT 'Completed Shipments (Delivered lines)', COUNT(*)
FROM shipments
WHERE status = 'Delivered'

UNION ALL
SELECT 'Total Forecast Quantity', SUM(forecast_qty)
FROM forecasts

UNION ALL
SELECT 'Total Actual Quantity', SUM(actual_qty)
FROM forecasts

UNION ALL
SELECT 'Forecast Error (actual - forecast)', SUM(actual_qty - forecast_qty)
FROM forecasts

UNION ALL
SELECT 'Absolute Forecast Error', SUM(ABS(actual_qty - forecast_qty))
FROM forecasts

UNION ALL
SELECT 'MAPE % (row average)', ROUND(AVG(ABS(actual_qty - forecast_qty)::numeric / NULLIF(actual_qty, 0)) * 100, 2)
FROM forecasts

UNION ALL
SELECT 'Unit Fill Rate % (shipped orders)',
    ROUND(SUM(oi.fulfilled_qty)::numeric / NULLIF(SUM(oi.ordered_qty), 0) * 100, 2)
FROM order_items AS oi
JOIN orders AS o ON oi.order_id = o.order_id
WHERE o.status IN ('Delivered', 'In Transit', 'Delayed');
