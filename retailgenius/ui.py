"""Look and feel: CSS theme, SVG icons and small HTML helpers.

Only our own static markup goes through unsafe_allow_html here - never model or database text.
"""
import streamlit as st

CSS = """
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
"""

ICON_DASHBOARD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>'
ICON_FORECAST = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h5l3 5 5-11 4 6h3"/><path d="M12 22a10 10 0 0 0 10-10"/></svg>'
ICON_BRAIN = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16v-4"/><path d="M12 8h.01"/><path d="M20.5 12a8.5 8.5 0 1 1-8-8.5 8.5 8.5 0 0 1 8 8.5Z"/><path d="M9 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/></svg>'
ICON_FILTER = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>'
ICON_PEOPLE = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>'

SIDEBAR_BRAND = """
<div style="margin-bottom: 30px;">
    <h1 style="font-size: 32px; font-weight: 800; background: -webkit-linear-gradient(0deg, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;">RetailGenius</h1>
    <div style="font-size: 12px; color: #64748b; font-weight: 600; letter-spacing: 1px;">RETAIL ANALYTICS</div>
</div>
"""


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def header(title, icon):
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <div style="background: rgba(56, 189, 248, 0.1); padding: 10px; border-radius: 8px; color: #38bdf8;">
            {icon}
        </div>
        <h2 style="margin: 0; font-weight: 700; font-size: 24px; color: white;">{title}</h2>
    </div>
    """, unsafe_allow_html=True)


def context_box(title, body_html, margin_bottom=0):
    """Explanation box under a chart. `body_html` must be our own static text."""
    st.markdown(f'<div class="chart-context" style="margin-bottom:{margin_bottom}px;">'
                f'<strong>{title}</strong><br>{body_html}</div>', unsafe_allow_html=True)


def transparent(fig, **layout):
    """Dark-theme friendly Plotly layout."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#94a3b8"), **layout)
    return fig
