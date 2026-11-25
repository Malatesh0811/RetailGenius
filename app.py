"""RetailGenius - Streamlit UI.

This file only lays out the page. All logic lives in the `retailgenius` package
(data, analytics, agent, etl), which is unit-tested in tests/.
"""
import json
import os

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from retailgenius import ui
from retailgenius.agent import DEFAULT_MODEL, ask_with_sql, build_sql_agent
from retailgenius.analytics import DORMANT, LOYAL, REGULAR, VIP, build_rfm, kpis, pct_change, previous_period
from retailgenius.data import DB_PATH, PROJECT_ROOT, filter_orders, load_orders
from retailgenius.forecasting import backtest, forecast_sales

st.set_page_config(page_title="RetailGenius", page_icon="🚀", layout="wide")
ui.apply_theme()


# --- Settings: from .streamlit/secrets.toml (or Streamlit Cloud secrets), else environment variables ---
def get_setting(name, default=None):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except FileNotFoundError:
        pass  # no secrets.toml at all
    return os.environ.get(name, default)


GROQ_API_KEY = get_setting("GROQ_API_KEY")
GROQ_MODEL = get_setting("GROQ_MODEL", DEFAULT_MODEL)
# A public deployment shares one API key with every visitor, so cap questions per browser session.
MAX_QUESTIONS = int(get_setting("MAX_QUESTIONS_PER_SESSION", 15))


# --- Cached wrappers: Streamlit caching stays in the UI layer, the package stays plain Python ---
@st.cache_data
def cached_orders():
    return load_orders()


@st.cache_data(show_spinner=False)  # same filters -> reuse the result instead of refitting 3 models
def cached_forecast(data, days):
    return forecast_sales(data, days)


@st.cache_data(show_spinner=False)
def cached_backtest(data):
    return backtest(data)


@st.cache_data
def latest_eval_score():
    """Score from the last `python -m retailgenius.evaluation` run, if the results file exists."""
    path = PROJECT_ROOT / "evals" / "results.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: data[k] for k in ("passed", "total", "model")}


@st.cache_resource  # build the agent once per key/model, not on every question
def cached_agent(api_key, model):
    return build_sql_agent(api_key, model)


try:
    df_raw = cached_orders()
except Exception as e:  # show the real reason instead of hiding it
    st.error(f"❌ Could not load data from '{DB_PATH.name}': {e}")
    st.stop()

# --- Sidebar filters ---
with st.sidebar:
    st.markdown(ui.SIDEBAR_BRAND, unsafe_allow_html=True)
    st.markdown(f'<div style="display:flex; align-items:center; gap:8px; color:#fff; margin-bottom:10px;">'
                f'{ui.ICON_FILTER} <span>Filters</span></div>', unsafe_allow_html=True)

    min_date = df_raw["order_date"].min().date()
    max_date = df_raw["order_date"].max().date()
    date_range = st.date_input("Period", value=(min_date, max_date), min_value=min_date,
                               max_value=max_date, label_visibility="collapsed")
    all_regions = sorted(df_raw["region"].unique())
    sel_region = st.multiselect("Region", all_regions, default=all_regions)
    all_cats = sorted(df_raw["product_category"].unique())
    sel_cat = st.multiselect("Category", all_cats, default=all_cats)

# While only the start date is picked, date_input returns 1 value -> the end defaults to the last date.
start_date = date_range[0] if len(date_range) >= 1 else min_date
end_date = date_range[1] if len(date_range) == 2 else max_date
df = filter_orders(df_raw, start_date, end_date, sel_region, sel_cat)

if df.empty:
    st.warning("⚠️ No data matches filters.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Forecast", "Analyst", "Segmentation"])


def money(value):
    """$1.52M / $381.5K / $950 - short and readable on a metric card."""
    for size, suffix in ((1_000_000, "M"), (1_000, "K")):
        if abs(value) >= size:
            return f"${value / size:,.{2 if suffix == 'M' else 1}f}{suffix}"
    return f"${value:,.0f}"


def delta_label(now, before):
    change = pct_change(now, before)
    return None if change is None else f"{change:+.1f}% vs prev. period"


