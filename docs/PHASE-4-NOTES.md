# Phase 4 — Forecast Evaluation (Backtest vs Baselines)

## Why this phase
The Forecast tab drew a line into the future, but nothing said whether that line
is any good. The first interview question about any model is **"how accurate is
it, and compared to what?"** This phase answers it with a proper backtest.

## Step 1 — Look at the data before choosing a metric
| Level | Coefficient of variation (std / mean) | Notes |
|---|---|---|
| Daily | **1.04** | 42 days with zero sales |
| Weekly | 0.41 | |
| Monthly | **0.20** | fairly flat 2009-2012 |

Daily sales are mostly noise, and MAPE divides by the actual value, so a day with
$0 sales gives a division by zero. **Decision:** train on daily data, but **score
monthly totals** — that's also the level a business plans stock and budgets at.

## Step 2 — Backtest design
**Rolling-origin backtest** ("walk-forward"): pretend it is an earlier date, train
only on data before it, forecast the next 6 months, compare with what actually happened.

```
fold 1: train 2009-01 .. 2011-06 | test 2011-07 .. 2011-12
fold 2: train 2009-01 .. 2011-12 | test 2012-01 .. 2012-06
fold 3: train 2009-01 .. 2012-06 | test 2012-07 .. 2012-12
```
3 folds x 6 months = 18 monthly predictions per model. One split could be lucky;
three is fairer. The model never sees test data (no "leakage").

**Two baselines** — a model only earns its place if it beats something simple:
- *Historical monthly average*: predict the average month seen in training.
- *Same period last year* ("seasonal naive"): each day = same date one year earlier.

**Metrics:** MAPE (mean absolute % error of monthly totals) and MAE in dollars.

## Step 3 — A bug found by sanity-checking
The first run gave **MAPE 12,678%** for the average baseline — impossible on a flat
series. Cause: windows of "183 days" from 2012-01-01 ended on **2012-07-01**,
creating a 1-day "July" with tiny sales; dividing by it blew up the average.
**Fix:** test windows are whole calendar months (`pd.DateOffset(months=6)`).
Lesson: when a metric looks absurd, find the bug before believing the number.

## Step 4 — The honest result
```
python -m retailgenius.forecasting
```
| Model | Monthly MAPE | MAE |
|---|---|---|
| Baseline: historical monthly average | **12.1%** | $36,750 |
| Prophet (default settings) | 14.2% | $45,017 |
| Baseline: same period last year | 20.8% | $63,399 |

**Prophet beats "same as last year" but loses to a plain average.** The data has
almost no trend and weak seasonality, so there's little for Prophet to learn and
its flexibility mostly fits noise.

I tried a few Prophet settings (fewer changepoints, simpler yearly seasonality):
best was 14.1%. I **did not** keep tuning to these test months — choosing settings
because they score well on the test folds is overfitting the backtest, and the
number would no longer be honest.

## What changed in the code
| File | Change |
|---|---|
| `retailgenius/forecasting.py` | **New.** `daily_sales`, `forecast_sales` (moved from analytics.py) + `backtest`, `backtest_cutoffs`, two baseline models. Runnable with `python -m`. |
| `daily_sales()` | Now fills days with no orders with **0** (before, those days were just missing, so Prophet never saw a zero day). |
| `app.py` Forecast tab | 80% uncertainty band on the projection; new **"How accurate is this forecast?"** section: runs the backtest on the current filters, shows the table, says plainly when a baseline wins, and charts predicted vs actual per month. Cached with `st.cache_data`. If filters leave < 12 months of history, it says so. |
| `analytics.py` | Forecasting removed (KPIs + RFM only). |
| `README.md` | Forecast section now shows the real backtest table instead of "seasonality detection". |

`backtest(data, models=...)` takes the models as a dict of functions — that lets
the tests plug in fake models with known errors.

## Tests (7 new → 32 total)
- `daily_sales` fills missing days with 0.
- Cutoffs are the last three half-years; folds without 12 months of history are dropped.
- "Last year" baseline copies the same date a year earlier; "average" baseline spreads
  the monthly mean evenly.
- **Metric math:** on constant synthetic sales (100/day), a "perfect" fake model scores
  MAPE 0% and a "always double" model scores exactly 100%, over 18 months.
- Too little history → empty result (no crash).
- Prophet smoke test: forecast = history + 30 days, with `yhat_lower/upper`.

## Checkpoint (passed)
- `pytest` → 32 passed.
- App: forecast chart includes the 80% band; accuracy check shows the table above and
  the "baseline beats Prophet" message; filtering to only 2012 shows "not enough history".

## Interview talking points
- "I evaluated the forecast with a rolling backtest against naive baselines. Prophet
  scored 14.2% monthly MAPE but a simple historical average scored 12.1%, so I report
  that in the app rather than overselling the model."
- "I scored monthly instead of daily because daily sales have a coefficient of
  variation over 1 and zero-sales days make MAPE undefined."
- "I didn't tune hyperparameters on the test folds — that would overfit the backtest."
