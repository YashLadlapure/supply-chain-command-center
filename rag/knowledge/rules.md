# Business rules and data limits

## Rule: the data is a snapshot on 31 December 2025
All statuses are as of 2025-12-31. "Today", "now" or "currently" means 2025-12-31.
"Last month" means December 2025. "This year" means 2025.
Orders, purchase orders and forecasts cover 2025 only. There is no data for 2024, 2026 or any other year.
Inventory is a single snapshot with no history, so stock levels cannot be compared over time.

## Rule: questions about data that does not exist
If no table or KPI card covers what a question asks for, the answer is "not available in this data". Do not substitute a different measure, and do not guess.
The same applies to any year other than 2025, to customer regions, and to price changes over time.
The tool also does not predict future values or recommend actions.

## Rule: no defect, return or product quality data
The database records no defects, returns, rejects, scrap, damage or warranty claims.
Questions about defect rate, return rate, failure rate or product quality get the answer "not available in this data".
Do not use suppliers.rating in its place: it is a general rating, not a defect rate.
Also called: defect rate, reject rate, return rate, quality issues, faulty units, PPM.

## Rule: no customer satisfaction data
The database records no customer feedback: no satisfaction scores, surveys, reviews, complaints or NPS.
Questions about how satisfied or happy customers are get the answer "not available in this data".
Do not use OTIF or fill rate in its place: they measure delivery, not what customers think.
Also called: CSAT, NPS, customer feedback, complaints, customer experience.

## Rule: no cost or profit data (delivery, freight, storage, labour)
The database records no costs. There is no delivery cost, freight cost, shipping cost, storage cost, holding cost, labour cost or purchase cost, and no profit or margin.
Questions about what deliveries, shipping or anything else cost, or about profit, margin or savings, get the answer "not available in this data".
The only money column is products.unit_price. The values that can be calculated are quantity × unit_price: inventory value, shipped value, order value and open PO value.
Also called: expenses, freight cost, transport cost, cost per order, margin, profitability.

## Rule: no employee or staffing data
The database records no people: no employees, headcount, shifts, working hours, overtime, absence or productivity.
Questions about staff or labour get the answer "not available in this data".
Also called: workforce, staff, labour hours, overtime hours, manpower, headcount.

## Rule: suppliers and customer orders are not linked
Purchase orders link suppliers to warehouses and products. Customer orders and shipments link to warehouses and products, never to suppliers.
So a late customer delivery cannot be traced to a supplier, and OTIF, fill rate or order counts cannot be filtered by supplier.
Supplier questions are answered from purchase_orders only.

## Rule: which region a question means
There are two region columns with different values.
warehouses.region ('North', 'Central', 'South') is used for customer orders, fill rate, OTIF and inventory.
suppliers.region ('Central', 'East', 'North', 'South', 'West') is used for supplier and purchase order questions.
'East' or 'West' can only be a supplier region. If a question about orders or inventory names East or West, there is no such warehouse region.
Applies whenever a question names North, Central, South, East or West. Also called: area, zone, territory.

## Rule: category does not filter whole orders
A customer order can contain products from several categories, so it has no single category.
Order-level KPIs (OTIF %, On-Time Delivery %, order counts) cannot be filtered by category.
Line-level KPIs (Fill Rate %, units, shipped value) can: join order_items to products and filter products.category.

## Rule: the supplier rating stands in for quality
suppliers.rating (1 to 5) is the only quality measure. The Supplier Composite Score uses rating ÷ 5 as its quality part.
If a user asks for supplier quality or rating, use this column and say that it is a rating, not a defect rate.

## Rule: how to show numbers
Show percentages from 0 to 100, rounded to 2 decimals, for example ROUND(x * 100, 2).
Round money and averages to 2 decimals. Show counts as whole numbers.
Values have no currency symbol, because the data does not record a currency.
For "top" or "bottom" lists, return the names with their values, ordered, and use LIMIT for the number asked (5 if no number is given).

## Rule: months and dates
Applies whenever a question names a month or period: January to December, 'Jun 2025', a quarter such as Q2, 'monthly', 'by month' or 'last month'.
Order month comes from orders.order_date. PO month comes from purchase_orders.order_date. Forecast month is forecasts.forecast_month.
Filter a month with a date range, for example order_date >= '2025-06-01' AND order_date < '2025-07-01', or with DATE_TRUNC('month', order_date) = '2025-06-01'.
Group by month with DATE_TRUNC('month', date_column)::date.