# ==========================================
# TAB 1: OVERVIEW
# ==========================================
with tab1:
    ui.header("Performance Metrics", ui.ICON_DASHBOARD)

    # Deltas compare with the period of the same length right before the selected one (same filters).
    now = kpis(df)
    prev_start, prev_end = previous_period(start_date, end_date)
    before = kpis(filter_orders(df_raw, prev_start, prev_end, sel_region, sel_cat))

    if before.orders:
        st.caption(f"Deltas compare {start_date} → {end_date} with the previous period {prev_start} → {prev_end}.")
    else:
        st.caption("No data before the selected period, so there is nothing to compare with "
                   "(pick a later start date to see period-over-period change).")
    c1, c2, c3 = st.columns(3, gap="large")
    c1.metric("Total Revenue", money(now.sales), delta_label(now.sales, before.sales))
    c2.metric("Net Profit", money(now.profit), delta_label(now.profit, before.profit))
    c3.metric("Orders", f"{now.orders:,}", delta_label(now.orders, before.orders))
    st.caption(f"Profit margin: {now.profit / now.sales * 100:.1f}%" if now.sales else "")

    st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)
    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        st.subheader("Revenue Composition")
        fig_pie = px.pie(df, names="product_category", values="sales", hole=0.7,
                         color_discrete_sequence=px.colors.sequential.Teal_r)
        fig_pie.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(ui.transparent(fig_pie, showlegend=False, margin=dict(t=0, b=0, l=0, r=0)), width="stretch")
        ui.context_box("💡 Revenue Mix:", "Breakdown of total sales by category. Larger slices indicate your "
                       "core revenue drivers. Use this to identify which product lines are your \"Cash Cows.\"")

    with col_right:
        st.subheader("Top 8 Provinces by Profit")
        prov = df.groupby("province")["profit"].sum().reset_index().sort_values("profit").tail(8)
        fig_bar = px.bar(prov, x="profit", y="province", orientation="h",
                         color="profit", color_continuous_scale="Teal")
        st.plotly_chart(ui.transparent(fig_bar, xaxis_title="Net Profit ($)", yaxis_title=None), width="stretch")
        ui.context_box("💡 Profit Hotspots:", "Ranking of provinces by Net Profit (not just Sales). "
                       '<span style="color:#2dd4bf">Teal bars</span> indicate your most efficient markets.')

