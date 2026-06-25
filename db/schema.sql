CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50),
    customer_id VARCHAR(50),
    order_status VARCHAR(30),
    order_purchase_timestamp TIMESTAMP,
    order_value NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL,
    order_id VARCHAR(50),
    product_id VARCHAR(50),
    price NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);
