import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Load orders
orders = pd.read_csv("data/raw/olist_orders_dataset.csv", usecols=[
    "order_id", "customer_id", "order_status", "order_purchase_timestamp"
])
orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])

# Olist has no order_value in orders — pull price sum from order_items
items = pd.read_csv("data/raw/olist_order_items_dataset.csv")
order_values = items.groupby("order_id")["price"].sum().reset_index()
order_values.columns = ["order_id", "order_value"]

orders = orders.merge(order_values, on="order_id", how="left")

orders.to_sql("orders", engine, if_exists="replace", index=False)
print(f"Orders loaded: {len(orders)} rows")

# Load order_items
items_subset = items[["order_id", "product_id", "price"]].copy()
items_subset.to_sql("order_items", engine, if_exists="replace", index=False)
print(f"Order items loaded: {len(items_subset)} rows")
