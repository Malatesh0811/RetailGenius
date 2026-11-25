import os
import streamlit as st
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

    /* AI Bubble */
    .ai-bubble {
        background: #1e293b; border-radius: 16px; padding: 20px;
        border: 1px solid #334155; border-left: 4px solid #818cf8;
        color: #e2e8f0;
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

# --- 4. DATA LOADER (SMART AUTO-FIX) ---
@st.cache_data
def load_data():
    try:
        conn = sqlite3.connect('sales.db')
        query = "SELECT * FROM orders"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # 1. Standardize column names (lowercase, no spaces)
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # 2. Fix Date Column
        date_col = 'order_date' if 'order_date' in df.columns else 'date'
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
        
        # 3. CRITICAL: Find or Rename Customer ID
        if 'customer_id' not in df.columns:
            found_proxy = False
            possible_ids = ['customer_name', 'customer', 'client_name', 'client', 'contact_name', 'customer_segment']
            
            for candidate in possible_ids:
                if candidate in df.columns:
                    df.rename(columns={candidate: 'customer_id'}, inplace=True)
                    found_proxy = True
                    break
            
            if not found_proxy:
                id_col = 'order_id' if 'order_id' in df.columns else df.columns[0]
                df['customer_id'] = df[id_col]

        return df
    except Exception as e:
        return None

# LOAD THE DATA
df_raw = load_data()

if df_raw is None:
    st.error("❌ Database Error. Please ensure 'sales.db' exists and has an 'orders' table.")
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
    
    with st.container():
        if 'order_date' in df_raw.columns:
            min_date = df_raw['order_date'].min()
            max_date = df_raw['order_date'].max()
            date_range = st.date_input("Period", value=(min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
        else:
            date_range = []

        region_col = 'region' if 'region' in df_raw.columns else df_raw.columns[0]
        all_regions = sorted(df_raw[region_col].unique())
        sel_region = st.multiselect("Region", all_regions, default=all_regions)
        
        cat_col = 'product_category' if 'product_category' in df_raw.columns else 'category'
        if cat_col in df_raw.columns:
            all_cats = sorted(df_raw[cat_col].unique())
            sel_cat = st.multiselect("Category", all_cats, default=all_cats)
        else:
            sel_cat = []

# --- 6. FILTER LOGIC ---
if len(date_range) == 2 and 'order_date' in df_raw.columns:
    start_date, end_date = date_range
    mask = (
        (df_raw['order_date'] >= pd.to_datetime(start_date)) & 
        (df_raw['order_date'] <= pd.to_datetime(end_date)) &
        (df_raw[region_col].isin(sel_region))
    )
    if cat_col in df_raw.columns:
        mask = mask & (df_raw[cat_col].isin(sel_cat))
        
    df = df_raw.loc[mask]
else:
    df = df_raw

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
    
    sales = df['sales'].sum() if 'sales' in df.columns else 0
    profit = df['profit'].sum() if 'profit' in df.columns else 0
    orders = df.shape[0]
    
    # HUGE CARDS + HORIZONTAL FILL
    c1, c2, c3 = st.columns(3, gap="large")
    c1.metric("Total Revenue", f"${sales/1000000:.2f}M", "Global Sales")
    c2.metric("Net Profit", f"${profit/1000:.1f}K", f"{(profit/sales)*100:.1f}% Margin" if sales > 0 else "0%")
    c3.metric("Transactions", f"{orders:,}", "Total Orders")

    st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2, gap="medium")
    
    with col_left:
        st.subheader("Revenue Composition")
        if cat_col in df.columns:
            fig_pie = px.pie(df, names=cat_col, values='sales', hole=0.7, 
                             color_discrete_sequence=px.colors.sequential.Teal_r)
            fig_pie.update_traces(textposition='outside', textinfo='percent+label')
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0),
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("""
            <div class="chart-context">
                <strong>💡 Revenue Mix:</strong><br>
                Breakdown of total sales by category. Larger slices indicate your core revenue drivers.
                Use this to identify which product lines are your "Cash Cows."
            </div>
            """, unsafe_allow_html=True)
    
    with col_right:
        st.subheader("Regional Profitability")
        state_col = 'state' if 'state' in df.columns else 'province' if 'province' in df.columns else 'region'
        if state_col in df.columns:
            state_data = df.groupby(state_col)['profit'].sum().reset_index().sort_values('profit').tail(8)
            fig_bar = px.bar(state_data, x='profit', y=state_col, orientation='h', 
                             color='profit', color_continuous_scale='Teal')
            fig_bar.update_layout(xaxis_title="Net Profit ($)", yaxis_title=None,
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font=dict(color='#94a3b8'))
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown("""
            <div class="chart-context">
                <strong>💡 Profit Hotspots:</strong><br>
                Ranking of locations by Net Profit (not just Sales). 
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
        run_btn = st.button("Run Simulation", type="primary", use_container_width=True)

    with c_viz:
        if run_btn and 'order_date' in df.columns:
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
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("""
                <div class="chart-context">
                    <strong>💡 AI Prediction:</strong><br>
                    The <span style="color:#38bdf8">Blue Line</span> represents the AI's forecast for the next 90 days.
                    Upward trends suggest growth; look for recurring patterns (seasonality).
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 3: AI ANALYST
# ==========================================
with tab3:
    render_svg_header("Intelligent Query Engine", ICON_BRAIN)
    if "messages" not in st.session_state: st.session_state.messages = []

    for msg in st.session_state.messages:
        role_class = "user" if msg["role"] == "user" else "ai-bubble"
        if msg["role"] == "user":
            with st.chat_message("user"): st.write(msg["content"])
        else:
            with st.chat_message("assistant"): st.markdown(f'<div class="ai-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

    user_query = st.chat_input("Query the database...")

    if user_query:
        if not GROQ_API_KEY:
            st.error("🚨 No Groq API key found. Add GROQ_API_KEY to .streamlit/secrets.toml "
                     "(see .streamlit/secrets.toml.example) or set it as an environment variable.")
        else:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"): st.write(user_query)
            
            with st.chat_message("assistant"):
                with st.spinner("Processing Logic..."):
                    try:
                        db = SQLDatabase.from_uri("sqlite:///sales.db")
                        llm = ChatGroq(temperature=0, groq_api_key=GROQ_API_KEY, model_name=GROQ_MODEL)
                        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
                        agent = create_sql_agent(llm=llm, toolkit=toolkit, agent_type="tool-calling", verbose=False)
                        response = agent.run(user_query)
                        st.markdown(f'<div class="ai-bubble">{response}</div>', unsafe_allow_html=True)
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
    
    try:
        snapshot_date = df['order_date'].max() + timedelta(days=1)
        
        # Safe aggregation
        rfm = df.groupby('customer_id').agg({
            'order_date': lambda x: (snapshot_date - x.max()).days,
            'sales': 'sum',
            'customer_id': 'count'
        })
        
        rfm.rename(columns={'order_date': 'Recency', 'sales': 'Monetary', 'customer_id': 'Frequency'}, inplace=True)
        rfm.reset_index(inplace=True)
        
        def segment_customer(row):
            if row['Monetary'] > rfm['Monetary'].quantile(0.95): return '💎 VIP'
            elif row['Recency'] > 365: return '💤 Dormant'
            elif row['Frequency'] >= 5: return '🔥 Loyal'
            else: return '🌱 Regular'
                
        rfm['Segment'] = rfm.apply(segment_customer, axis=1)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("VIP Count", rfm[rfm['Segment'] == '💎 VIP'].shape[0])
        c2.metric("Loyal Count", rfm[rfm['Segment'] == '🔥 Loyal'].shape[0])
        c3.metric("At Risk", rfm[rfm['Segment'] == '💤 Dormant'].shape[0])
        c4.metric("Avg Spend", f"${rfm['Monetary'].mean():.0f}")
        
        col_chart, col_data = st.columns([2, 1], gap="medium")
        
        with col_chart:
            fig_rfm = px.scatter(rfm, x='Recency', y='Monetary', color='Segment',
                                 color_discrete_map={'💎 VIP': '#38bdf8', '🔥 Loyal': '#10b981', 
                                                     '💤 Dormant': '#94a3b8', '🌱 Regular': '#f43f5e'})
            fig_rfm.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
            st.plotly_chart(fig_rfm, use_container_width=True)
            
        with col_data:
            st.dataframe(rfm[rfm['Segment'] == '💎 VIP'].sort_values('Monetary', ascending=False).head(10), hide_index=True)

    except Exception as e:
        st.error(f"RFM Error: {e}")