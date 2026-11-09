# Tables and views

One card per table or view in the `supply_chain` database.

## Table: products
One row per product.
Columns: product_id (key), product_name, category, unit_price, lead_time_days (planned supplier lead time), reorder_point (units).
Category values: 'Electrical', 'Finished Goods', 'Mechanical', 'Packaging', 'Raw Material'.
Used for: unit price in every value calculation, and the category filter on order lines, inventory, purchase orders and forecasts.
Also called: item, SKU, part, material.

## Table: suppliers
One row per supplier.
Columns: supplier_id (key), supplier_name, region, category_specialization, rating (1 to 5).
Region values: 'Central', 'East', 'North', 'South', 'West'. This is the supplier's own region, not a warehouse region.
Watch out: rating is a score from 1 to 5. It is the only quality measure; there is no defect data.
Also called: vendor.

## Table: warehouses
One row per warehouse. There are 5.
Columns: warehouse_id (key), warehouse_name, city, region, capacity_units.
Region values: 'North', 'Central', 'South'. "Region" on orders and inventory questions means this column.
Watch out: warehouse names start with the word "Warehouse", for example 'Warehouse Carterbury'. Match names with ILIKE '%carterbury%' when the user types a short name.
Also called: site, DC, distribution centre, location.

## Table: orders
One row per customer order.
Columns: order_id (key), order_date, warehouse_id → warehouses, customer_name, status.
Status values: 'Delivered', 'In Transit', 'Delayed' (promised date passed, not delivered), 'Processing' (not shipped yet), 'Cancelled'.
Shipped orders are 'Delivered', 'In Transit' and 'Delayed'. Open orders are 'Processing', 'In Transit' and 'Delayed'.
Watch out: an order has no product or supplier column. Category comes from order_items → products.
Also called: sales order, customer order.

## Table: order_items
One row per order line: one product on one order.
Columns: order_item_id (key), order_id → orders, product_id → products, ordered_qty, fulfilled_qty.
fulfilled_qty is the number of units shipped for the line. It can be 0, and it is never more than ordered_qty.
Watch out: lines of cancelled orders still exist. Filter on orders.status when you need shipped orders only.
Also called: order lines, line items.

## Table: shipments
One row per shipped order line. Lines with fulfilled_qty = 0 have no shipment.
Columns: shipment_id (key), order_id → orders, product_id → products, promised_date, actual_date, status, delay_days, shipped_qty.
Status values: 'Delivered', 'In Transit'.
delay_days = days delivered after the promised date, 0 if on time or early.
Watch out: actual_date and delay_days are empty for 'In Transit'. Shipments link to customer orders, never to suppliers.
Also called: deliveries, outbound shipments.

## Table: inventory
One row per product and warehouse (a "location"). Every product is stocked in at least one warehouse.
Columns: inventory_id (key), product_id → products, warehouse_id → warehouses, stock_on_hand, reserved_qty, last_updated.
Available stock = stock_on_hand − reserved_qty.
Watch out: this is a single snapshot, not a history. There is no stock level by month.
Also called: stock, stock levels, on hand.

## Table: purchase_orders
One row per purchase order sent to a supplier.
Columns: po_id (key), supplier_id → suppliers, warehouse_id → warehouses, product_id → products, order_date, expected_date, actual_date, quantity, status, lead_time_days (planned lead time).
Status values: 'Received', 'Released' (sent, not arrived yet), 'Pending' (raised in the last 3 days), 'Cancelled'.
Watch out: actual_date is empty unless status = 'Received'. Late means actual_date > expected_date. There is no price column; value = quantity × products.unit_price.
Also called: POs, replenishment orders, inbound orders.

## Table: forecasts
One row per product per month, January to December 2025.
Columns: forecast_id (key), product_id → products, forecast_month (first day of the month), forecast_qty, actual_qty.
actual_qty is the real demand for that month. "Demand" questions use this column.
Watch out: forecast_month is a date such as '2025-06-01'. Filter a month with forecast_month = '2025-06-01'.
Also called: demand plan, demand forecast.

## View: vw_order_performance
One row per order, with its lines added up.
Columns: order_id, order_date, warehouse_id, customer_name, status, ordered_quantity, fulfilled_quantity, unfulfilled_quantity, fill_rate_percent (0–100).
Use it for per-order fill rate and for finding short-shipped orders.
Watch out: it includes every status. For the Fill Rate KPI, keep only status IN ('Delivered', 'In Transit', 'Delayed') and divide the summed quantities. Never average fill_rate_percent.

## View: vw_inventory_health
One row per inventory location, with product and warehouse details joined in.
Columns: inventory_id, product_id, product_name, category, warehouse_id, warehouse_name, city, region, stock_on_hand, reserved_qty, available_qty, reorder_point, unit_price, inventory_value, risk_status, last_updated.
risk_status values: 'Stockout' (available ≤ 0), 'Low Stock' (above 0 but below the reorder point), 'Healthy'.
Watch out: the Low-Stock Locations KPI counts both 'Stockout' and 'Low Stock'.

## View: vw_forecast_details
One row per product per month, with product details joined in.
Columns: forecast_id, product_id, product_name, category, forecast_month, forecast_qty, actual_qty, variance_qty (actual − forecast), absolute_variance_qty, absolute_percentage_error (0–100).
Use it for forecast error questions by product, category or month.
Watch out: absolute_percentage_error is already × 100. Forecast Accuracy = 100 − AVG(absolute_percentage_error).
