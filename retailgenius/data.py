"""Loading and filtering the orders table."""
import sqlite3
from pathlib import Path

import pandas as pd

# Absolute path, so the app works no matter which folder `streamlit run` is started from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "sales.db"
TABLE = "orders"

# The schema comes from retailgenius/etl.py. We check for it explicitly instead of guessing
# column names (guessing once risked treating customer_segment as the customer).
REQUIRED_COLUMNS = {"order_id", "order_date", "customer_name", "sales", "profit",
                    "region", "province", "product_category"}


def load_orders(db_path=DB_PATH):
    """Read the whole orders table, check the schema and parse order_date."""
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(f"SELECT * FROM {TABLE}", conn)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"'{TABLE}' table is missing columns: {sorted(missing)}. "
                         "Re-run: python -m retailgenius.etl")
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def filter_orders(data, start, end, regions, categories):
    """Rows with start <= order_date <= end (both inclusive) in the selected regions and categories."""
    return data[
        data["order_date"].between(pd.Timestamp(start), pd.Timestamp(end))
        & data["region"].isin(regions)
        & data["product_category"].isin(categories)
    ]
