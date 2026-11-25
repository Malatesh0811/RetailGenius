import sqlite3
from datetime import date

import pytest

from retailgenius.data import filter_orders, load_orders

ALL_REGIONS = ["West", "East"]
ALL_CATS = ["Technology", "Furniture"]


def test_load_orders_parses_dates(orders_db):
    df = load_orders(orders_db)
    assert len(df) == 6
    assert str(df["order_date"].dtype).startswith("datetime64")


def test_load_orders_rejects_wrong_schema(tmp_path):
    path = tmp_path / "bad.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE orders (order_id INTEGER, sales REAL)")
    with pytest.raises(ValueError, match="missing columns"):
        load_orders(path)


def test_filter_end_date_is_inclusive(orders):
    out = filter_orders(orders, date(2012, 1, 1), date(2012, 12, 30), ALL_REGIONS, ALL_CATS)
    assert set(out["order_id"]) == {1, 2, 3}        # 2012-12-30 itself is included


def test_filter_applies_region_and_category(orders):
    out = filter_orders(orders, date(2009, 1, 1), date(2012, 12, 31), ["East"], ["Furniture"])
    assert set(out["order_id"]) == {3, 5}


def test_filter_can_return_nothing(orders):
    assert filter_orders(orders, date(2009, 1, 1), date(2012, 12, 31), [], ALL_CATS).empty
