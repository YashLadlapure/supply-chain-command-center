# Power BI Model and DAX Measures

The Power BI report is stored as a Power BI Project in this folder, so the whole model can be read as text:

- `SupplyChainCommandCenter.SemanticModel/definition/` holds the model in TMDL: tables, relationships and measures
- `SupplyChainCommandCenter.Report/definition/` holds the three report pages and their visuals

This page summarises the model. KPI definitions are in [`docs/kpi-library.md`](../docs/kpi-library.md), and the SQL vs DAX checks are in [`docs/validation-log.md`](../docs/validation-log.md).

## Data source

Every table imports from PostgreSQL through two parameters, `Server` (default `localhost`) and `Database` (default `supply_chain`). To change them, use **Transform data → Edit parameters**.

## Date table

`Date` is a calculated table, marked as the model's date table. `Month` sorts by `Month Start`.

```dax
Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2025, 1, 1 ), DATE ( 2026, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM yyyy" ),
    "Month Start", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 )
)
```

## Relationships

All relationships are many-to-one with single-direction filtering, from the dimension to the fact table.

| Many side | One side |
|---|---|
| `orders[order_date]` | `Date[Date]` |
| `purchase_orders[order_date]` | `Date[Date]` |
| `forecasts[forecast_month]` | `Date[Date]` |
| `order_items[product_id]` | `products[product_id]` |
| `shipments[product_id]` | `products[product_id]` |
| `inventory[product_id]` | `products[product_id]` |
| `purchase_orders[product_id]` | `products[product_id]` |
| `forecasts[product_id]` | `products[product_id]` |
| `orders[warehouse_id]` | `warehouses[warehouse_id]` |
| `inventory[warehouse_id]` | `warehouses[warehouse_id]` |
| `purchase_orders[warehouse_id]` | `warehouses[warehouse_id]` |
| `purchase_orders[supplier_id]` | `suppliers[supplier_id]` |
| `order_items[order_id]` | `orders[order_id]` |
| `shipments[order_id]` | `orders[order_id]` |

- **Fact tables:** `order_items`, `shipments`, `inventory`, `purchase_orders`, `forecasts`.
- **Dimensions:** `Date`, `products`, `suppliers`, `warehouses`.
- `orders` sits between the two groups. It filters its order lines and shipments, so order-level measures such as OTIF iterate over `orders`.

A product category filter reaches order lines but not whole orders. OTIF and order counts therefore respond to region, warehouse and date filters, but not to category.

## Measures

All measures live in the `_Measures` table, grouped into display folders.

### Delivery

**Total Orders** (format `#,0`): Number of customer orders.

```dax
Total Orders =
COUNTROWS ( orders )
```

**Open Orders** (format `#,0`): Orders not yet delivered or cancelled: Processing, In Transit or Delayed.

```dax
Open Orders =
CALCULATE ( COUNTROWS ( orders ), orders[status] IN { "Processing", "In Transit", "Delayed" } )
```

**OTIF %** (format `0.00%`): Delivered orders that arrived by the promised date and shipped every line in full, divided by delivered orders.

```dax
OTIF % =
VAR DeliveredOrders =
    ADDCOLUMNS (
        CALCULATETABLE ( VALUES ( orders[order_id] ), orders[status] = "Delivered" ),
        "@OnTime",
            CALCULATE ( MAX ( shipments[actual_date] ) )
                <= CALCULATE ( MIN ( shipments[promised_date] ) ),
        "@InFull",
            CALCULATE ( SUM ( order_items[fulfilled_qty] ) )
                = CALCULATE ( SUM ( order_items[ordered_qty] ) )
    )
RETURN
    DIVIDE (
        COUNTROWS ( FILTER ( DeliveredOrders, [@OnTime] && [@InFull] ) ),
        COUNTROWS ( DeliveredOrders )
    )
```

**Fill Rate %** (format `0.00%`): Units shipped divided by units ordered, for shipped orders only.

```dax
Fill Rate % =
CALCULATE (
    DIVIDE ( SUM ( order_items[fulfilled_qty] ), SUM ( order_items[ordered_qty] ) ),
    orders[status] IN { "Delivered", "In Transit", "Delayed" }
)
```

### Inventory

**Inventory Value** (format `#,0`): Stock on hand multiplied by unit price.

```dax
Inventory Value =
SUMX ( inventory, inventory[stock_on_hand] * RELATED ( products[unit_price] ) )
```

**Available Stock** (format `#,0`): Stock on hand minus reserved quantity.

```dax
Available Stock =
SUM ( inventory[stock_on_hand] ) - SUM ( inventory[reserved_qty] )
```

**Locations Tracked** (format `#,0`): Product and warehouse combinations with an inventory record.

```dax
Locations Tracked =
COUNTROWS ( inventory )
```

**Low-Stock Locations** (format `#,0`): Locations where available stock is below the reorder point.

```dax
Low-Stock Locations =
COUNTROWS (
    FILTER (
        inventory,
        inventory[stock_on_hand] - inventory[reserved_qty] < RELATED ( products[reorder_point] )
    )
)
```

**Shortfall vs Reorder Point** (format `#,0`): Units needed to bring low-stock locations back up to their reorder point. Blank when no location is low.

```dax
Shortfall vs Reorder Point =
SUMX (
    inventory,
    VAR Available = inventory[stock_on_hand] - inventory[reserved_qty]
    VAR ReorderPoint = RELATED ( products[reorder_point] )
    RETURN IF ( Available < ReorderPoint, ReorderPoint - Available )
)
```

