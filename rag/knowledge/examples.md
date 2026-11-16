# Example questions

Each card pairs a question with SQL that answers it. The SQL is based on `sql/queries/01–04`. Where a query there differs from a KPI definition in `kpis.md`, the version here follows the KPI definition.

## Example: orders by status
Question: How many orders are in each status?
```sql
SELECT status, COUNT(*) AS order_count
FROM orders
GROUP BY status
ORDER BY order_count DESC;
```

## Example: total orders
Question: How many customer orders did we receive in 2025?
```sql
SELECT COUNT(*) AS total_orders
FROM orders;
```

## Example: fill rate and shipped value by category
Question: What is the unit fill rate and shipped value for each product category?
```sql
SELECT p.category,
       SUM(oi.ordered_qty) AS ordered_units,
       SUM(oi.fulfilled_qty) AS fulfilled_units,
       ROUND(SUM(oi.fulfilled_qty * p.unit_price), 2) AS shipped_value,
       ROUND(SUM(oi.fulfilled_qty)::numeric / NULLIF(SUM(oi.ordered_qty), 0) * 100, 2) AS fill_rate_percent
FROM orders AS o
JOIN order_items AS oi ON o.order_id = oi.order_id
JOIN products AS p ON oi.product_id = p.product_id
WHERE o.status IN ('Delivered', 'In Transit', 'Delayed')
GROUP BY p.category
ORDER BY shipped_value DESC;
```

## Example: fill rate by warehouse
Question: Which warehouse has the lowest fill rate?
```sql
SELECT w.warehouse_name, w.region,
       ROUND(SUM(oi.fulfilled_qty)::numeric / NULLIF(SUM(oi.ordered_qty), 0) * 100, 2) AS fill_rate_percent
FROM orders AS o
JOIN warehouses AS w ON o.warehouse_id = w.warehouse_id
JOIN order_items AS oi ON o.order_id = oi.order_id
WHERE o.status IN ('Delivered', 'In Transit', 'Delayed')
GROUP BY w.warehouse_name, w.region
ORDER BY fill_rate_percent;
```

## Example: on-time delivery by warehouse
Question: How often does each warehouse deliver customer orders on time?
```sql
WITH order_delivery AS (
    SELECT order_id, MIN(promised_date) AS promised_date, MAX(actual_date) AS delivered_date
    FROM shipments
    WHERE status = 'Delivered'
    GROUP BY order_id
)
SELECT w.warehouse_name,
       COUNT(*) AS delivered_orders,
       ROUND(AVG((d.delivered_date <= d.promised_date)::int) * 100, 2) AS on_time_percent
FROM order_delivery AS d
JOIN orders AS o ON d.order_id = o.order_id
JOIN warehouses AS w ON o.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_name
ORDER BY on_time_percent;
```

## Example: supplier delivery performance
Question: How does each supplier perform on received purchase orders?
```sql
SELECT sp.supplier_name, sp.region, sp.rating,
       COUNT(po.po_id) AS received_pos,
       ROUND(AVG((po.actual_date <= po.expected_date)::int) * 100, 2) AS on_time_percent,
       ROUND(AVG(GREATEST(po.actual_date - po.expected_date, 0)), 2) AS avg_days_late,
       ROUND(AVG(po.actual_date - po.order_date), 2) AS avg_actual_lead_time_days
FROM suppliers AS sp
JOIN purchase_orders AS po ON sp.supplier_id = po.supplier_id
WHERE po.status = 'Received'
GROUP BY sp.supplier_name, sp.region, sp.rating
ORDER BY on_time_percent;
```

## Example: inventory value by warehouse
Question: Which warehouse holds the most inventory value?
```sql
SELECT w.warehouse_name,
       SUM(i.stock_on_hand) AS stock_on_hand,
       ROUND(SUM(i.stock_on_hand * p.unit_price), 2) AS inventory_value,
       ROUND(SUM(i.stock_on_hand)::numeric / w.capacity_units * 100, 2) AS capacity_used_percent
FROM inventory AS i
JOIN products AS p ON i.product_id = p.product_id
JOIN warehouses AS w ON i.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_name, w.capacity_units
ORDER BY inventory_value DESC;
```

