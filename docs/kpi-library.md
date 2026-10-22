# KPI Library

Every KPI used in this project: what it means, how it is calculated, the level it is calculated at (grain), who would own it, and where the SQL lives.

**Reference values** are calculated in SQL on the committed seed data (seed 42, snapshot date 31 Dec 2025, no filters). They are the numbers the Power BI measures must match.

## Delivery and fulfilment

### OTIF % (On Time In Full)
- **Business question:** What share of customer orders arrived on time and complete?
- **Formula:** delivered orders where the delivery date ≤ the promised date **and** every line shipped in full ÷ delivered orders
- **Grain:** order
- **Owner:** Logistics / Customer Service Manager
- **SQL:** `sql/queries/03_ctes.sql` (OTIF by month, OTIF by region)
- **Reference value:** 43.97% (on time 67.67%, in full 65.09%, 464 delivered orders)
- **Note:** OTIF is lower than either part because the late orders and the short-shipped orders are mostly different orders.

### Fill Rate (unit)
- **Business question:** Of the units customers ordered, how many did we ship?
- **Formula:** Σ fulfilled_qty ÷ Σ ordered_qty, for shipped orders (Delivered, In Transit, Delayed)
- **Grain:** order line
- **Owner:** Fulfilment / Warehouse Manager
- **SQL:** `sql/queries/02_joins_and_aggregates.sql` (by category, by warehouse), `03_ctes.sql` (by product), `sql/views/01_order_performance.sql` (per order)
- **Reference value:** 92.68%

### On-Time Delivery %
- **Business question:** How often do shipments arrive by the promised date?
- **Formula:** delivered orders with actual_date ≤ promised_date ÷ delivered orders
- **Grain:** order
- **Owner:** Logistics Manager
- **SQL:** `sql/queries/02_joins_and_aggregates.sql` (by warehouse)
- **Reference value:** 67.67%

## Inventory

### Inventory Value
- **Business question:** How much money is tied up in stock?
- **Formula:** Σ (stock_on_hand × unit_price)
- **Grain:** product × warehouse
- **Owner:** Inventory Manager / Finance
- **SQL:** `sql/queries/02_joins_and_aggregates.sql` (by warehouse), `04_window_functions.sql` (category share), `sql/views/02_inventory_health.sql`
- **Reference value:** 62,427,937.91

### Available Stock
- **Formula:** Σ (stock_on_hand − reserved_qty)
- **Grain:** product × warehouse
- **Owner:** Inventory Manager
- **SQL:** `sql/validation/kpi_checks.sql`, `sql/views/02_inventory_health.sql`
- **Reference value:** 228,248 units

### Low-Stock Locations
- **Business question:** Which product–warehouse locations need replenishing?
- **Formula:** count of locations where available stock < reorder_point (this includes locations with zero stock)
- **Grain:** product × warehouse
- **Owner:** Inventory Planner
- **SQL:** `sql/validation/kpi_checks.sql`, `sql/queries/03_ctes.sql` (replenishment gap)
- **Reference value:** 135 locations

### Stockout Risk
- **Business question:** Where will we run out within a week?
- **Formula:** days of cover = available stock ÷ daily demand. A location is flagged when days of cover < 7.
- **Daily demand assumption:** average actual monthly demand over the last 3 forecast months ÷ 30, split evenly across the warehouses that stock the product
- **Grain:** product × warehouse
- **Owner:** Inventory Planner
- **SQL:** `sql/queries/03_ctes.sql`
- **Reference value:** 54 locations at risk

## Suppliers and purchasing

### Average Lead Time
- **Business question:** How long do suppliers take to deliver?
- **Formula:** planned = average of purchase_orders.lead_time_days. Actual = average of (actual_date − order_date) for received POs.
- **Grain:** purchase order
- **Owner:** Procurement Manager
- **SQL:** `sql/queries/02_joins_and_aggregates.sql` (supplier performance)
- **Reference value:** planned 15.74 days, actual 15.89 days

### Supplier On-Time %
- **Formula:** received POs with actual_date ≤ expected_date ÷ received POs
- **Grain:** purchase order
- **Owner:** Procurement Manager
- **SQL:** `sql/queries/02_joins_and_aggregates.sql`, `03_ctes.sql`, `04_window_functions.sql`
- **Reference value:** 71.84% (277 received POs)

### Supplier Composite Score
- **Business question:** Which suppliers are the most reliable overall?
- **Formula (0–100):** 50% on-time rate + 30% quality score + 20% lateness score
  - The quality score is rating ÷ 5. The schema has no defect data, so the supplier rating stands in for quality.
  - The lateness score is 1 − min(average days late ÷ 7, 1).
- **Grain:** supplier
- **Owner:** Procurement Manager
- **SQL:** `sql/queries/03_ctes.sql`

### Open PO Value
- **Formula:** Σ (quantity × unit_price) for Pending and Released POs
- **Grain:** purchase order
- **Owner:** Procurement / Finance
- **SQL:** `sql/queries/02_joins_and_aggregates.sql` (by supplier)
- **Reference value:** 635,713.15 (13 open POs)

## Forecasting

### Forecast Accuracy (MAPE-based)
- **Business question:** How close was the demand forecast to actual demand?
- **Formula:** 1 − MAPE, where MAPE = average of |actual − forecast| ÷ actual across product-months
- **Grain:** product × month
- **Owner:** Demand Planner
- **SQL:** `sql/queries/02_joins_and_aggregates.sql` (MAPE by product), `sql/validation/kpi_checks.sql`
- **Reference value:** 85.07% (MAPE 14.93%)

### WAPE (Weighted Absolute Percentage Error)
- **Formula:** Σ |actual − forecast| ÷ Σ actual
- **Why both:** MAPE gives every product-month equal weight, so a few low-volume rows can inflate it. WAPE weights errors by volume.
- **Grain:** product × month
- **Owner:** Demand Planner
- **SQL:** `sql/queries/04_window_functions.sql` (by category, with a 3-month rolling average)
- **Reference value:** 9.16%
