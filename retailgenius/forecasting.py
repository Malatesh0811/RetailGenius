"""Sales forecasting with Prophet, plus an honest backtest against simple baselines.

Run the backtest from the command line:  python -m retailgenius.forecasting
"""
import logging

import pandas as pd

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)  # Prophet's backend is very chatty


def daily_sales(data):
    """Total sales for EVERY calendar day (days without orders = 0), as Prophet's columns ds, y.

    Filling the gaps matters: a missing day means "no sales", and leaving it out would make
    the model think sales never drop that low.
    """
    per_day = data.groupby("order_date")["sales"].sum()
    if per_day.empty:
        return pd.DataFrame({"ds": pd.Series(dtype="datetime64[ns]"), "y": pd.Series(dtype=float)})
    all_days = pd.date_range(per_day.index.min(), per_day.index.max(), freq="D")
    per_day = per_day.reindex(all_days, fill_value=0.0)
    return pd.DataFrame({"ds": per_day.index, "y": per_day.values})


def _prophet():
    from prophet import Prophet  # imported lazily: slow to import, only needed here
    return Prophet()


def forecast_sales(data, days):
    """Fit Prophet on all daily sales and predict `days` ahead. Returns (history, forecast)."""
    history = daily_sales(data)
    model = _prophet()
    model.fit(history)
    return history, model.predict(model.make_future_dataframe(periods=days))


# --- Backtest ----------------------------------------------------------------------
# Daily sales are mostly noise (std ~ mean, some zero days -> % error undefined), so we
# train on daily data but SCORE MONTHLY totals - the level a business actually plans at.

def _predict_prophet(train, test_days):
    model = _prophet()
    model.fit(pd.DataFrame({"ds": train.index, "y": train.values}))
    return pd.Series(model.predict(pd.DataFrame({"ds": test_days}))["yhat"].values, index=test_days)


def _predict_last_year(train, test_days):
    """Seasonal naive baseline: each day gets the sales of the same date one year earlier."""
    return pd.Series(train.reindex(test_days - pd.DateOffset(years=1)).fillna(0.0).values, index=test_days)


def _predict_average(train, test_days):
    """Mean baseline: every month = the average monthly total seen in training (spread over its days)."""
    avg_month = train.resample("MS").sum().mean()
    days_in_month = test_days.days_in_month
    return pd.Series(avg_month / days_in_month, index=test_days)


MODELS = {
    "Prophet": _predict_prophet,
    "Baseline: same period last year": _predict_last_year,
    "Baseline: historical monthly average": _predict_average,
}


def backtest_cutoffs(series, n_folds=3, horizon_months=6, min_train_months=12):
    """Start dates of the test windows: the last `n_folds` blocks of `horizon_months` whole months,
    keeping only those with at least `min_train_months` of history before them."""
    end = (series.index.max() + pd.offsets.MonthBegin(1)).normalize()  # first day after the data's last month
    cutoffs = [end - pd.DateOffset(months=horizon_months * k) for k in range(n_folds, 0, -1)]
    earliest = series.index.min() + pd.DateOffset(months=min_train_months)
    return [c for c in cutoffs if c >= earliest]


def backtest(data, n_folds=3, horizon_months=6, models=None):
    """Rolling-origin backtest: for each fold, train on everything before the cutoff and forecast
    the next `horizon_months` whole months. Returns (summary, details):

    - summary: one row per model with MAPE (%) and MAE ($) of the MONTHLY totals, best first
    - details: one row per model per forecast month (actual vs predicted)
    """
    models = models or MODELS
    daily = daily_sales(data).set_index("ds")["y"]
    rows = []
    for cutoff in backtest_cutoffs(daily, n_folds, horizon_months):
        train = daily[daily.index < cutoff]
        test = daily[(daily.index >= cutoff) & (daily.index < cutoff + pd.DateOffset(months=horizon_months))]
        actual = test.resample("MS").sum()
        for name, predict in models.items():
            predicted = predict(train, test.index).resample("MS").sum()
            for month in actual.index:
                rows.append({"model": name, "cutoff": cutoff, "month": month,
                             "actual": actual[month], "predicted": predicted[month]})

    details = pd.DataFrame(rows, columns=["model", "cutoff", "month", "actual", "predicted"])
    if details.empty:
        return pd.DataFrame(columns=["model", "MAPE %", "MAE $", "months"]), details
    err = (details["actual"] - details["predicted"]).abs()
    details["abs_pct_error"] = err / details["actual"] * 100
    summary = (details.assign(abs_error=err)
               .groupby("model")
               .agg(**{"MAPE %": ("abs_pct_error", "mean"), "MAE $": ("abs_error", "mean"),
                       "months": ("month", "count")})
               .sort_values("MAPE %").reset_index())
    return summary, details


if __name__ == "__main__":
    from retailgenius.data import load_orders

    summary, details = backtest(load_orders())
    folds = [str(c.date()) for c in sorted(details["cutoff"].unique())]
    print(f"Monthly backtest - {len(folds)} folds of 6 months, test windows start: {', '.join(folds)}\n")
    print(summary.round({"MAPE %": 1, "MAE $": 0}).to_string(index=False))