**Days of Cover (At Risk)** (format `0.0`): Days of stock left at one location, shown only when below 7. Daily demand is the average actual demand of the last 3 forecast months divided by 30, split evenly across the warehouses that stock the product.

```dax
Days of Cover (At Risk) =
VAR Product = SELECTEDVALUE ( inventory[product_id] )
VAR LastMonth = CALCULATE ( MAX ( forecasts[forecast_month] ), REMOVEFILTERS () )
VAR DailyDemand =
    CALCULATE (
        AVERAGE ( forecasts[actual_qty] ),
        REMOVEFILTERS (),
        forecasts[product_id] = Product,
        forecasts[forecast_month] >= EDATE ( LastMonth, -2 )
    ) / 30
VAR Locations =
    CALCULATE ( COUNTROWS ( inventory ), REMOVEFILTERS (), inventory[product_id] = Product )
VAR Cover = DIVIDE ( [Available Stock], DIVIDE ( DailyDemand, Locations ) )
RETURN
    IF ( HASONEVALUE ( inventory[inventory_id] ) && DailyDemand > 0 && Cover < 7, Cover )
```

**Stockout Risk Locations** (format `#,0`): Locations with less than 7 days of stock cover.

```dax
Stockout Risk Locations =
COUNTROWS ( FILTER ( inventory, NOT ISBLANK ( [Days of Cover (At Risk)] ) ) )
```

**At-Risk Available Stock** (format `#,0`): Available stock, shown only for locations at stockout risk.

```dax
At-Risk Available Stock =
IF ( NOT ISBLANK ( [Days of Cover (At Risk)] ), [Available Stock] )
```

### Suppliers

**Active Suppliers** (format `#,0`): Suppliers with at least one purchase order.

```dax
Active Suppliers =
DISTINCTCOUNT ( purchase_orders[supplier_id] )
```

**Received POs** (format `#,0`): Purchase orders that have been received.

```dax
Received POs =
CALCULATE ( COUNTROWS ( purchase_orders ), purchase_orders[status] = "Received" )
```

**Late POs** (format `#,0`): Received purchase orders that arrived after the expected date.

```dax
Late POs =
CALCULATE (
    COUNTROWS ( FILTER ( purchase_orders, purchase_orders[actual_date] > purchase_orders[expected_date] ) ),
    purchase_orders[status] = "Received"
)
```

**Avg Planned Lead Time (days)** (format `0.00`): Average planned lead time across all purchase orders.

```dax
Avg Planned Lead Time (days) =
AVERAGE ( purchase_orders[lead_time_days] )
```

**Avg Actual Lead Time (days)** (format `0.00`): Average days from order to receipt, for received purchase orders.

```dax
Avg Actual Lead Time (days) =
CALCULATE (
    AVERAGEX (
        purchase_orders,
        INT ( purchase_orders[actual_date] - purchase_orders[order_date] )
    ),
    purchase_orders[status] = "Received",
    NOT ISBLANK ( purchase_orders[actual_date] )
)
```

**Supplier On-Time %** (format `0.00%`): Received purchase orders that arrived on or before the expected date.

```dax
Supplier On-Time % =
CALCULATE (
    DIVIDE (
        COUNTROWS (
            FILTER ( purchase_orders, purchase_orders[actual_date] <= purchase_orders[expected_date] )
        ),
        COUNTROWS ( purchase_orders )
    ),
    purchase_orders[status] = "Received",
    NOT ISBLANK ( purchase_orders[actual_date] )
)
```

**Supplier Avg Days Late** (format `0.00`): Average days late on received purchase orders, counting early arrivals as 0.

```dax
Supplier Avg Days Late =
CALCULATE (
    AVERAGEX (
        purchase_orders,
        MAX ( 0, INT ( purchase_orders[actual_date] - purchase_orders[expected_date] ) )
    ),
    purchase_orders[status] = "Received",
    NOT ISBLANK ( purchase_orders[actual_date] )
)
```

**Supplier Score** (format `0.00`): 0-100 score: 50% on-time rate, 30% rating (used as the quality measure), 20% lateness. Use per supplier.

```dax
Supplier Score =
VAR OnTime = [Supplier On-Time %]
VAR Quality = AVERAGE ( suppliers[rating] ) / 5
VAR Lateness = 1 - MIN ( [Supplier Avg Days Late] / 7, 1 )
RETURN
    IF ( NOT ISBLANK ( OnTime ), 100 * ( 0.5 * OnTime + 0.3 * Quality + 0.2 * Lateness ) )
```

### Forecasting

**Total Forecast Quantity** (format `#,0`): Sum of forecast demand.

```dax
Total Forecast Quantity =
SUM ( forecasts[forecast_qty] )
```

**Total Actual Quantity** (format `#,0`): Sum of actual demand.

```dax
Total Actual Quantity =
SUM ( forecasts[actual_qty] )
```

**MAPE %** (format `0.00%`): Average absolute percentage error across product-months.

```dax
MAPE % =
AVERAGEX (
    forecasts,
    DIVIDE ( ABS ( forecasts[actual_qty] - forecasts[forecast_qty] ), forecasts[actual_qty] )
)
```

**Forecast Accuracy %** (format `0.00%`): 1 minus MAPE.

```dax
Forecast Accuracy % =
1 - [MAPE %]
```

**WAPE %** (format `0.00%`): Total absolute error divided by total actual demand.

```dax
WAPE % =
DIVIDE (
    SUMX ( forecasts, ABS ( forecasts[actual_qty] - forecasts[forecast_qty] ) ),
    SUM ( forecasts[actual_qty] )
)
```
