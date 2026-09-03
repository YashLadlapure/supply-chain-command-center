import os
import pandas as pd
from faker import Faker
import numpy as np

# ---------- Configuration ----------
SEED = 42
NUM_PRODUCTS = 200
NUM_SUPPLIERS = 30
NUM_WAREHOUSES = 5

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

# ---------- 1) products ----------
rows = []
for i in range(1, NUM_PRODUCTS + 1):
    rows.append({
        "product_id": i,
        "product_name": faker.catch_phrase().replace(",", ""),
        "category": faker.random_element(CATEGORIES),
        "unit_price": round(faker.pyfloat(min_value=5, max_value=500), 2),
        "lead_time_days": faker.random_int(1, 30),
        "reorder_point": faker.random_int(5, 100),
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
        "rating": round(faker.pyfloat(min_value=1.0, max_value=5.0), 2),
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
        "capacity_units": faker.random_int(5000, 50000),
    })
warehouses = pd.DataFrame(rows)
warehouses.to_csv(os.path.join(OUTPUT_DIR, "warehouses.csv"), index=False)

print("Phase 1 (partial) complete: products, suppliers, warehouses created.")
print(f"Output folder: {OUTPUT_DIR}")
print("Files created:")
for f in ["products.csv", "suppliers.csv", "warehouses.csv"]:
    path = os.path.join(OUTPUT_DIR, f)
    print(f"  {path} -> {pd.read_csv(path).shape[0]} rows")