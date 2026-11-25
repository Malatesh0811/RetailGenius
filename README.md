# ⚡ RetailGenius: Enterprise AI Analytics Suite

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-v1.40-FF4B4B)
![LangChain](https://img.shields.io/badge/AI-LangChain-green)

**RetailGenius** is an autonomous business intelligence platform designed to bridge the gap between raw data and executive decision-making. It replaces static dashboards with an interactive AI agent capable of answering complex ad-hoc queries and forecasting future trends.

## 🚀 Key Features

### 1. 📊 Executive Command Center
* **Real-time KPIs**: Monitor Revenue, Net Profit, and Transaction Volume with dynamic growth deltas.
* **Interactive Visuals**: Full-width charts for Revenue Composition and Regional Profitability.
* **Titanium UI**: A modern, high-contrast "Dark Mode" interface designed for long-session usability.

### 2. 🧠 Autonomous SQL Analyst
* **Natural Language Querying**: Powered by an LLM on **Groq** (default `openai/gpt-oss-120b`, configurable via `GROQ_MODEL`), users can ask questions like *"What were the top 3 selling products in 2012?"* in plain English.
* **Self-Correcting Logic**: The agent intelligently identifies database schemas and corrects its own SQL syntax errors.

### 3. 🔮 Forecast + Honest Evaluation
* **Time-Series Forecasting**: **Prophet** projects daily sales 30-365 days ahead with an 80% uncertainty band.
* **Rolling Backtest**: 3 folds x 6 months, scored on monthly totals against two baselines
  (`python -m retailgenius.forecasting`):

  | Model | Monthly MAPE |
  |---|---|
  | Historical monthly average (baseline) | **12.1%** |
  | Prophet | 14.2% |
  | Same period last year (baseline) | 20.8% |

  Sales in this dataset are nearly flat with weak seasonality, so Prophet does **not** beat a simple
  average - the app says so instead of hiding it.

---

## 🛠️ Tech Stack

* **Frontend**: Streamlit (Custom CSS for "Titanium" Theme)
* **AI/LLM**: LangChain (tool-calling SQL agent), Groq API
* **Database**: SQLite (Production-ready local instance)
* **Visualization**: Plotly Express & Graph Objects
* **Forecasting**: Prophet

---

## 💻 Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Malatesh0811/RetailGenius.git
    cd RetailGenius
    ```

2.  **Install Dependencies** (inside a virtual environment)
    ```bash
    python -m venv venv
    venv\Scripts\activate        # Windows  (macOS/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    ```

3.  **Configure API Key** (never put it in the code)
    * Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
    * Replace the placeholder with your Groq key from https://console.groq.com/keys
    * `secrets.toml` is git-ignored, so the key never reaches GitHub

4.  **Run the Application** (from the project folder, so Streamlit finds `.streamlit/`)
    ```bash
    streamlit run app.py
    ```

5.  *(Optional)* **Rebuild the database** from `Superstore.xls`
    ```bash
    python -m retailgenius.etl
    ```

6.  *(Optional)* **Run the tests**
    ```bash
    pip install -r requirements-dev.txt
    pytest
    ```

---

## 🗂️ Project Structure

```
app.py                  Streamlit UI only (layout, widgets, charts)
retailgenius/
  data.py               load + validate the orders table, filter_orders()
  analytics.py          KPIs, period-over-period change, RFM segmentation
  forecasting.py        Prophet forecast + rolling backtest vs baselines
  agent.py              LangChain SQL agent on a read-only SQLite connection
  etl.py                Superstore.xls -> sales.db
  ui.py                 theme CSS, icons, small HTML helpers
tests/                  pytest suite (runs without an API key)
```

---

## 🔮 Future Roadmap

* **Containerization**: Docker support for cloud-agnostic deployment.
* **RFM Clustering**: Automated customer segmentation using K-Means.
* **Multi-Source ETL**: Connectors for PostgreSQL and Snowflake.