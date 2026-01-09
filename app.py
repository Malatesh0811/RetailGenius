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
st.set_page_config(page_title="RetailGenius Enterprise", page_icon="🏢", layout="wide")

# ⚠️ PASTE YOUR KEY HERE
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
# --- 2. CUSTOM CSS (TITANIUM LOOK) ---
st.markdown("""
<style>
    /* Import Google Font: Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background: Deep Blue/Black Professional Gradient */
    .stApp {
        background: radial-gradient(circle at top left, #0f172a, #020617);
    }

    /* --- REALISTIC TABS (NO EMOJIS) --- */
    button[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: 600 !important;
        background-color: transparent;
        border: none;
        color: #64748b;
        padding: 15px 30px !important; /* Wider clickable area */
        margin-right: 0px;
        border-bottom: 2px solid transparent;
        transition: color 0.2s ease;
    }
    button[data-baseweb="tab"]:hover {
        color: #94a3b8;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important; /* Neon Blue Text */
        border-bottom: 3px solid #38bdf8 !important; /* Underline */
    }

    /* --- MASSIVE KPI CARDS (HORIZONTAL FIT) --- */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.6) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 30px 20px; /* Bigger padding */
        width: 100%; /* Force full width */
        min-height: 160px; /* Force consistent height */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }
    
    /* Permanent Edge Highlight */
    div[data-testid="stMetric"]::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        border-radius: 12px;
        padding: 1px;
        background: linear-gradient(45deg, transparent, rgba(56, 189, 248, 0.3), transparent);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }

    /* Hover Effect: Lift & Glow */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px -10px rgba(56, 189, 248, 0.15);
        border-color: rgba(56, 189, 248, 0.5);
    }

    /* KPI Typography */
    div[data-testid="stMetric"] label {
        color: #94a3b8;
        font-size: 0.95rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 3.5rem !important; /* HUGE Numbers */
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -1px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        font-weight: 600;
        background: rgba(16, 185, 129, 0.1); /* Green tint background */
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
    }

    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] {
        background-color: #0b1120;
        border-right: 1px solid #1e293b;
    }
    
    /* --- CHART CONTEXT BOX --- */
    .chart-context {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px;
        margin-top: 15px;
        font-size: 13px;
        color: #cbd5e1;
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }
    .icon-box {
        color: #38bdf8;
        font-size: 18px;
        margin-top: 2px;
    }

    /* --- AI CHAT BUBBLE --- */
    .ai-bubble {
        background: #1e293b;
        border-radius: 8px;
        padding: 20px;
        border: 1px solid #334155;
        color: #e2e8f0;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. HELPER: SVG ICONS ---
def render_svg_header(title, icon_path):
    # This renders a realistic SVG icon next to the title
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <div style="background: rgba(56, 189, 248, 0.1); padding: 10px; border-radius: 8px; color: #38bdf8;">
            {icon_path}
        </div>
        <h2 style="margin: 0; font-weight: 700; font-size: 24px; color: white;">{title}</h2>
    </div>
    """, unsafe_allow_html=True)

# SVG Paths (Realistic Icons)
ICON_DASHBOARD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>'
ICON_FORECAST = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h5l3 5 5-11 4 6h3"/><path d="M12 22a10 10 0 0 0 10-10"/></svg>'
ICON_BRAIN = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16v-4"/><path d="M12 8h.01"/><path d="M20.5 12a8.5 8.5 0 1 1-8-8.5 8.5 8.5 0 0 1 8 8.5Z"/><path d="M9 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/></svg>'
ICON_FILTER = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>'

# --- 4. DATA LOADER ---
@st.cache_data
def load_data():
    conn = sqlite3.connect('sales.db')
    query = "SELECT * FROM orders"
    df = pd.read_sql(query, conn)
    conn.close()
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df

try:
    df_raw = load_data()