## Example: average order value by category
Question: What is the average order value for each category?
```sql
WITH order_category_value AS (
    SELECT o.order_id, p.category, SUM(oi.ordered_qty * p.unit_price) AS order_value
    FROM orders AS o
    JOIN order_items AS oi ON o.order_id = oi.order_id
    JOIN products AS p ON oi.product_id = p.product_id
    WHERE o.status <> 'Cancelled'
    GROUP BY o.order_id, p.category
)
SELECT category, COUNT(*) AS orders, ROUND(AVG(order_value), 2) AS avg_order_value
FROM order_category_value
GROUP BY category
ORDER BY avg_order_value DESC;
```

## Example: open purchase order value by supplier
Question: Which suppliers have the most open purchase order value?
```sql
SELECT sp.supplier_name,
       COUNT(po.po_id) AS open_pos,
       ROUND(SUM(po.quantity * p.unit_price), 2) AS open_po_value
FROM purchase_orders AS po
JOIN suppliers AS sp ON po.supplier_id = sp.supplier_id
JOIN products AS p ON po.product_id = p.product_id
WHERE po.status IN ('Pending', 'Released')
GROUP BY sp.supplier_name
ORDER BY open_po_value DESC;
```

## Example: products with the worst forecast error
Question: Which 10 products have the highest forecast error (MAPE)?
```sql
SELECT p.product_name, p.category,
       ROUND(AVG(ABS(f.actual_qty - f.forecast_qty)::numeric / NULLIF(f.actual_qty, 0)) * 100, 2) AS mape_percent
FROM forecasts AS f
JOIN products AS p ON f.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY mape_percent DESC
LIMIT 10;
```

## Example: OTIF by month
Question: How did OTIF change month by month?
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
)
SELECT DATE_TRUNC('month', o.order_date)::date AS order_month,
       COUNT(*) AS delivered_orders,
       ROUND(AVG((d.delivered_date <= d.promised_date AND l.fulfilled_units = l.ordered_units)::int) * 100, 2) AS otif_percent
FROM orders AS o
JOIN order_delivery AS d ON o.order_id = d.order_id
JOIN order_lines AS l ON o.order_id = l.order_id
GROUP BY order_month
ORDER BY order_month;
```

## Example: OTIF by region
Question: Which warehouse region has the best OTIF?
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
)
SELECT w.region,
       COUNT(*) AS delivered_orders,
       ROUND(AVG((d.delivered_date <= d.promised_date AND l.fulfilled_units = l.ordered_units)::int) * 100, 2) AS otif_percent
FROM orders AS o
JOIN warehouses AS w ON o.warehouse_id = w.warehouse_id
JOIN order_delivery AS d ON o.order_id = d.order_id
JOIN order_lines AS l ON o.order_id = l.order_id
GROUP BY w.region
ORDER BY otif_percent DESC;
```

## Example: supplier tiers
Question: Which suppliers are preferred, on watch or at risk?
```sql
WITH supplier_stats AS (
    SELECT supplier_id,
           AVG((actual_date <= expected_date)::int) * 100 AS on_time_percent,
           AVG(GREATEST(actual_date - expected_date, 0)) AS avg_days_late
    FROM purchase_orders
    WHERE status = 'Received'
    GROUP BY supplier_id
)
SELECT sp.supplier_name,
       ROUND(ss.on_time_percent, 2) AS on_time_percent,
       ROUND(ss.avg_days_late, 2) AS avg_days_late,
       CASE WHEN ss.on_time_percent >= 85 THEN 'Preferred'
            WHEN ss.on_time_percent >= 65 THEN 'Watch'
            ELSE 'At Risk' END AS supplier_tier
FROM supplier_stats AS ss
JOIN suppliers AS sp ON ss.supplier_id = sp.supplier_id
ORDER BY ss.on_time_percent;
```

