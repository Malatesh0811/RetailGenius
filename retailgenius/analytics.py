"""Pure analytics functions (no Streamlit) - KPIs, period comparison, RFM, forecasting."""
from datetime import timedelta
from typing import NamedTuple

import numpy as np
import pandas as pd


class Kpis(NamedTuple):
    sales: float
    profit: float
    orders: int


def kpis(data):
    # One order can have several product rows, so orders = distinct order_id, not the row count.
    return Kpis(float(data["sales"].sum()), float(data["profit"].sum()), int(data["order_id"].nunique()))


def pct_change(now, before):
    """Percentage change from `before` to `now`; None when there is nothing to compare with."""
    if not before:
        return None
    return (now - before) / abs(before) * 100


def previous_period(start, end):
    """The period of the same length that ends the day before `start` (dates are inclusive)."""
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=length - 1), prev_end


# --- RFM segmentation -------------------------------------------------------------
VIP, DORMANT, LOYAL, REGULAR = "💎 VIP", "💤 Dormant", "🔥 Loyal", "🌱 Regular"
SEGMENTS = [VIP, LOYAL, DORMANT, REGULAR]


def build_rfm(data, vip_quantile=0.95, dormant_days=365, loyal_orders=5):
    """One row per customer: Recency (days since last order), Frequency (orders), Monetary (total sales), Segment.

    Rules, first match wins: top 5% spenders -> VIP, no order for over a year -> Dormant,
    5+ orders -> Loyal, everyone else -> Regular.
    """
    snapshot_date = data["order_date"].max() + timedelta(days=1)
    rfm = data.groupby("customer_name").agg(
        Recency=("order_date", lambda x: (snapshot_date - x.max()).days),
        Frequency=("order_id", "nunique"),   # orders, not rows (count() over-counted by ~50%)
        Monetary=("sales", "sum"),
    ).reset_index()

    vip_threshold = rfm["Monetary"].quantile(vip_quantile)
    rfm["Segment"] = np.select(
        [rfm["Monetary"] > vip_threshold, rfm["Recency"] > dormant_days, rfm["Frequency"] >= loyal_orders],
        [VIP, DORMANT, LOYAL],
        default=REGULAR,
    )
    return rfm


# --- Forecasting -----------------------------------------------------------------
def daily_sales(data):
    """Total sales per order date, in Prophet's expected format (columns ds, y)."""
    return data.groupby("order_date")["sales"].sum().reset_index().rename(columns={"order_date": "ds", "sales": "y"})


def forecast_sales(data, days):
    """Fit Prophet on daily sales and predict `days` ahead. Returns (history, forecast)."""
    from prophet import Prophet  # imported lazily: Prophet is slow to import and only this needs it

    history = daily_sales(data)
    model = Prophet()
    model.fit(history)
    forecast = model.predict(model.make_future_dataframe(periods=days))
    return history, forecast
