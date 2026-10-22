CREATE OR REPLACE VIEW vw_inventory_health AS
SELECT
    i.inventory_id,
    i.product_id,
    p.product_name,
    p.category,
    i.warehouse_id,
    w.warehouse_name,
    w.city,
    w.region,
    i.stock_on_hand,
    i.reserved_qty,
    i.stock_on_hand - i.reserved_qty AS available_qty,
    p.reorder_point,
    p.unit_price,
    ROUND(
        i.stock_on_hand::numeric * p.unit_price,
        2
    ) AS inventory_value,
    CASE
        WHEN i.stock_on_hand - i.reserved_qty <= 0
            THEN 'Stockout'
        WHEN i.stock_on_hand - i.reserved_qty < p.reorder_point
            THEN 'Low Stock'
        ELSE 'Healthy'
    END AS risk_status,
    i.last_updated
FROM inventory AS i
JOIN products AS p
    ON i.product_id = p.product_id
JOIN warehouses AS w
    ON i.warehouse_id = w.warehouse_id;