# KPIs

One card per KPI. The definitions match `docs/kpi-library.md` and the Power BI measures in `powerbi/dax-measures.md`.

## OTIF %
Meaning: share of delivered customer orders that arrived on time AND complete.
Formula: per order, on time = MAX(shipments.actual_date) <= MIN(shipments.promised_date), using shipments with status = 'Delivered'. In full = SUM(order_items.fulfilled_qty) = SUM(order_items.ordered_qty).
OTIF % = orders that are both ÷ delivered orders × 100.
Grain: one row per order. Never average shipments or order lines directly.
Tables: orders, shipments, order_items.
Filters that work: region and warehouse (orders.warehouse_id → warehouses), order month (orders.order_date).
Filters that do not work: product category, supplier (an order mixes categories and has no supplier).
Also called: on time in full, OTIF rate, perfect order rate.

## Fill Rate %
Meaning: of the units customers ordered, the share that was shipped.
Formula: SUM(order_items.fulfilled_qty) ÷ SUM(order_items.ordered_qty) × 100, for orders with status IN ('Delivered', 'In Transit', 'Delayed').
Grain: order line. Sum the quantities first, then divide. Never average per-line or per-order rates.
Tables: order_items, orders, plus products for category and warehouses for region.
Filters that work: region, warehouse, order month, category, product.
Also called: unit fill rate, fulfilment rate, service level.

## On-Time Delivery %
Meaning: share of delivered orders that arrived by the promised date, regardless of quantity.
Formula: per order, MAX(actual_date) <= MIN(promised_date) over shipments with status = 'Delivered'. On-Time Delivery % = on-time orders ÷ delivered orders × 100.
Grain: order.
Tables: shipments, orders, warehouses.
Filters that work: region, warehouse, order month.
Watch out: this is the "on time" half of OTIF. OTIF % is always lower or equal.
Also called: OTD, on-time rate for customer deliveries.

## Inventory Value
Meaning: money tied up in stock.
Formula: SUM(inventory.stock_on_hand × products.unit_price).
Grain: product × warehouse.
Tables: inventory, products, warehouses (or the view vw_inventory_health, column inventory_value).
Filters that work: region, warehouse, category, product.
Watch out: it uses stock_on_hand, not available stock. There is one snapshot, so no value by month.
Also called: stock value, inventory on hand value.

## Available Stock
Meaning: units that can still be promised to customers.
Formula: SUM(inventory.stock_on_hand − inventory.reserved_qty).
Grain: product × warehouse.
Tables: inventory (or vw_inventory_health, column available_qty).
Filters that work: region, warehouse, category, product.
Also called: free stock, unreserved stock, available to promise.

## Low-Stock Locations
Meaning: product–warehouse locations that need replenishing.
Formula: COUNT of inventory rows where stock_on_hand − reserved_qty < products.reorder_point. This includes locations with zero or negative available stock.
Grain: product × warehouse.
Tables: inventory, products (or vw_inventory_health WHERE risk_status IN ('Stockout', 'Low Stock')).
Filters that work: region, warehouse, category.
Related: shortfall = reorder_point − available stock, for low-stock locations only.
Also called: below reorder point, items to reorder, replenishment list.

## Stockout Risk Locations
Meaning: locations that will run out within a week.
Formula: daily demand = AVG(forecasts.actual_qty) over the last 3 forecast months (October to December 2025) ÷ 30, then divided evenly by the number of warehouses that stock the product. Days of cover = available stock ÷ that daily demand. A location is at risk when days of cover < 7.
Grain: product × warehouse.
Tables: inventory, forecasts, products, warehouses.
See the example "Stockout risk locations" for the full SQL.
Also called: days of cover, days of supply, running out, stockout risk.

## Average Lead Time
Meaning: how long suppliers take to deliver a purchase order.
Formula: planned = AVG(purchase_orders.lead_time_days) over all purchase orders. Actual = AVG(actual_date − order_date) over purchase orders with status = 'Received'.
Grain: purchase order.
Tables: purchase_orders, suppliers, products.
Filters that work: supplier, supplier region (suppliers.region), category, warehouse, PO month (purchase_orders.order_date).
Watch out: report planned and actual separately. "Region" here means the supplier's region.
Also called: supplier lead time, PO cycle time, days to receive.

## Supplier On-Time %
Meaning: share of received purchase orders that arrived on or before the expected date.
Formula: AVG((actual_date <= expected_date)::int) × 100 over purchase_orders with status = 'Received'.
Grain: purchase order.
Tables: purchase_orders, suppliers.
Filters that work: supplier, supplier region, category, PO month.
Also called: supplier OTD, vendor on-time rate, supplier reliability.

## Supplier Avg Days Late
Meaning: average number of days a received purchase order arrived after the expected date. Early or on-time arrivals count as 0.
Formula: AVG(GREATEST(actual_date − expected_date, 0)) over purchase_orders with status = 'Received'.
Grain: purchase order.
Tables: purchase_orders, suppliers.
Filters that work: supplier, supplier region, category, PO month.
Also called: average lateness, days late.

## Supplier Composite Score
Meaning: one 0–100 score for how reliable a supplier is.
Formula: 100 × (0.5 × on-time rate + 0.3 × quality + 0.2 × lateness score), using received purchase orders only.
On-time rate = AVG((actual_date <= expected_date)::int). Quality = suppliers.rating ÷ 5.0. Lateness score = 1 − LEAST(average days late ÷ 7.0, 1), where days late = GREATEST(actual_date − expected_date, 0).
Grain: supplier. Calculate it per supplier; there is no meaningful overall score.
Tables: purchase_orders, suppliers.
Watch out: suppliers with no received purchase orders have no score.
Also called: supplier score, vendor scorecard, supplier rating score.

## Open PO Value
Meaning: value of purchase orders that have been raised but not received.
Formula: SUM(purchase_orders.quantity × products.unit_price) for status IN ('Pending', 'Released').
Grain: purchase order.
Tables: purchase_orders, products, suppliers.
Filters that work: supplier, warehouse, category.
Also called: open purchase orders, on-order value, incoming supply value.

## Forecast Accuracy %
Meaning: how close the demand forecast was to actual demand.
Formula: MAPE = AVG(ABS(actual_qty − forecast_qty) ÷ actual_qty) over product-months. Forecast Accuracy % = (1 − MAPE) × 100.
Grain: product × month. Calculate the error per row first, then average.
Tables: forecasts, products (or vw_forecast_details).
Filters that work: category, product, forecast month (forecasts.forecast_month).
Filters that do not work: region, warehouse, supplier (forecasts are per product only).
Also called: forecast accuracy, 1 − MAPE. MAPE % on its own is also called forecast error.

## WAPE %
Meaning: forecast error weighted by volume, so small products don't dominate.
Formula: SUM(ABS(actual_qty − forecast_qty)) ÷ SUM(actual_qty) × 100.
Grain: product × month, summed before dividing.
Tables: forecasts, products.
Filters that work: category, product, forecast month.
Watch out: WAPE and MAPE give different numbers. Use WAPE only when the question asks for it or for weighted error.
Also called: weighted absolute percentage error, weighted forecast error.