## Example: supplier composite score
Question: What is the supplier score for each supplier?
```sql
WITH supplier_stats AS (
    SELECT supplier_id,
           AVG((actual_date <= expected_date)::int) AS on_time_rate,
           AVG(GREATEST(actual_date - expected_date, 0)) AS avg_days_late
    FROM purchase_orders
    WHERE status = 'Received'
    GROUP BY supplier_id
)
SELECT sp.supplier_name,
       ROUND((0.5 * ss.on_time_rate
            + 0.3 * sp.rating / 5.0
            + 0.2 * (1 - LEAST(ss.avg_days_late / 7.0, 1))) * 100, 2) AS supplier_score
FROM supplier_stats AS ss
JOIN suppliers AS sp ON ss.supplier_id = sp.supplier_id
ORDER BY supplier_score DESC;
```

## Example: replenishment gap
Question: Which low-stock locations are not covered by open purchase orders?
```sql
WITH low_stock AS (
    SELECT i.product_id, i.warehouse_id, i.stock_on_hand - i.reserved_qty AS available_qty, p.reorder_point
    FROM inventory AS i
    JOIN products AS p ON i.product_id = p.product_id
    WHERE i.stock_on_hand - i.reserved_qty < p.reorder_point
),
open_supply AS (
    SELECT product_id, warehouse_id, SUM(quantity) AS open_po_qty
    FROM purchase_orders
    WHERE status IN ('Pending', 'Released')
    GROUP BY product_id, warehouse_id
)
SELECT p.product_name, w.warehouse_name, ls.available_qty, ls.reorder_point,
       COALESCE(os.open_po_qty, 0) AS open_po_qty,
       GREATEST(ls.reorder_point - ls.available_qty - COALESCE(os.open_po_qty, 0), 0) AS uncovered_gap
FROM low_stock AS ls
JOIN products AS p ON ls.product_id = p.product_id
JOIN warehouses AS w ON ls.warehouse_id = w.warehouse_id
LEFT JOIN open_supply AS os ON ls.product_id = os.product_id AND ls.warehouse_id = os.warehouse_id
ORDER BY uncovered_gap DESC, p.product_name
LIMIT 20;
```

## Example: products with the lowest fill rate
Question: Which products have the lowest fill rate?
```sql
WITH product_fill AS (
    SELECT oi.product_id, SUM(oi.ordered_qty) AS ordered_units, SUM(oi.fulfilled_qty) AS fulfilled_units
    FROM order_items AS oi
    JOIN orders AS o ON oi.order_id = o.order_id
    WHERE o.status IN ('Delivered', 'In Transit', 'Delayed')
    GROUP BY oi.product_id
)
SELECT p.product_name, p.category, pf.ordered_units,
       ROUND(pf.fulfilled_units::numeric / NULLIF(pf.ordered_units, 0) * 100, 2) AS fill_rate_percent
FROM product_fill AS pf
JOIN products AS p ON pf.product_id = p.product_id
WHERE pf.ordered_units >= 20
ORDER BY fill_rate_percent, pf.ordered_units DESC
LIMIT 10;
```

## Example: stockout risk locations
Question: Where will we run out of stock within a week?
```sql
WITH recent_demand AS (
    SELECT product_id, AVG(actual_qty) / 30.0 AS daily_demand
    FROM forecasts
    WHERE forecast_month > (SELECT MAX(forecast_month) FROM forecasts) - INTERVAL '3 months'
    GROUP BY product_id
),
location_cover AS (
    SELECT i.product_id, i.warehouse_id,
           i.stock_on_hand - i.reserved_qty AS available_qty,
           rd.daily_demand / COUNT(*) OVER (PARTITION BY i.product_id) AS location_daily_demand
    FROM inventory AS i
    JOIN recent_demand AS rd ON i.product_id = rd.product_id
)
SELECT p.product_name, w.warehouse_name, lc.available_qty,
       ROUND(lc.available_qty / NULLIF(lc.location_daily_demand, 0), 1) AS days_of_cover
FROM location_cover AS lc
JOIN products AS p ON lc.product_id = p.product_id
JOIN warehouses AS w ON lc.warehouse_id = w.warehouse_id
WHERE lc.available_qty / NULLIF(lc.location_daily_demand, 0) < 7
ORDER BY days_of_cover, p.product_name;
```

