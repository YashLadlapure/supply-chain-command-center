import os
import pandas as pd
from faker import Faker
import numpy as np
from datetime import timedelta, date

# ---------- Configuration ----------
SEED = 42
NUM_PRODUCTS = 200
NUM_SUPPLIERS = 30
NUM_WAREHOUSES = 5
NUM_ORDERS = 500
NUM_ORDER_ITEMS = 1500  # every order gets at least one line
NUM_PURCHASE_ORDERS = 300
NUM_FORECAST_MONTHS = 12

# Write next to this script so it works from any working directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- Reproducibility ----------
Faker.seed(SEED)
np.random.seed(SEED)
faker = Faker()

# ---------- Helper lists ----------
CATEGORIES = ["Electrical", "Mechanical", "Packaging", "Raw Material", "Finished Goods"]
REGIONS = ["North", "South", "East", "West", "Central"]

# Base date as Python date; statuses are evaluated as of the snapshot date
base_date = date(2025, 1, 1)
AS_OF_DATE = date(2025, 12, 31)

# Delivery delay vs promised date (negative = early); most orders arrive on time,
# with a small long tail of carrier exceptions
DELIVERY_DELAYS = [-2, -1, 0, 1, 2, 3, 5, 7, 14, 21]
DELIVERY_DELAY_PROBS = [0.05, 0.15, 0.46, 0.12, 0.08, 0.05, 0.03, 0.02, 0.02, 0.02]
CANCEL_RATE = 0.06
FULL_FILL_RATE = 0.85  # share of shipped order lines filled in full

# ---------- 1) products ----------
rows = []
for i in range(1, NUM_PRODUCTS + 1):
    rows.append({
        "product_id": i,
        "product_name": faker.catch_phrase().replace(",", ""),
        "category": faker.random_element(CATEGORIES),
        "unit_price": round(float(np.random.uniform(5, 500)), 2),
        "lead_time_days": int(np.random.randint(1, 31)),
        "reorder_point": int(np.random.randint(5, 101)),
    })
products = pd.DataFrame(rows)
products.to_csv(os.path.join(OUTPUT_DIR, "products.csv"), index=False)

# ---------- 2) suppliers ----------
rows = []
for i in range(1, NUM_SUPPLIERS + 1):
    rows.append({
        "supplier_id": i,
        "supplier_name": faker.company().replace(",", ""),
        "region": faker.random_element(REGIONS),
        "category_specialization": faker.random_element(CATEGORIES),
        "rating": round(float(np.random.uniform(1.0, 5.0)), 2),
    })
suppliers = pd.DataFrame(rows)
suppliers.to_csv(os.path.join(OUTPUT_DIR, "suppliers.csv"), index=False)

# ---------- 3) warehouses ----------
rows = []
for i in range(1, NUM_WAREHOUSES + 1):
    rows.append({
        "warehouse_id": i,
        "warehouse_name": f"Warehouse {faker.city()}",
        "city": faker.city(),
        "region": faker.random_element(REGIONS),
        "capacity_units": int(np.random.randint(60000, 100001)),
    })
warehouses = pd.DataFrame(rows)
warehouses.to_csv(os.path.join(OUTPUT_DIR, "warehouses.csv"), index=False)

# ---------- 4) orders ----------
# Status follows the order lifecycle as of AS_OF_DATE:
#   Cancelled  -> never shipped
#   Processing -> placed in the last 2 days, not shipped yet
#   Delivered  -> delivery date on or before AS_OF_DATE
#   Delayed    -> promised date passed, not delivered yet
#   In Transit -> shipped, promised date still ahead
rows = []
delivery = {}  # order_id -> (promised_date, actual_date or None)
for i in range(1, NUM_ORDERS + 1):
    order_date = base_date + timedelta(days=int(np.random.randint(0, 365)))
    promised_date = order_date + timedelta(days=int(np.random.randint(2, 9)))
    delay = int(np.random.choice(DELIVERY_DELAYS, p=DELIVERY_DELAY_PROBS))
    delivered_date = promised_date + timedelta(days=delay)

    if np.random.rand() < CANCEL_RATE:
        status = "Cancelled"
    elif order_date > AS_OF_DATE - timedelta(days=2):
        status = "Processing"
    elif delivered_date <= AS_OF_DATE:
        status = "Delivered"
    elif promised_date < AS_OF_DATE:
        status = "Delayed"
    else:
        status = "In Transit"

    if status in ("Delivered", "Delayed", "In Transit"):
        actual_date = delivered_date if status == "Delivered" else None
        delivery[i] = (promised_date, actual_date)

    rows.append({
        "order_id": i,
        "order_date": order_date,
        "warehouse_id": int(np.random.randint(1, NUM_WAREHOUSES + 1)),
        "customer_name": faker.name().replace(",", ""),
        "status": status,
    })
orders = pd.DataFrame(rows)
orders.to_csv(os.path.join(OUTPUT_DIR, "orders.csv"), index=False)

# ---------- 5) order_items ----------
# One line per order guaranteed, remaining lines spread at random;
# a product appears at most once per order
lines_per_order = 1 + np.random.multinomial(
    NUM_ORDER_ITEMS - NUM_ORDERS, [1 / NUM_ORDERS] * NUM_ORDERS
)
rows = []
order_item_id = 1
for order_id, num_lines in zip(orders["order_id"], lines_per_order):
    shipped = order_id in delivery
    product_ids = np.random.choice(np.arange(1, NUM_PRODUCTS + 1), size=num_lines, replace=False)
    order_rows = []
    for product_id in product_ids:
        ordered_qty = int(np.random.randint(1, 50))
        if not shipped:
            fulfilled_qty = 0
        elif np.random.rand() < FULL_FILL_RATE:
            fulfilled_qty = ordered_qty
        else:
            fulfilled_qty = int(np.random.randint(0, ordered_qty))  # short-shipped
        order_rows.append({
            "order_item_id": order_item_id,
            "order_id": int(order_id),
            "product_id": int(product_id),
            "ordered_qty": ordered_qty,
            "fulfilled_qty": fulfilled_qty,
        })
        order_item_id += 1
    # A shipped order must ship at least one line
    if shipped and all(r["fulfilled_qty"] == 0 for r in order_rows):
        order_rows[0]["fulfilled_qty"] = order_rows[0]["ordered_qty"]
    rows.extend(order_rows)
