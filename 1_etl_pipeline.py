import pandas as pd
import sqlite3
import os

DB_NAME = "sales.db"
TABLE_NAME = "orders"
DATA_FILE = "Superstore.xls"   

def run_etl():
    print("🚀 Starting ETL Pipeline")

    # 1. Load Excel
    try:
        df = pd.read_excel(DATA_FILE)
    except FileNotFoundError:
        raise Exception(f"❌ File '{DATA_FILE}' not found in project folder")

    # 2. Standardize column names
    df.columns = (
        df.columns
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    # 3. Rename columns (Excel → Clean schema)
    df = df.rename(columns={
        "row_id": "row_id",
        "order_id": "order_id",
        "order_date": "order_date",
        "ship_date": "ship_date",
        "order_priority": "order_priority",
        "customer_name": "customer_name",
        "customer_segment": "customer_segment",
        "product_category": "product_category",
        "product_sub_category": "product_sub_category",
        "product_name": "product_name",
        "product_container": "product_container",
        "ship_mode": "ship_mode",
        "order_quantity": "order_quantity",
        "product_base_margin": "product_base_margin",
        "unit_price": "unit_price",
        "shipping_cost": "shipping_cost",
        "province": "province",
        "region": "region"
    })

    # 4. Data types (CRITICAL)
    df['order_date'] = pd.to_datetime(df['order_date'], dayfirst=True)
    df['ship_date'] = pd.to_datetime(df['ship_date'], dayfirst=True)

    df['order_quantity'] = df['order_quantity'].astype(int)
    df['sales'] = df['sales'].astype(float)
    df['profit'] = df['profit'].astype(float)
    df['discount'] = df['discount'].astype(float)
    df['unit_price'] = df['unit_price'].astype(float)
    df['shipping_cost'] = df['shipping_cost'].astype(float)
    df['product_base_margin'] = df['product_base_margin'].astype(float)

    # 5. Remove old DB (idempotent)
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    # 6. Load into SQLite
    conn = sqlite3.connect(DB_NAME)
    df.to_sql(TABLE_NAME, conn, index=False)
    conn.close()

    print("✅ ETL Completed Successfully")
    print(f"📦 Rows loaded: {len(df)}")
    print(f"📊 Columns loaded: {len(df.columns)}")

if __name__ == "__main__":
    run_etl()