## Example: monthly order trend
Question: How many orders did we get each month, and how did that change from the month before?
```sql
WITH monthly AS (
    SELECT DATE_TRUNC('month', order_date)::date AS order_month, COUNT(*) AS orders
    FROM orders
    WHERE status <> 'Cancelled'
    GROUP BY DATE_TRUNC('month', order_date)
)
SELECT order_month, orders,
       orders - LAG(orders) OVER (ORDER BY order_month) AS change_vs_prior_month,
       SUM(orders) OVER (ORDER BY order_month) AS running_total_orders
FROM monthly
ORDER BY order_month;
```

## Example: top products in each category
Question: What are the top 3 products by shipped value in each category?
```sql
WITH product_value AS (
    SELECT p.category, p.product_name, SUM(oi.fulfilled_qty * p.unit_price) AS shipped_value
    FROM order_items AS oi
    JOIN products AS p ON oi.product_id = p.product_id
    GROUP BY p.category, p.product_name
),
ranked AS (
    SELECT category, product_name, shipped_value,
           RANK() OVER (PARTITION BY category ORDER BY shipped_value DESC) AS value_rank
    FROM product_value
)
SELECT category, value_rank, product_name, ROUND(shipped_value, 2) AS shipped_value
FROM ranked
WHERE value_rank <= 3
ORDER BY category, value_rank;
```

## Example: forecast error trend by category
Question: How has weighted forecast error (WAPE) moved over the year for each category?
```sql
WITH monthly_error AS (
    SELECT p.category, f.forecast_month,
           SUM(ABS(f.actual_qty - f.forecast_qty))::numeric / NULLIF(SUM(f.actual_qty), 0) * 100 AS wape_percent
    FROM forecasts AS f
    JOIN products AS p ON f.product_id = p.product_id
    GROUP BY p.category, f.forecast_month
)
SELECT category, forecast_month,
       ROUND(wape_percent, 2) AS wape_percent,
       ROUND(AVG(wape_percent) OVER (PARTITION BY category ORDER BY forecast_month
                                     ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS wape_3m_rolling_percent
FROM monthly_error
ORDER BY category, forecast_month;
```

## Example: supplier on-time ranking
Question: Rank suppliers by on-time delivery and split them into quartiles.
```sql
WITH supplier_on_time AS (
    SELECT sp.supplier_name, COUNT(*) AS received_pos,
           AVG((po.actual_date <= po.expected_date)::int) * 100 AS on_time_percent
    FROM purchase_orders AS po
    JOIN suppliers AS sp ON po.supplier_id = sp.supplier_id
    WHERE po.status = 'Received'
    GROUP BY sp.supplier_name
)
SELECT supplier_name, received_pos,
       ROUND(on_time_percent, 2) AS on_time_percent,
       DENSE_RANK() OVER (ORDER BY on_time_percent DESC) AS on_time_rank,
       NTILE(4) OVER (ORDER BY on_time_percent DESC) AS performance_quartile
FROM supplier_on_time
ORDER BY on_time_rank, supplier_name;
```

## Example: category share of inventory value
Question: What share of each warehouse's inventory value does each category make up?
```sql
WITH category_value AS (
    SELECT w.warehouse_name, p.category, SUM(i.stock_on_hand * p.unit_price) AS inventory_value
    FROM inventory AS i
    JOIN products AS p ON i.product_id = p.product_id
    JOIN warehouses AS w ON i.warehouse_id = w.warehouse_id
    GROUP BY w.warehouse_name, p.category
)
SELECT warehouse_name, category,
       ROUND(inventory_value, 2) AS inventory_value,
       ROUND(inventory_value / SUM(inventory_value) OVER (PARTITION BY warehouse_name) * 100, 2) AS share_of_warehouse_percent
FROM category_value
ORDER BY warehouse_name, inventory_value DESC;
```

## Example: OTIF overall
Question: What is our OTIF?
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
)
SELECT ROUND(AVG((d.delivered_date <= d.promised_date
                  AND l.fulfilled_units = l.ordered_units)::int) * 100, 2) AS otif_percent
FROM order_delivery AS d
JOIN order_lines AS l ON d.order_id = l.order_id;
```

## Example: OTIF for one region or one month
Question: What was OTIF for North region warehouses, or for orders placed in June 2025?
```sql
-- Build the two CTEs first, then filter. One SELECT only; never nest one aggregate inside another.
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
)
SELECT ROUND(AVG((d.delivered_date <= d.promised_date
                  AND l.fulfilled_units = l.ordered_units)::int) * 100, 2) AS otif_percent
