"""ETL: Superstore.xls -> sales.db (table `orders`).

Run with:  python -m retailgenius.etl
"""
import sqlite3

import pandas as pd

from retailgenius.data import DB_PATH, PROJECT_ROOT, TABLE

SOURCE_FILE = PROJECT_ROOT / "Superstore.xls"
NUMERIC_COLUMNS = ["sales", "profit", "discount", "unit_price", "shipping_cost", "product_base_margin"]


def transform(df):
    """Clean the raw Excel sheet: snake_case column names and correct types."""
    df = df.copy()
    # "Product Sub-Category" -> "product_sub_category"
    df.columns = df.columns.str.strip().str.lower().str.replace(r"[\s\-]+", "_", regex=True)
    for col in ("order_date", "ship_date"):
        df[col] = pd.to_datetime(df[col])
    df["order_quantity"] = df["order_quantity"].astype(int)
    df[NUMERIC_COLUMNS] = df[NUMERIC_COLUMNS].astype(float)
    return df


def load(df, db_path=DB_PATH):
    # if_exists="replace" makes the run idempotent: running it twice gives the same database.
    with sqlite3.connect(db_path) as conn:
        df.to_sql(TABLE, conn, index=False, if_exists="replace")


def run_etl(source=SOURCE_FILE, db_path=DB_PATH):
    df = transform(pd.read_excel(source))
    load(df, db_path)
    return df


if __name__ == "__main__":
    out = run_etl()
    print(f"ETL done: {len(out)} rows, {len(out.columns)} columns -> {DB_PATH.name}")
