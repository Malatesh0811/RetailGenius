import os
import streamlit as st
import numpy as np
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent
from datetime import timedelta

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="RetailGenius Enterprise", page_icon="🚀", layout="wide")

# --- API KEY SETUP ---
# The key is never written in the code. It is read from (1) .streamlit/secrets.toml
# locally / Streamlit Cloud secrets when deployed, or (2) the GROQ_API_KEY environment variable.
def get_setting(name, default=None):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except FileNotFoundError:
        pass  # no secrets.toml file at all -> fall back to the environment variable
    return os.environ.get(name, default)

GROQ_API_KEY = get_setting("GROQ_API_KEY")
# Groq retires models over time (llama-3.3-70b-versatile is gone), so the model is a setting, not hard-coded.
GROQ_MODEL = get_setting("GROQ_MODEL", "openai/gpt-oss-120b")

# --- 2. CUSTOM CSS (NEON GLOW + HORIZONTAL FIT) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Background */
    .stApp { background: radial-gradient(circle at top right, #0f172a, #020617); }

    /* Tabs - Big & Bold */
    button[data-baseweb="tab"] {
        font-size: 18px !important; font-weight: 700 !important;
        background-color: transparent; border: none; color: #64748b;
        padding: 12px 24px !important; transition: all 0.3s ease;
    }
    button[data-baseweb="tab"]:hover { color: #e2e8f0; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important; border-bottom: 3px solid #38bdf8 !important;
    }

    /* --- METRIC CARDS: NEON GLOW & PERMANENT EDGE --- */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        border: 2px solid #38bdf8; /* Permanent Neon Border */
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 0 15px -3px rgba(56, 189, 248, 0.3); /* Permanent Glow */
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%; /* Force Horizontal Fit */
    }
    
    /* HOVER PHYSICS: LIFT & INTENSIFY */
    div[data-testid="stMetric"]:hover {
        transform: scale(1.02) translateY(-5px); /* Lift */
        background: rgba(30, 41, 59, 0.6);
        box-shadow: 0 15px 40px -5px rgba(56, 189, 248, 0.6); /* Intense Glow */
        border-color: #7dd3fc;
    }

    /* METRIC TEXT - MASSIVE */
    div[data-testid="stMetric"] label {
        color: #94a3b8; font-size: 1rem !important; font-weight: 600; letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 3.2rem !important; font-weight: 900;
        background: -webkit-linear-gradient(0deg, #f8fafc, #bae6fd);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }

    /* --- CONTEXT BOXES (EXPLANATIONS) --- */
    .chart-context {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid #334155;
        border-left: 5px solid #38bdf8; /* Neon Accent */
        padding: 15px 20px;
        border-radius: 0 12px 12px 0;
        color: #cbd5e1;
        font-size: 14px;
        margin-top: 15px;
        line-height: 1.6;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }

</style>
""", unsafe_allow_html=True)

# --- 3. HELPER: SVG ICONS ---
def render_svg_header(title, icon_path):
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <div style="background: rgba(56, 189, 248, 0.1); padding: 10px; border-radius: 8px; color: #38bdf8;">
            {icon_path}
        </div>
        <h2 style="margin: 0; font-weight: 700; font-size: 24px; color: white;">{title}</h2>
    </div>
    """, unsafe_allow_html=True)

# Icons
ICON_DASHBOARD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>'
ICON_FORECAST = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h5l3 5 5-11 4 6h3"/><path d="M12 22a10 10 0 0 0 10-10"/></svg>'
ICON_BRAIN = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16v-4"/><path d="M12 8h.01"/><path d="M20.5 12a8.5 8.5 0 1 1-8-8.5 8.5 8.5 0 0 1 8 8.5Z"/><path d="M9 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/></svg>'
ICON_FILTER = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>'
ICON_PEOPLE = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>'

# --- 4. DATA LOADER ---
DB_PATH = "sales.db"
# The schema is defined by 1_etl_pipeline.py, so we check for it explicitly instead of
# guessing column names (guessing could silently pick e.g. customer_segment as the customer).
REQUIRED_COLUMNS = {"order_id", "order_date", "customer_name", "sales", "profit",
                    "region", "province", "product_category"}

@st.cache_data
def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM orders", conn)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"'orders' table is missing columns: {sorted(missing)}. Re-run 1_etl_pipeline.py.")
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df

try:
    df_raw = load_data()
except Exception as e:  # show the real reason instead of hiding it
    st.error(f"❌ Could not load data from '{DB_PATH}': {e}")
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 30px;">
        <h1 style="font-size: 32px; font-weight: 800; background: -webkit-linear-gradient(0deg, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;">RetailGenius</h1>
        <div style="font-size: 12px; color: #64748b; font-weight: 600; letter-spacing: 1px;">ENTERPRISE ANALYTICS</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f'<div style="display:flex; align-items:center; gap:8px; color:#fff; margin-bottom:10px;">{ICON_FILTER} <span>Filters</span></div>', unsafe_allow_html=True)
    
    min_date = df_raw['order_date'].min().date()
    max_date = df_raw['order_date'].max().date()
    date_range = st.date_input("Period", value=(min_date, max_date), min_value=min_date,
                               max_value=max_date, label_visibility="collapsed")

    all_regions = sorted(df_raw['region'].unique())
    sel_region = st.multiselect("Region", all_regions, default=all_regions)

    all_cats = sorted(df_raw['product_category'].unique())
    sel_cat = st.multiselect("Category", all_cats, default=all_cats)

# --- 6. FILTER LOGIC ---
# While the user has picked only the start date, date_input returns 1 value -> treat the end as max_date.
# (Before, that case skipped ALL filters, including region and category.)
start_date = date_range[0] if len(date_range) >= 1 else min_date
end_date = date_range[1] if len(date_range) == 2 else max_date

def filter_orders(data, start, end, regions, categories):
    """Rows between start and end (inclusive) in the selected regions and categories."""
    return data[
        data['order_date'].between(pd.Timestamp(start), pd.Timestamp(end))
        & data['region'].isin(regions)
        & data['product_category'].isin(categories)
    ]

df = filter_orders(df_raw, start_date, end_date, sel_region, sel_cat)

if df.empty:
    st.warning("⚠️ No data matches filters.")
    st.stop()

# --- 7. MAIN APP TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Forecast", "Analyst", "Segmentation"])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab1:
    render_svg_header("Performance Metrics", ICON_DASHBOARD)
    
    def kpis(data):
        # One order can have several product rows, so orders = distinct order_id, not row count.
        return data['sales'].sum(), data['profit'].sum(), data['order_id'].nunique()

    def pct_change(now, before):
        return f"{(now - before) / abs(before) * 100:+.1f}% vs prev. period" if before else None

    sales, profit, orders = kpis(df)

    # Real deltas: compare with the period of the same length right before the selected one
    # (same region/category filters). No earlier data -> no delta arrow is shown.
    period_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)
    prev_sales, prev_profit, prev_orders = kpis(filter_orders(df_raw, prev_start, prev_end, sel_region, sel_cat))

    st.caption(f"Deltas compare {start_date} → {end_date} with {prev_start} → {prev_end}.")
    c1, c2, c3 = st.columns(3, gap="large")
    c1.metric("Total Revenue", f"${sales/1_000_000:.2f}M", pct_change(sales, prev_sales))
    c2.metric("Net Profit", f"${profit/1000:.1f}K", pct_change(profit, prev_profit))
    c3.metric("Orders", f"{orders:,}", pct_change(orders, prev_orders))
    st.caption(f"Profit margin: {profit / sales * 100:.1f}%" if sales else "")

    st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2, gap="medium")
    
    with col_left:
        st.subheader("Revenue Composition")
        fig_pie = px.pie(df, names='product_category', values='sales', hole=0.7,
                         color_discrete_sequence=px.colors.sequential.Teal_r)
        fig_pie.update_traces(textposition='outside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, width="stretch")

        st.markdown("""
        <div class="chart-context">
            <strong>💡 Revenue Mix:</strong><br>
            Breakdown of total sales by category. Larger slices indicate your core revenue drivers.
            Use this to identify which product lines are your "Cash Cows."
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.subheader("Top 8 Provinces by Profit")
        prov_data = df.groupby('province')['profit'].sum().reset_index().sort_values('profit').tail(8)
        fig_bar = px.bar(prov_data, x='profit', y='province', orientation='h',
                         color='profit', color_continuous_scale='Teal')
        fig_bar.update_layout(xaxis_title="Net Profit ($)", yaxis_title=None,
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(color='#94a3b8'))
        st.plotly_chart(fig_bar, width="stretch")

        st.markdown("""
        <div class="chart-context">
            <strong>💡 Profit Hotspots:</strong><br>
            Ranking of provinces by Net Profit (not just Sales).
            <span style="color:#2dd4bf">Teal bars</span> indicate your most efficient markets.
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# TAB 2: PREDICTIVE ENGINE
# ==========================================
with tab2:
    render_svg_header("AI Demand Forecast", ICON_FORECAST)
    c_ctrl, c_viz = st.columns([1, 3], gap="medium")
    
    with c_ctrl:
        st.markdown("**Model Config**")
        days_pred = st.slider("Projection Horizon", 30, 365, 90)
        run_btn = st.button("Run Simulation", type="primary", width="stretch")

    with c_viz:
        if run_btn:
            with st.spinner("Calculating future trends..."):
                prophet_df = df.groupby('order_date')['sales'].sum().reset_index()
                prophet_df.columns = ['ds', 'y']
                
                m = Prophet()
                m.fit(prophet_df)
                future = m.make_future_dataframe(periods=days_pred)
                forecast = m.predict(future)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=prophet_df['ds'], y=prophet_df['y'], name='Historical',
                                         mode='markers', marker=dict(color='#2dd4bf', size=3, opacity=0.5)))
                fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], name='Projection',
                                         mode='lines', line=dict(color='#38bdf8', width=2)))
                
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                  font=dict(color='#94a3b8'), xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#1e293b'))
                st.plotly_chart(fig, width="stretch")

                # f-string so the text matches the slider (it used to always say "90 days")
                st.markdown(f"""
                <div class="chart-context">
                    <strong>💡 Prophet Forecast:</strong><br>
                    The <span style="color:#38bdf8">Blue Line</span> is the model's fit on past data plus its
                    projection for the next {days_pred} days.
                    Upward trends suggest growth; look for recurring patterns (seasonality).
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 3: AI ANALYST
# ==========================================
@st.cache_resource  # build the agent once per key/model, not on every question
def get_sql_agent(api_key, model):
    # Read-only connection: mode=ro makes SQLite itself reject INSERT/UPDATE/DELETE/DROP,
    # so even a bad or prompt-injected query from the LLM cannot change or wipe the data.
    db = SQLDatabase.from_uri(f"sqlite:///file:{DB_PATH}?mode=ro&uri=true", include_tables=["orders"])
    llm = ChatGroq(temperature=0, groq_api_key=api_key, model_name=model)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return create_sql_agent(llm=llm, toolkit=toolkit, agent_type="tool-calling", verbose=False)

with tab3:
    render_svg_header("Intelligent Query Engine", ICON_BRAIN)
    if "messages" not in st.session_state: st.session_state.messages = []

    # LLM output is shown as plain markdown, NOT unsafe HTML: the text comes from the model
    # (and indirectly from database contents), so it must not be able to inject HTML/scripts.
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
                with st.spinner("Processing Logic..."):
                    try:
                        agent = get_sql_agent(GROQ_API_KEY, GROQ_MODEL)
                        response = agent.invoke({"input": user_query})["output"]
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Error: {e}")

# ==========================================
# TAB 4: SEGMENTATION (RFM)
# ==========================================
with tab4:
    render_svg_header("Customer Segmentation (RFM)", ICON_PEOPLE)
    
    st.markdown("""
    <div class="chart-context" style="margin-bottom: 20px;">
        <strong>👥 What is RFM?</strong><br>
        We segment customers based on <b>Recency</b> (Time since last buy), <b>Frequency</b> (Total orders), and <b>Monetary</b> (Total spend).
        Use this to find VIPs and Customers at risk of leaving.
    </div>
    """, unsafe_allow_html=True)
    
    def build_rfm(data):
        """One row per customer with Recency (days), Frequency (orders), Monetary (total sales) and a Segment."""
        snapshot_date = data['order_date'].max() + timedelta(days=1)
        rfm = data.groupby('customer_name').agg(
            Recency=('order_date', lambda x: (snapshot_date - x.max()).days),
            # nunique, not count: one order has several product rows. count() inflated
            # Frequency (8,399 rows vs 5,496 real orders) and put too many people in "Loyal".
            Frequency=('order_id', 'nunique'),
            Monetary=('sales', 'sum'),
        ).reset_index()

        vip_threshold = rfm['Monetary'].quantile(0.95)  # computed once, not once per customer
        # First matching rule wins (same priority as before: VIP > Dormant > Loyal > Regular)
        rfm['Segment'] = np.select(
            [rfm['Monetary'] > vip_threshold, rfm['Recency'] > 365, rfm['Frequency'] >= 5],
            ['💎 VIP', '💤 Dormant', '🔥 Loyal'],
            default='🌱 Regular',
        )
        return rfm

    rfm = build_rfm(df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("VIP Count", int((rfm['Segment'] == '💎 VIP').sum()))
    c2.metric("Loyal Count", int((rfm['Segment'] == '🔥 Loyal').sum()))
    c3.metric("At Risk", int((rfm['Segment'] == '💤 Dormant').sum()))
    c4.metric("Avg Spend", f"${rfm['Monetary'].mean():.0f}")

    col_chart, col_data = st.columns([2, 1], gap="medium")

    with col_chart:
        fig_rfm = px.scatter(rfm, x='Recency', y='Monetary', color='Segment',
                             hover_data=['customer_name', 'Frequency'],
                             color_discrete_map={'💎 VIP': '#38bdf8', '🔥 Loyal': '#10b981',
                                                 '💤 Dormant': '#94a3b8', '🌱 Regular': '#f43f5e'})
        fig_rfm.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
        st.plotly_chart(fig_rfm, width="stretch")

    with col_data:
        st.dataframe(rfm[rfm['Segment'] == '💎 VIP'].sort_values('Monetary', ascending=False).head(10), hide_index=True)