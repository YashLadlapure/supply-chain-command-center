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
NUM_ORDER_ITEMS = 1500
NUM_INVENTORY = NUM_PRODUCTS * NUM_WAREHOUSES  # one row per product-warehouse
NUM_PURCHASE_ORDERS = 300
NUM_SHIPMENTS = NUM_ORDERS  # one shipment per order
NUM_FORECASTS = NUM_PRODUCTS * 12  # 12 months of forecast per product

OUTPUT_DIR = os.path.join("data", "seed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- Reproducibility ----------
Faker.seed(SEED)
np.random.seed(SEED)
faker = Faker()

# ---------- Helper lists ----------
CATEGORIES = ["Electrical", "Mechanical", "Packaging", "Raw Material", "Finished Goods"]
REGIONS = ["North", "South", "East", "West", "Central"]
STATUSES_ORDER = ["Processing", "In Transit", "Delivered", "Delayed", "Cancelled"]
STATUSES_SHIPMENT = ["In Transit", "Delivered", "Delayed"]
STATUSES_PO = ["Pending", "Released", "Received", "Cancelled"]

# Base date as Python date
base_date = date(2025, 1, 1)

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
        "capacity_units": int(np.random.randint(5000, 50001)),
    })
warehouses = pd.DataFrame(rows)
warehouses.to_csv(os.path.join(OUTPUT_DIR, "warehouses.csv"), index=False)

# ---------- 4) orders ----------
rows = []
for i in range(1, NUM_ORDERS + 1):
    order_date = base_date + timedelta(days=int(np.random.randint(0, 365)))
    rows.append({
        "order_id": i,
        "order_date": order_date,
        "warehouse_id": int(np.random.randint(1, NUM_WAREHOUSES + 1)),
        "customer_name": faker.name().replace(",", ""),
        "status": faker.random_element(STATUSES_ORDER),
    })
orders = pd.DataFrame(rows)
orders.to_csv(os.path.join(OUTPUT_DIR, "orders.csv"), index=False)

# ---------- 5) order_items ----------
rows = []
for i in range(1, NUM_ORDER_ITEMS + 1):
    order_id = int(np.random.randint(1, NUM_ORDERS + 1))
    product_id = int(np.random.randint(1, NUM_PRODUCTS + 1))
    ordered_qty = int(np.random.randint(1, 50))
    fulfilled_qty = int(np.random.randint(0, ordered_qty + 1))
    rows.append({
        "order_item_id": i,
        "order_id": order_id,
        "product_id": product_id,
        "ordered_qty": ordered_qty,
        "fulfilled_qty": fulfilled_qty,
    })
order_items = pd.DataFrame(rows)
order_items.to_csv(os.path.join(OUTPUT_DIR, "order_items.csv"), index=False)

# ---------- 6) inventory ----------
rows = []
inventory_id = 1
for product_id in range(1, NUM_PRODUCTS + 1):
    for warehouse_id in range(1, NUM_WAREHOUSES + 1):
        stock_on_hand = int(np.random.randint(0, 500))
        reserved_qty = int(np.random.randint(0, min(stock_on_hand, 50)))
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
rows = []
for i in range(1, NUM_PURCHASE_ORDERS + 1):
    supplier_id = int(np.random.randint(1, NUM_SUPPLIERS + 1))
    warehouse_id = int(np.random.randint(1, NUM_WAREHOUSES + 1))
    product_id = int(np.random.randint(1, NUM_PRODUCTS + 1))
    order_date = base_date + timedelta(days=int(np.random.randint(0, 365)))
    lead_time = int(np.random.randint(3, 30))
    expected_date = order_date + timedelta(days=lead_time)
    actual_date = expected_date + timedelta(days=int(np.random.randint(-2, 5))) if np.random.rand() > 0.2 else None
    rows.append({
        "po_id": i,
        "supplier_id": supplier_id,
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "order_date": order_date,
        "expected_date": expected_date,
        "actual_date": actual_date,
        "quantity": int(np.random.randint(10, 500)),
        "status": faker.random_element(STATUSES_PO),
        "lead_time_days": lead_time,
    })
purchase_orders = pd.DataFrame(rows)
purchase_orders.to_csv(os.path.join(OUTPUT_DIR, "purchase_orders.csv"), index=False)

# ---------- 8) shipments ----------
rows = []
for i in range(1, NUM_SHIPMENTS + 1):
    order_id = i  # one shipment per order
    product_id = int(np.random.randint(1, NUM_PRODUCTS + 1))
    promised_date = base_date + timedelta(days=int(np.random.randint(1, 365)))
    delay = int(np.random.randint(-2, 10))
    actual_date = promised_date + timedelta(days=delay) if np.random.rand() > 0.1 else None
    status = "Delivered" if actual_date is not None else faker.random_element(STATUSES_SHIPMENT)
    delay_days = max(0, delay) if actual_date is not None else None
    rows.append({
        "shipment_id": i,
        "order_id": order_id,
        "product_id": product_id,
        "promised_date": promised_date,
        "actual_date": actual_date,
        "status": status,
        "delay_days": delay_days,
        "shipped_qty": int(np.random.randint(1, 100)),
    })
shipments = pd.DataFrame(rows)
shipments.to_csv(os.path.join(OUTPUT_DIR, "shipments.csv"), index=False)

# ---------- 9) forecasts ----------
rows = []
forecast_id = 1
for product_id in range(1, NUM_PRODUCTS + 1):
    for month_offset in range(12):
        # Approximate month as 30 days
        forecast_month = base_date + timedelta(days=month_offset * 30)
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

print("Phase 1 complete: all 9 tables generated.")
print(f"Output folder: {OUTPUT_DIR}")
for f in [
    "products.csv", "suppliers.csv", "warehouses.csv",
    "orders.csv", "order_items.csv", "inventory.csv",
    "purchase_orders.csv", "shipments.csv", "forecasts.csv"
]:
    path = os.path.join(OUTPUT_DIR, f)
    print(f"  {path} -> {pd.read_csv(path).shape[0]} rows")