# Phase 3 — Refactor into Modules + pytest

## Why this phase
Everything lived in one 400-line `app.py`, mixed with CSS and Streamlit calls.
You can't unit-test a function that only exists inside `with tab4:` — and
"no tests" is one of the first things a reviewer notices. Splitting the
**logic** (pure Python) from the **UI** (Streamlit) makes the logic testable.

## New structure
```
app.py                  UI only: widgets, layout, charts (~200 lines, was ~400)
retailgenius/
  data.py               load_orders(), filter_orders(), REQUIRED_COLUMNS, DB_PATH
  analytics.py          kpis(), pct_change(), previous_period(), build_rfm(), daily_sales(), forecast_sales()
  agent.py              read_only_db(), build_sql_agent(), ask()
  etl.py                transform(), load(), run_etl()   ->  python -m retailgenius.etl
  ui.py                 CSS, icons, header(), context_box(), transparent()
tests/                  25 tests
pytest.ini              tells pytest where tests are + adds project root to the import path
requirements-dev.txt    requirements.txt + pytest
```

**Rule:** only `app.py` and `ui.py` import Streamlit. Even caching
(`@st.cache_data`, `@st.cache_resource`) stays in `app.py` as thin wrappers, so
the package is plain Python that tests can import without starting a web app.

## Design decisions
| Decision | Why |
|---|---|
| `pct_change()` returns a **number** (or `None`); `app.py` formats it as text | Logic returns data, UI decides presentation — and numbers are easy to assert in tests |
| `kpis()` returns a `NamedTuple` (`now.sales`, `now.orders`) | Readable at the call site, unlike `result[0]` |
| Segment names are constants (`VIP`, `LOYAL`, ...) | Before, `'💎 VIP'` was typed in 4 places; a typo in one would silently break a count |
| `build_rfm()` thresholds are parameters (defaults 0.95 / 365 / 5) | Tests can use tiny data with a small `loyal_orders`; business can tune them later |
| `DB_PATH` is absolute (`Path(__file__)...`) | The data loads no matter which folder Streamlit is started from |
| Prophet imported inside `forecast_sales()` | It's slow to import; tests that don't forecast stay fast |
| `1_etl_pipeline.py` → `retailgenius/etl.py` | A file name starting with a digit can't be imported (`import 1_etl...` is a syntax error), so it couldn't be tested. The rename map in the old script mapped every column to itself — removed. `if_exists="replace"` replaces delete-the-file-then-write. |

**ETL proof:** ran the new ETL into a temp DB and compared with the committed
`sales.db` using `pd.testing.assert_frame_equal` → identical (8,399 rows, same columns, same values).

## The tests (25, ~3 s, no API key needed)
The fixture in `conftest.py` is a **6-row table built so every answer can be
worked out by hand** — e.g. Alice has 3 rows but only 2 orders.

| File | What it proves |
|---|---|
| `test_data.py` | dates parsed; wrong schema → clear error; end date inclusive; region + category filters applied |
| `test_analytics.py` | orders = distinct `order_id`; `pct_change` incl. negative baseline and "no baseline" → `None`; previous period is same length and adjacent; RFM Frequency/Recency/Monetary; segment rules and **priority** (VIP beats Dormant) |
| `test_etl.py` | column names snake_cased (`Product Sub-Category` → `product_sub_category`), types converted, input not mutated |
| `test_agent.py` | read-only DB allows `SELECT` but rejects `DELETE`, `DROP`, `UPDATE`, `INSERT` — the agent's safety guarantee, tested without calling the LLM |
| `test_app.py` | the full page renders on the real DB; Orders = 5,496, Loyal = 460 |

**Do the tests actually catch bugs?** I temporarily put the Phase 2 bug back
(`count` instead of `nunique`) → **3 tests failed**. Restored → 25 passed.
(This is called *mutation testing* — a test that can't fail is worthless.)

## Things learned while testing
- `streamlit run` adds the app's folder to `sys.path`
  (`streamlit/web/bootstrap.py`), which is why `from retailgenius import ...`
  works. Plain `python some_script.py` from another folder doesn't — so
  `pytest.ini` sets `pythonpath = .`.
- Streamlit reads `.streamlit/secrets.toml` and `config.toml` from the folder you
  **start it in**. Run `streamlit run app.py` from the project folder (now in the README).

## Checkpoint (passed)
- `pytest` → 25 passed.
- Forecast button with 120-day horizon works, caption says 120.
- Agent: "How many distinct orders are in the West region?" → 1,330 = SQL.

## Interview talking point
"I separated the analytics logic from the Streamlit UI so it's unit-testable.
The tests use a tiny hand-built dataset where I know every right answer, and
I checked they actually catch the line-item vs order bug by reintroducing it."