FROM orders AS o
JOIN warehouses AS w ON o.warehouse_id = w.warehouse_id
JOIN order_delivery AS d ON o.order_id = d.order_id
JOIN order_lines AS l ON o.order_id = l.order_id
WHERE w.region = 'North';
-- For a month instead, drop the warehouse join and filter the order month:
--   WHERE DATE_TRUNC('month', o.order_date) = DATE '2025-06-01'
```

## Example: forecast accuracy overall
Question: How accurate is our demand forecast?
```sql
-- Multiply by 100.0 (a decimal) so this is not integer division, which would make the result wrong.
SELECT ROUND(AVG(100 - ABS(f.actual_qty - f.forecast_qty) * 100.0 / NULLIF(f.actual_qty, 0)), 2)
       AS forecast_accuracy_percent
FROM forecasts AS f;
-- For one month, add:   WHERE DATE_TRUNC('month', f.forecast_month) = DATE '2025-06-01'
-- For one category, join products and filter on p.category.
```

## Example: supplier score for one supplier
Question: What is the supplier score for a named supplier?
```sql
WITH supplier_stats AS (
    SELECT supplier_id,
           AVG((actual_date <= expected_date)::int) AS on_time_rate,
           AVG(GREATEST(actual_date - expected_date, 0)) AS avg_days_late
    FROM purchase_orders
    WHERE status = 'Received'
    GROUP BY supplier_id
)
SELECT sp.supplier_name,
       ROUND((0.5 * ss.on_time_rate
            + 0.3 * sp.rating / 5.0
            + 0.2 * (1 - LEAST(ss.avg_days_late / 7.0, 1))) * 100, 2) AS supplier_score
FROM supplier_stats AS ss
JOIN suppliers AS sp ON ss.supplier_id = sp.supplier_id
WHERE sp.supplier_name = 'Carlson Montgomery and Rowe';
```

## Example: low-stock count
Question: How many product-warehouse locations are below their reorder point?
```sql
SELECT COUNT(*) AS low_stock_locations
FROM inventory AS i
JOIN products AS p ON i.product_id = p.product_id
WHERE i.stock_on_hand - i.reserved_qty < p.reorder_point;
```

## Example: stockout risk count
Question: How many locations will run out of stock within a week?
```sql
-- Count the locations with less than 7 days of cover. This is the "days of cover < 7" query,
-- wrapped in a COUNT; do not mix it with the reorder-point (low-stock) query.
WITH recent_demand AS (
    SELECT product_id, AVG(actual_qty) / 30.0 AS daily_demand
    FROM forecasts
    WHERE forecast_month > (SELECT MAX(forecast_month) FROM forecasts) - INTERVAL '3 months'
    GROUP BY product_id
),
location_cover AS (
    SELECT i.stock_on_hand - i.reserved_qty AS available_qty,
           rd.daily_demand / COUNT(*) OVER (PARTITION BY i.product_id) AS location_daily_demand
    FROM inventory AS i
    JOIN recent_demand AS rd ON i.product_id = rd.product_id
)
SELECT COUNT(*) AS stockout_risk_locations
FROM location_cover
WHERE available_qty / NULLIF(location_daily_demand, 0) < 7;
```

## Example: planned lead time overall
Question: What is the average planned supplier lead time in days?
```sql
-- Planned lead time is stored on every purchase order. Do not filter by status.
SELECT ROUND(AVG(lead_time_days), 2) AS avg_planned_lead_time_days
FROM purchase_orders;
```

## Example: actual lead time for a region
Question: How long do suppliers in the West region actually take to deliver, on average?
```sql
-- Actual lead time = days from order to receipt, for received POs only.
SELECT ROUND(AVG(po.actual_date - po.order_date), 2) AS avg_actual_lead_time_days
FROM purchase_orders AS po
JOIN suppliers AS sp ON po.supplier_id = sp.supplier_id
WHERE sp.region = 'West' AND po.status = 'Received';
```
