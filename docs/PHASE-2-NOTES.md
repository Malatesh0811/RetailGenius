# Phase 2 — Bug Fixes & Safety

## Why this phase
Phase 1 made the repo look clean; this phase makes the numbers on screen *true*
and closes the security holes. In an interview, "my dashboard showed 8,399
orders but there were really 5,496" is the kind of thing a sharp interviewer
finds by asking one question.

## Correctness bugs fixed

| # | Bug | Effect | Fix |
|---|---|---|---|
| 1 | **RFM Frequency counted rows**, not orders (`'customer_id': 'count'`) | One order has several product rows, so Frequency was inflated → **78 customers wrongly labelled "Loyal"** (538 → 460) | `Frequency=('order_id', 'nunique')` |
| 2 | **"Transactions" card** used `df.shape[0]` | Showed 8,399 instead of 5,496 real orders | `order_id.nunique()`, card renamed "Orders" |
| 3 | **Fake KPI deltas** ("Global Sales", "Total Orders" shown as green arrows) | Looked like growth numbers but were static text; README claimed "dynamic growth deltas" | Real % change vs the previous period of equal length, same filters. E.g. 2012 revenue **+8.2%** vs 2011 (matches SQL). No earlier data → no arrow. |
| 4 | **Filters ignored mid-selection** | While only the start date was picked, the `else` branch returned *all* data — region & category filters silently ignored | New `filter_orders()` always applies all three filters; a missing end date means "until the last date" |
| 5 | **Forecast caption always said "90 days"** | Wrong whenever the slider moved | f-string uses `days_pred` |
| 6 | **Column guessing in `load_data`** could rename `customer_segment` → `customer_id` | RFM would silently group by segment (3 "customers") | Removed guessing. The ETL defines the schema, so we check `REQUIRED_COLUMNS` and fail with a clear message |
| 7 | `except Exception: return None` in loader | Every DB problem showed the same vague message | Error now shows the real reason |
| 8 | `verify_answer.py` used `BETWEEN '2012-01-01' AND '2012-12-31'` | Dates are stored as text `'2012-12-31 00:00:00'`, which sorts *after* `'2012-12-31'` → last day excluded (no data on that day here, but the query was wrong) | `strftime('%Y', order_date) = '2012'` |

## Security fixes

| Risk | Before | After |
|---|---|---|
| **LLM could modify data** | Agent had a normal read-write SQLite connection; a prompt like "delete all orders" (or a prompt injection hidden in data) could run `DELETE`/`DROP` | `sqlite:///file:sales.db?mode=ro&uri=true` — SQLite itself refuses writes. Also `include_tables=["orders"]` |
| **HTML injection from LLM output** | Response pasted into `<div>` with `unsafe_allow_html=True` → model output like `<img onerror=...>` would be executed as HTML | Plain `st.markdown(response)`; Streamlit escapes HTML. Remaining `unsafe_allow_html` calls only render our own static CSS/icons |
| **CORS / XSRF disabled** in `.streamlit/config.toml` | Other websites could send requests to the app on the user's behalf | Lines removed → Streamlit's protections back on |

## Smaller cleanups
- Agent is built once with `@st.cache_resource` instead of on every question.
- `agent.run()` (deprecated) → `agent.invoke({"input": ...})["output"]`.
- RFM segments with `np.select` (vectorised) and the 95th-percentile VIP threshold
  computed once, not once per customer inside `apply`.
- `use_container_width=True` (deprecated) → `width="stretch"`.
- Bar chart title says "Top 8 Provinces by Profit" (it was labelled "Regional"
  but plotted provinces).

## Main code
```python
def filter_orders(data, start, end, regions, categories):
    return data[
        data['order_date'].between(pd.Timestamp(start), pd.Timestamp(end))
        & data['region'].isin(regions)
        & data['product_category'].isin(categories)
    ]

rfm = data.groupby('customer_name').agg(
    Recency=('order_date', lambda x: (snapshot_date - x.max()).days),
    Frequency=('order_id', 'nunique'),     # orders, not rows
    Monetary=('sales', 'sum'),
)

db = SQLDatabase.from_uri(f"sqlite:///file:{DB_PATH}?mode=ro&uri=true", include_tables=["orders"])
```

## Checkpoint test (all passed)
Run headlessly with `AppTest`, each number compared against hand-written SQL:
1. App loads, no errors. Orders card **5,496** = SQL `count(distinct order_id)`.
2. Period 2012 → revenue delta **+8.2%** = SQL (2012 vs 2011).
3. Only start date picked + Region = West → **1,330** orders = SQL for West (filter respected).
4. Loyal count **460** (was 538 with the row-count bug).
5. Slider 180 → caption says "next 180 days".
6. `DELETE` through the agent's connection → `attempt to write a readonly database`; still 8,399 rows.
7. A message containing `<img onerror=...>` is rendered with `allow_html = False`.
8. Agent "top 5 customers by total sales" → Emily Phan $117,124.44 … Grant Carroll $88,417.00,
   identical to `verify_customers.py`.

## Interview talking points
- "I gave the LLM a **read-only** database connection — least privilege — so
  even a prompt injection can't change data. Safety is enforced by the database,
  not by trusting the model."
- "I found my RFM frequency was counting line items instead of orders; fixing it
  moved 78 customers out of the Loyal segment. I verify agent and dashboard
  numbers against hand-written SQL."