# ==========================================
# TAB 2: FORECAST
# ==========================================
with tab2:
    ui.header("Sales Forecast", ui.ICON_FORECAST)
    c_ctrl, c_viz = st.columns([1, 3], gap="medium")

    with c_ctrl:
        st.markdown("**Model Config**")
        days_pred = st.slider("Projection Horizon", 30, 365, 90)
        # A button is True only for the one rerun right after the click, so clicking any other
        # widget would hide the chart again. Remember the request in session_state instead.
        if st.button("Run Simulation", type="primary", width="stretch"):
            st.session_state.show_forecast = True

    with c_viz:
        if st.session_state.get("show_forecast"):
            with st.spinner("Calculating future trends..."):
                history, forecast = cached_forecast(df, days_pred)

            future = forecast[forecast["ds"] > history["ds"].max()]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=history["ds"], y=history["y"], name="Historical",
                                     mode="markers", marker=dict(color="#2dd4bf", size=3, opacity=0.5)))
            # 80% uncertainty band for the future days: upper edge, then lower edge filled up to it
            fig.add_trace(go.Scatter(x=future["ds"], y=future["yhat_upper"], mode="lines",
                                     line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=future["ds"], y=future["yhat_lower"], name="80% interval", mode="lines",
                                     line=dict(width=0), fill="tonexty", fillcolor="rgba(56,189,248,0.15)"))
            fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"], name="Projection",
                                     mode="lines", line=dict(color="#38bdf8", width=2)))
            st.plotly_chart(ui.transparent(fig, xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#1e293b")),
                            width="stretch")
            ui.context_box("💡 Prophet Forecast:", 'The <span style="color:#38bdf8">Blue Line</span> is the '
                           f"model's fit on past data plus its projection for the next {days_pred} days; the "
                           "shaded band is its 80% uncertainty interval. Daily sales are very noisy, so read "
                           "the line as the expected level, not a prediction for any single day.")

    # --- How accurate is it? Backtest on data the model never saw ---
    st.markdown("#### How accurate is this forecast?")
    st.caption("Rolling backtest: train on everything before a cutoff, forecast the next 6 months, compare "
               "with what actually happened. Repeated for the last 3 half-years and scored on monthly totals. "
               "Prophet is compared with two simple baselines - a model is only useful if it beats them.")
    if st.button("Run accuracy check"):
        st.session_state.show_backtest = True
    if st.session_state.get("show_backtest"):
        with st.spinner("Fitting one model per fold..."):
            summary, details = cached_backtest(df)
        if summary.empty:
            st.info("Not enough history in the selected period (need 12+ months before the test windows).")
        else:
            st.dataframe(summary.style.format({"MAPE %": "{:.1f}", "MAE $": "${:,.0f}"}), hide_index=True)
            best = summary.iloc[0]["model"]
            prophet_mape = summary.set_index("model").loc["Prophet", "MAPE %"]
            if best == "Prophet":
                st.success(f"Prophet is the most accurate model here (monthly MAPE {prophet_mape:.1f}%).")
            else:
                st.warning(f"**{best}** beats Prophet (Prophet's MAPE: {prophet_mape:.1f}%). This data has "
                           "little trend or seasonality for Prophet to learn, so a simple average does as well "
                           "or better - treat the projection above as a rough guide.")
            monthly = details.pivot_table(index="month", columns="model", values="predicted")
            monthly["Actual"] = details.groupby("month")["actual"].first()
            st.line_chart(monthly)

# ==========================================
# TAB 3: AI ANALYST
# ==========================================
with tab3:
    ui.header("Intelligent Query Engine", ui.ICON_BRAIN)
    eval_score = latest_eval_score()
    if eval_score:
        st.caption(f"Benchmark: answered {eval_score['passed']}/{eval_score['total']} test questions correctly "
                   f"(model `{eval_score['model']}`, checked against hand-written SQL - see evals/results.md). "
                   "Note: the agent queries the full database; sidebar filters do not apply here.")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    def show_sql(queries):
        if queries:
            with st.expander(f"Show SQL ({len(queries)} quer{'y' if len(queries) == 1 else 'ies'})"):
                for q in queries:
                    st.code(q, language="sql")

    # Model output is rendered as plain markdown (never unsafe HTML), so it cannot inject HTML/scripts.
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            show_sql(msg.get("sql"))

    user_query = st.chat_input("Query the database...")
    if user_query:
        asked = sum(m["role"] == "user" for m in st.session_state.messages)
        if not GROQ_API_KEY:
            st.error("🚨 No Groq API key found. Add GROQ_API_KEY to .streamlit/secrets.toml "
                     "(see .streamlit/secrets.toml.example) or set it as an environment variable.")
        elif asked >= MAX_QUESTIONS:
            st.warning(f"This demo allows {MAX_QUESTIONS} questions per session to share the free API quota "
                       "fairly. Run it locally with your own key for unlimited questions (see the README).")
        else:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
            with st.chat_message("assistant"):
                with st.spinner("Querying the database..."):
                    try:
                        response, queries = ask_with_sql(cached_agent(GROQ_API_KEY, GROQ_MODEL), user_query)
                        st.markdown(response)
                        show_sql(queries)
                        st.session_state.messages.append({"role": "assistant", "content": response, "sql": queries})
                    except Exception as e:
                        st.error(f"Error: {e}")

# ==========================================
# TAB 4: SEGMENTATION (RFM)
# ==========================================
with tab4:
    ui.header("Customer Segmentation (RFM)", ui.ICON_PEOPLE)
    ui.context_box("👥 What is RFM?", "We segment customers based on <b>Recency</b> (time since last order), "
                   "<b>Frequency</b> (number of orders), and <b>Monetary</b> (total spend). "
                   "Use this to find VIPs and customers at risk of leaving.", margin_bottom=20)

    rfm = build_rfm(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("VIP Count", int((rfm["Segment"] == VIP).sum()))
    c2.metric("Loyal Count", int((rfm["Segment"] == LOYAL).sum()))
    c3.metric("At Risk", int((rfm["Segment"] == DORMANT).sum()))
    c4.metric("Avg Spend", money(rfm["Monetary"].mean()))

    col_chart, col_data = st.columns([2, 1], gap="medium")
    with col_chart:
        fig_rfm = px.scatter(rfm, x="Recency", y="Monetary", color="Segment",
                             hover_data=["customer_name", "Frequency"],
                             color_discrete_map={VIP: "#38bdf8", LOYAL: "#10b981",
                                                 DORMANT: "#94a3b8", REGULAR: "#f43f5e"})
        st.plotly_chart(ui.transparent(fig_rfm), width="stretch")
    with col_data:
        st.markdown("**Top 10 VIP customers**")
        top_vips = rfm[rfm["Segment"] == VIP].sort_values("Monetary", ascending=False).head(10)
        st.dataframe(
            top_vips[["customer_name", "Recency", "Frequency", "Monetary"]], hide_index=True, width="stretch",
            column_config={
                "customer_name": "Customer",
                "Recency": st.column_config.NumberColumn("Days since last", format="%d"),
                "Frequency": st.column_config.NumberColumn("Orders", format="%d"),
                "Monetary": st.column_config.NumberColumn("Total spend", format="dollar"),
            },
        )
