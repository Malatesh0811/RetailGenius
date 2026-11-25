"""Shared test data: a tiny orders table where every expected answer is easy to work out by hand."""
import sqlite3

import pandas as pd
import pytest


@pytest.fixture
def orders():
    rows = [
        # order_id, order_date,  customer, sales, profit, region,  province,  category
        (1, "2012-01-10", "Alice", 100.0, 10.0, "West", "Alberta", "Technology"),
        (1, "2012-01-10", "Alice", 50.0,   5.0, "West", "Alberta", "Furniture"),   # same order, 2nd product row
        (2, "2012-06-01", "Alice", 30.0,   3.0, "West", "Alberta", "Technology"),
        (3, "2012-12-30", "Bob",   20.0,  -2.0, "East", "Ontario", "Furniture"),
        (4, "2010-03-15", "Carol", 40.0,   4.0, "East", "Ontario", "Technology"),  # last order long ago
        (5, "2011-12-31", "Bob",   10.0,   1.0, "East", "Ontario", "Furniture"),
    ]
    df = pd.DataFrame(rows, columns=["order_id", "order_date", "customer_name", "sales", "profit",
                                     "region", "province", "product_category"])
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


@pytest.fixture
def orders_db(orders, tmp_path):
    """The same rows saved to a temporary SQLite file (dates stored as text, like the real ETL)."""
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as conn:
        orders.assign(order_date=orders["order_date"].astype(str)).to_sql("orders", conn, index=False)
    return path