order_items = pd.DataFrame(rows)
order_items.to_csv(os.path.join(OUTPUT_DIR, "order_items.csv"), index=False)

# ---------- 6) inventory ----------
rows = []
inventory_id = 1
for product_id in range(1, NUM_PRODUCTS + 1):
    for warehouse_id in range(1, NUM_WAREHOUSES + 1):
        stock_on_hand = int(np.random.randint(0, 500))
        reserved_qty = int(np.random.randint(0, min(stock_on_hand, 50) + 1))
        last_updated = base_date + timedelta(days=int(np.random.randint(0, 365)))
        rows.append({
            "inventory_id": inventory_id,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "stock_on_hand": stock_on_hand,
            "reserved_qty": reserved_qty,
            "last_updated": last_updated,
        })
        inventory_id += 1
inventory = pd.DataFrame(rows)
inventory.to_csv(os.path.join(OUTPUT_DIR, "inventory.csv"), index=False)

# ---------- 7) purchase_orders ----------
# Planned lead time comes from the product; lower-rated suppliers deliver late more often.
# Status as of AS_OF_DATE: Received (has actual_date), Released (open), Pending (just raised), Cancelled
product_lead_time = dict(zip(products["product_id"], products["lead_time_days"]))
supplier_rating = dict(zip(suppliers["supplier_id"], suppliers["rating"]))
rows = []
for i in range(1, NUM_PURCHASE_ORDERS + 1):
    supplier_id = int(np.random.randint(1, NUM_SUPPLIERS + 1))
    warehouse_id = int(np.random.randint(1, NUM_WAREHOUSES + 1))
    product_id = int(np.random.randint(1, NUM_PRODUCTS + 1))
    order_date = base_date + timedelta(days=int(np.random.randint(0, 365)))
    lead_time = int(product_lead_time[product_id])
    expected_date = order_date + timedelta(days=lead_time)

    late_probability = 0.10 + (5 - supplier_rating[supplier_id]) * 0.08
    if np.random.rand() < late_probability:
        delay = int(np.random.randint(1, 8))
    else:
        delay = int(np.random.randint(-2, 1))
    received_date = expected_date + timedelta(days=delay)

    actual_date = None
    if np.random.rand() < CANCEL_RATE:
        status = "Cancelled"
    elif received_date <= AS_OF_DATE:
        status = "Received"
        actual_date = received_date
    elif order_date > AS_OF_DATE - timedelta(days=3):
        status = "Pending"
    else:
        status = "Released"

    rows.append({
        "po_id": i,
        "supplier_id": supplier_id,
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "order_date": order_date,
        "expected_date": expected_date,
        "actual_date": actual_date,
        "quantity": int(np.random.randint(10, 500)),
        "status": status,
        "lead_time_days": lead_time,
    })
purchase_orders = pd.DataFrame(rows)
purchase_orders.to_csv(os.path.join(OUTPUT_DIR, "purchase_orders.csv"), index=False)

# ---------- 8) shipments ----------
# One shipment per shipped order line; dates and status come from the parent order
rows = []
shipment_id = 1
for item in order_items.itertuples():
    if item.fulfilled_qty == 0:
        continue
    promised_date, actual_date = delivery[item.order_id]
    status = orders.at[item.order_id - 1, "status"]
    delay_days = max(0, (actual_date - promised_date).days) if actual_date else None
    rows.append({
        "shipment_id": shipment_id,
        "order_id": item.order_id,
        "product_id": item.product_id,
        "promised_date": promised_date,
        "actual_date": actual_date,
        "status": status,
        "delay_days": delay_days,
        "shipped_qty": item.fulfilled_qty,
    })
    shipment_id += 1
shipments = pd.DataFrame(rows).astype({"delay_days": "Int64"})
shipments.to_csv(os.path.join(OUTPUT_DIR, "shipments.csv"), index=False)

# ---------- 9) forecasts ----------
rows = []
forecast_id = 1
for product_id in range(1, NUM_PRODUCTS + 1):
    for month_offset in range(NUM_FORECAST_MONTHS):
        forecast_month = date(base_date.year, month_offset + 1, 1)
        forecast_qty = int(np.random.randint(50, 500))
        actual_qty = int(np.random.randint(max(0, forecast_qty - 50), forecast_qty + 50))
        rows.append({
            "forecast_id": forecast_id,
            "product_id": product_id,
            "forecast_month": forecast_month,
            "forecast_qty": forecast_qty,
            "actual_qty": actual_qty,
        })
        forecast_id += 1
forecasts = pd.DataFrame(rows)
forecasts.to_csv(os.path.join(OUTPUT_DIR, "forecasts.csv"), index=False)

print("Data generation complete: all 9 tables generated.")
print(f"Output folder: {OUTPUT_DIR}")
for f in [
    "products.csv", "suppliers.csv", "warehouses.csv",
    "orders.csv", "order_items.csv", "inventory.csv",
    "purchase_orders.csv", "shipments.csv", "forecasts.csv"
]:
    path = os.path.join(OUTPUT_DIR, f)
    print(f"  {path} -> {pd.read_csv(path).shape[0]} rows")