except Exception:
    st.error("❌ Database not found. Please run 1_etl_pipeline.py first.")
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    # Custom HTML Title (No Emojis)
    st.markdown("""
    <div style="margin-bottom: 30px;">
        <h1 style="font-size: 32px; font-weight: 800; background: -webkit-linear-gradient(0deg, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;">RetailGenius</h1>
        <div style="font-size: 12px; color: #64748b; font-weight: 600; letter-spacing: 1px;">ENTERPRISE ANALYTICS</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""<div style="display:flex; align-items:center; gap:8px; color:#38bdf8; font-weight:600; font-size:14px; margin-bottom: 20px;">
        <span style="width:8px; height:8px; background:#38bdf8; border-radius:50%; box-shadow: 0 0 10px #38bdf8;"></span>
        Live Connection Active
    </div>""", unsafe_allow_html=True)
    
    # Filter Section with Realistic Icon
    st.markdown(f'<div style="display:flex; align-items:center; gap:8px; color:#fff; margin-bottom:10px;">{ICON_FILTER} <span>Filters</span></div>', unsafe_allow_html=True)
    
    with st.container():
        min_date = df_raw['order_date'].min()
        max_date = df_raw['order_date'].max()
        
        date_range = st.date_input("Period", value=(min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
        
        region_col = 'region' if 'region' in df_raw.columns else df_raw.columns[0]
        all_regions = sorted(df_raw[region_col].unique())
        sel_region = st.multiselect("Region", all_regions, default=all_regions)
        
        cat_col = 'product_category' if 'product_category' in df_raw.columns else 'category'
        all_cats = sorted(df_raw[cat_col].unique())
        sel_cat = st.multiselect("Category", all_cats, default=all_cats)

# --- 6. FILTER LOGIC ---
if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (
        (df_raw['order_date'] >= pd.to_datetime(start_date)) & 
        (df_raw['order_date'] <= pd.to_datetime(end_date)) &
        (df_raw['region'].isin(sel_region)) &
        (df_raw[cat_col].isin(sel_cat))
    )
    df = df_raw.loc[mask]
else:
    df = df_raw

if df.empty:
    st.warning("⚠️ No data matches filters.")
    st.stop()

# --- 7. MAIN APP TABS (Text Only, No Emojis) ---
tab1, tab2, tab3 = st.tabs(["Overview", "Forecast", "Analyst"])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab1:
    render_svg_header("Performance Metrics", ICON_DASHBOARD)
    
    # KPIs - USING GAP="LARGE" FOR HORIZONTAL FIT
    sales = df['sales'].sum()
    profit = df['profit'].sum()
    orders = df.shape[0]
    
    # st.columns(3, gap="large") ensures they spread out effectively
    c1, c2, c3 = st.columns(3, gap="large")
    
    c1.metric("Total Revenue", f"${sales/1000000:.2f}M", "Global Sales")
    c2.metric("Net Profit", f"${profit/1000:.1f}K", f"{(profit/sales)*100:.1f}% Margin")
    c3.metric("Transactions", f"{orders:,}", "Total Orders")

    st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True) # Spacer

    col_left, col_right = st.columns(2, gap="medium")
    
    with col_left:
        st.subheader("Revenue Composition")
        # CHART 1: PIE CHART
        fig_pie = px.pie(df, names=cat_col, values='sales', hole=0.7, 
                         color_discrete_sequence=px.colors.sequential.Teal_r)
        fig_pie.update_traces(textposition='outside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("""
        <div class="chart-context">
            <div class="icon-box">ℹ️</div>
            <div>
                <strong>Revenue Distribution:</strong><br>
                Shows the percentage contribution of each category to total sales. 
                Use this to balance your portfolio risk.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.subheader("Regional Profitability")
        # CHART 2: BAR CHART
        state_col = 'state' if 'state' in df.columns else 'province' if 'province' in df.columns else 'region'
        state_data = df.groupby(state_col)['profit'].sum().reset_index().sort_values('profit').tail(8)
        
        fig_bar = px.bar(state_data, x='profit', y=state_col, orientation='h', 
                         color='profit', color_continuous_scale='Teal')
        fig_bar.update_layout(xaxis_title="Net Profit ($)", yaxis_title=None,
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(color='#94a3b8'))
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("""
        <div class="chart-context">
            <div class="icon-box">ℹ️</div>
            <div>
                <strong>Profit Leaders:</strong><br>
                Ranks your top regions by Net Profit. Focus resources on the longest bars (highest efficiency markets).
            </div>
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
        st.caption("Algorithm: Facebook Prophet")

    with c_viz:
        if run_btn:
            with st.spinner("Calculating future trends..."):
                prophet_df = df.groupby('order_date')['sales'].sum().reset_index()
                prophet_df.columns = ['ds', 'y']
                
                m = Prophet()
                m.fit(prophet_df)
                future = m.make_future_dataframe(periods=days_pred)
                forecast = m.predict(future)
                
                # CHART 3: FORECAST
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=prophet_df['ds'], y=prophet_df['y'], name='Historical',
                                         mode='markers', marker=dict(color='#2dd4bf', size=3, opacity=0.5)))
                fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], name='Projection',
                                         mode='lines', line=dict(color='#38bdf8', width=2)))
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#94a3b8'),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(gridcolor='#1e293b')
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("""
                <div class="chart-context">
                    <div class="icon-box">📈</div>
                    <div>
                        <strong>Trend Analysis:</strong><br>
                        The <span style="color:#38bdf8">Blue Line</span> indicates the predicted sales trajectory.
                        Use this to plan inventory for the coming months.
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 3: AI ANALYST
# ==========================================
with tab3:
    render_svg_header("Intelligent Query Engine", ICON_BRAIN)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(f'<div class="ai-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

    user_query = st.chat_input("Query the database (e.g. 'Best selling products in 2012')...")

    if user_query:
        if "PASTE_YOUR" in GROQ_API_KEY:
            st.error("🚨 Configuration Error: Please add API Key in app.py")
        else:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user", avatar="👤"):
                st.write(user_query)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Processing Logic..."):
                    try:
                        db = SQLDatabase.from_uri("sqlite:///sales.db")
                        llm = ChatGroq(temperature=0, groq_api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")
                        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
                        agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=False, handle_parsing_errors=True)
                        
                        response = agent.run(user_query)
                        
                        st.markdown(f'<div class="ai-bubble">{response}</div>', unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                    except Exception as e:
                        st.error(f"Error: {e}")