import pandas as pd
from sqlalchemy import create_engine, text
from faker import Faker
from dotenv import load_dotenv
import os
import random

load_dotenv()
fake = Faker()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

with engine.connect() as conn:

    # ERROR 1 — Stale timestamps (freshness check will fail)
    # Push 500 rows to be 48+ hours old with NULL timestamps to simulate stale ingestion
    conn.execute(text("""
        UPDATE orders
        SET order_purchase_timestamp = NOW() - INTERVAL '72 hours'
        WHERE order_id IN (
            SELECT order_id FROM orders ORDER BY RANDOM() LIMIT 500
        )
    """))
    print("Injected: stale timestamps")

    # ERROR 2 — Null customer_ids (null rate check will fail)
    conn.execute(text("""
        UPDATE orders
        SET customer_id = NULL
        WHERE order_id IN (
            SELECT order_id FROM orders ORDER BY RANDOM() LIMIT 3500
        )
    """))
    print("Injected: null customer_ids (~34% null rate)")

    # ERROR 3 — Distribution drift (spike order_value for recent rows)
    conn.execute(text("""
        UPDATE orders
        SET order_value = order_value * 8.5
        WHERE order_purchase_timestamp >= NOW() - INTERVAL '24 hours'
    """))
    print("Injected: order_value spike (8.5x baseline)")

    # ERROR 4 — Duplicate order_ids
    conn.execute(text("""
        INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp, order_value)
        SELECT order_id, customer_id, order_status, order_purchase_timestamp, order_value
        FROM orders
        ORDER BY RANDOM()
        LIMIT 800
    """))
    print("Injected: 800 duplicate order_ids")

    # ERROR 5 — Orphan order_items (referential integrity break)
    orphan_ids = [fake.uuid4() for _ in range(1000)]
    orphan_data = pd.DataFrame({
        "order_id": orphan_ids,
        "product_id": [fake.uuid4() for _ in range(1000)],
        "price": [round(random.uniform(10, 500), 2) for _ in range(1000)]
    })
    orphan_data.to_sql("order_items", engine, if_exists="append", index=False)
    print("Injected: 1000 orphan order_items")

    conn.commit()

print("\nAll 5 error types injected. Run your DQ checks to verify.")
