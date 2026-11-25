import pandas as pd
import pytest

from retailgenius.forecasting import (_predict_average, _predict_last_year, backtest, backtest_cutoffs,
                                      daily_sales, forecast_sales)


def constant_orders(start="2009-01-01", end="2012-12-31", per_day=100.0):
    """Synthetic data: exactly `per_day` sales every day, so every right answer is known."""
    days = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"order_date": days, "sales": per_day, "order_id": range(len(days))})


def test_daily_sales_fills_days_without_orders_with_zero(orders):
    daily = daily_sales(orders)
    assert list(daily.columns) == ["ds", "y"]
    assert len(daily) == (pd.Timestamp("2012-12-30") - pd.Timestamp("2010-03-15")).days + 1
    assert daily.loc[daily["ds"] == "2012-01-10", "y"].item() == pytest.approx(150.0)  # 2 rows, same day
    assert daily.loc[daily["ds"] == "2012-01-11", "y"].item() == 0.0                    # no orders


def test_cutoffs_are_last_three_half_years():
    series = daily_sales(constant_orders()).set_index("ds")["y"]
    assert backtest_cutoffs(series) == [pd.Timestamp(d) for d in ("2011-07-01", "2012-01-01", "2012-07-01")]


def test_cutoffs_skip_folds_without_a_year_of_history():
    series = daily_sales(constant_orders(start="2011-06-01")).set_index("ds")["y"]
    assert backtest_cutoffs(series) == [pd.Timestamp("2012-07-01")]


def test_last_year_baseline_copies_same_date_one_year_earlier():
    train = pd.Series([5.0, 7.0], index=pd.to_datetime(["2011-03-01", "2011-03-02"]))
    pred = _predict_last_year(train, pd.date_range("2012-03-01", periods=3))
    assert pred.tolist() == [5.0, 7.0, 0.0]          # no data a year before 2012-03-03 -> 0


def test_average_baseline_spreads_monthly_mean_over_days():
    train = daily_sales(constant_orders(end="2011-12-31")).set_index("ds")["y"]
    pred = _predict_average(train, pd.date_range("2012-02-01", "2012-02-29"))
    # training = 1,095 days over 36 months -> average month = 100 * 1095 / 36; Feb 2012 gets exactly that
    assert pred.sum() == pytest.approx(100 * 1095 / 36)
    assert pred.nunique() == 1                       # spread evenly over the 29 days


def test_backtest_metrics_with_known_errors():
    models = {
        "perfect": lambda train, days: pd.Series(100.0, index=days),
        "double": lambda train, days: pd.Series(200.0, index=days),
    }
    summary, details = backtest(constant_orders(), models=models)
    s = summary.set_index("model")
    assert s.loc["perfect", "MAPE %"] == pytest.approx(0.0)
    assert s.loc["double", "MAPE %"] == pytest.approx(100.0)    # always 2x the actual -> 100% error
    assert s.loc["perfect", "months"] == 18                     # 3 folds x 6 months
    assert summary.iloc[0]["model"] == "perfect"                # best model first
    assert set(details.columns) >= {"model", "cutoff", "month", "actual", "predicted"}


def test_backtest_with_too_little_history_returns_empty():
    summary, details = backtest(constant_orders(start="2012-06-01"))
    assert summary.empty and details.empty


def test_prophet_forecast_extends_history():
    history, forecast = forecast_sales(constant_orders(start="2012-01-01"), days=30)
    assert len(forecast) == len(history) + 30
    assert {"yhat", "yhat_lower", "yhat_upper"} <= set(forecast.columns)
