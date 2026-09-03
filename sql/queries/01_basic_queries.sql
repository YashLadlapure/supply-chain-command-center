-- Basic counts and sanity checks

-- 1. Total number of orders
SELECT COUNT(*) AS total_orders
FROM orders;

-- 2. Orders by status
SELECT status, COUNT(*) AS order_count
FROM orders
GROUP BY status
ORDER BY order_count DESC;

-- 3. Total order lines (order_items)
SELECT COUNT(*) AS total_order_lines
FROM order_items;

-- 4. Average quantity per order line
SELECT AVG(ordered_qty) AS avg_ordered_qty
FROM order_items;