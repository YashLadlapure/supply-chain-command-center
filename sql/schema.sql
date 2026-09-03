-- Drop existing tables (optional, for clean re-runs)
DROP TABLE IF EXISTS
    forecasts,
    shipments,
    purchase_orders,
    inventory,
    order_items,
    orders,
    warehouses,
    suppliers,
    products
CASCADE;

-- products
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    lead_time_days INT,
    reorder_point INT
);

-- suppliers
CREATE TABLE suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    region TEXT NOT NULL,
    category_specialization TEXT,
    rating NUMERIC(3,2)
);

-- warehouses
CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    warehouse_name TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    capacity_units INT NOT NULL
);

-- orders
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    order_date DATE NOT NULL,
    warehouse_id INT NOT NULL,
    customer_name TEXT,
    status TEXT NOT NULL,
    CONSTRAINT fk_orders_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses (warehouse_id)
);

-- order_items
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    ordered_qty INT NOT NULL,
    fulfilled_qty INT NOT NULL,
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id),
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products (product_id)
);

-- inventory
CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    stock_on_hand INT NOT NULL,
    reserved_qty INT NOT NULL,
    last_updated DATE NOT NULL,
    CONSTRAINT fk_inventory_product
        FOREIGN KEY (product_id)
        REFERENCES products (product_id),
    CONSTRAINT fk_inventory_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses (warehouse_id)
);

-- purchase_orders
CREATE TABLE purchase_orders (
    po_id SERIAL PRIMARY KEY,
    supplier_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    product_id INT NOT NULL,
    order_date DATE NOT NULL,
    expected_date DATE NOT NULL,
    actual_date DATE,
    quantity INT NOT NULL,
    status TEXT NOT NULL,
    lead_time_days INT,
    CONSTRAINT fk_po_supplier
        FOREIGN KEY (supplier_id)
        REFERENCES suppliers (supplier_id),
    CONSTRAINT fk_po_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses (warehouse_id),
    CONSTRAINT fk_po_product
        FOREIGN KEY (product_id)
        REFERENCES products (product_id)
);

-- shipments
CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    promised_date DATE NOT NULL,
    actual_date DATE,
    status TEXT NOT NULL,
    delay_days INT,
    shipped_qty INT NOT NULL,
    CONSTRAINT fk_shipments_order
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id),
    CONSTRAINT fk_shipments_product
        FOREIGN KEY (product_id)
        REFERENCES products (product_id)
);

-- forecasts
CREATE TABLE forecasts (
    forecast_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL,
    forecast_month DATE NOT NULL,
    forecast_qty INT NOT NULL,
    actual_qty INT NOT NULL,
    CONSTRAINT fk_forecasts_product
        FOREIGN KEY (product_id)
        REFERENCES products (product_id)
);