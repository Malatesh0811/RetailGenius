from datetime import date

import pandas as pd
import pytest

from retailgenius.analytics import (DORMANT, LOYAL, REGULAR, VIP, build_rfm, daily_sales, kpis,
                                    pct_change, previous_period)


def test_kpis_counts_distinct_orders_not_rows(orders):
    result = kpis(orders)
    assert result.orders == 5                 # 6 rows, but order 1 has two product rows
    assert result.sales == pytest.approx(250.0)
    assert result.profit == pytest.approx(21.0)


@pytest.mark.parametrize("now, before, expected", [
    (110, 100, 10.0),
    (90, 100, -10.0),
    (50, -100, 150.0),     # abs() keeps the direction right when the old value was a loss
])
def test_pct_change(now, before, expected):
    assert pct_change(now, before) == pytest.approx(expected)


@pytest.mark.parametrize("before", [0, 0.0, None])
def test_pct_change_without_baseline_is_none(before):
    assert pct_change(100, before) is None


def test_previous_period_same_length_and_adjacent():
    assert previous_period(date(2012, 1, 1), date(2012, 12, 30)) == (date(2011, 1, 1), date(2011, 12, 31))
    assert previous_period(date(2012, 3, 10), date(2012, 3, 10)) == (date(2012, 3, 9), date(2012, 3, 9))


def test_rfm_frequency_counts_orders_not_rows(orders):
    rfm = build_rfm(orders).set_index("customer_name")
    assert rfm.loc["Alice", "Frequency"] == 2  # 3 rows but only orders 1 and 2
    assert rfm.loc["Bob", "Frequency"] == 2
    assert rfm.loc["Carol", "Frequency"] == 1


def test_rfm_recency_and_monetary(orders):
    rfm = build_rfm(orders).set_index("customer_name")
    # snapshot = last order date + 1 day = 2012-12-31
    assert rfm.loc["Bob", "Recency"] == 1
    assert rfm.loc["Alice", "Recency"] == 213   # 2012-06-01 -> 2012-12-31
    assert rfm.loc["Alice", "Monetary"] == pytest.approx(180.0)


def test_rfm_segments(orders):
    seg = build_rfm(orders, vip_quantile=0.95, loyal_orders=2).set_index("customer_name")["Segment"]
    assert seg["Alice"] == VIP                  # top spender
    assert seg["Carol"] == DORMANT              # last order in 2010
    assert seg["Bob"] == LOYAL                  # 2 orders, recent, not top spender


def test_rfm_vip_beats_dormant():
    """Rule order matters: a top spender who has gone quiet is still VIP."""
    df = pd.DataFrame({
        "order_id": [1, 2, 3],
        "order_date": pd.to_datetime(["2009-01-01", "2012-12-01", "2012-12-30"]),
        "customer_name": ["Big but old", "Small", "Tiny"],
        "sales": [1000.0, 10.0, 5.0],
    })
    seg = build_rfm(df).set_index("customer_name")["Segment"]
    assert seg["Big but old"] == VIP
    assert seg["Small"] == REGULAR


def test_daily_sales_sums_per_day_in_prophet_format(orders):
    daily = daily_sales(orders)
    assert list(daily.columns) == ["ds", "y"]
    assert daily.loc[daily["ds"] == "2012-01-10", "y"].item() == pytest.approx(150.0)
