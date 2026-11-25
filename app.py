"""RetailGenius - Streamlit UI.

This file only lays out the page. All logic lives in the `retailgenius` package
(data, analytics, agent, etl), which is unit-tested in tests/.
"""
import os

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from retailgenius import ui
from retailgenius.agent import DEFAULT_MODEL, ask, build_sql_agent
from retailgenius.analytics import DORMANT, LOYAL, REGULAR, VIP, build_rfm, kpis, pct_change, previous_period
from retailgenius.data import DB_PATH, filter_orders, load_orders
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


# --- Cached wrappers: Streamlit caching stays in the UI layer, the package stays plain Python ---
@st.cache_data
def cached_orders():
    return load_orders()


@st.cache_data(show_spinner=False)  # same filters -> reuse the result instead of refitting 3 models
def cached_backtest(data):
    return backtest(data)


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

    st.caption(f"Deltas compare {start_date} → {end_date} with {prev_start} → {prev_end}.")
    c1, c2, c3 = st.columns(3, gap="large")
    c1.metric("Total Revenue", f"${now.sales/1_000_000:.2f}M", delta_label(now.sales, before.sales))
    c2.metric("Net Profit", f"${now.profit/1000:.1f}K", delta_label(now.profit, before.profit))
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
        run_btn = st.button("Run Simulation", type="primary", width="stretch")

    with c_viz:
        if run_btn:
            with st.spinner("Calculating future trends..."):
                history, forecast = forecast_sales(df, days_pred)

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
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Model output is rendered as plain markdown (never unsafe HTML), so it cannot inject HTML/scripts.
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Query the database...")
    if user_query:
        if not GROQ_API_KEY:
            st.error("🚨 No Groq API key found. Add GROQ_API_KEY to .streamlit/secrets.toml "
                     "(see .streamlit/secrets.toml.example) or set it as an environment variable.")
        else:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
            with st.chat_message("assistant"):
                with st.spinner("Querying the database..."):
                    try:
                        response = ask(cached_agent(GROQ_API_KEY, GROQ_MODEL), user_query)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
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
    c4.metric("Avg Spend", f"${rfm['Monetary'].mean():.0f}")

    col_chart, col_data = st.columns([2, 1], gap="medium")
    with col_chart:
        fig_rfm = px.scatter(rfm, x="Recency", y="Monetary", color="Segment",
                             hover_data=["customer_name", "Frequency"],
                             color_discrete_map={VIP: "#38bdf8", LOYAL: "#10b981",
                                                 DORMANT: "#94a3b8", REGULAR: "#f43f5e"})
        st.plotly_chart(ui.transparent(fig_rfm), width="stretch")
    with col_data:
        st.dataframe(rfm[rfm["Segment"] == VIP].sort_values("Monetary", ascending=False).head(10), hide_index=True)
