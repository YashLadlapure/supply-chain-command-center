CREATE OR REPLACE VIEW vw_order_performance AS
SELECT
    o.order_id,
    o.order_date,
    o.warehouse_id,
    o.customer_name,
    o.status,
    SUM(oi.ordered_qty) AS ordered_quantity,
    SUM(oi.fulfilled_qty) AS fulfilled_quantity,
    SUM(oi.ordered_qty - oi.fulfilled_qty) AS unfulfilled_quantity,
    ROUND(
        SUM(oi.fulfilled_qty)::numeric
        / NULLIF(SUM(oi.ordered_qty), 0) * 100,
        2
    ) AS fill_rate_percent
FROM orders AS o
JOIN order_items AS oi
    ON o.order_id = oi.order_id
GROUP BY
    o.order_id,
    o.order_date,
    o.warehouse_id,
    o.customer_name,
    o.status;