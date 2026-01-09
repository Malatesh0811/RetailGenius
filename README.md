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
* **Natural Language Querying**: Powered by **Llama 3 (via Groq)**, users can ask questions like *"What were the top 3 selling products in 2012?"* in plain English.
* **Self-Correcting Logic**: The agent intelligently identifies database schemas and corrects its own SQL syntax errors.

### 3. 🔮 Predictive Engine
* **Time-Series Forecasting**: Integrated **Facebook Prophet** model to predict sales trends 30-365 days into the future.
* **Seasonality Detection**: Automatically identifies weekly and yearly buying patterns.

---

## 🛠️ Tech Stack

* **Frontend**: Streamlit (Custom CSS for "Titanium" Theme)
* **AI/LLM**: LangChain, Groq API (Llama 3 70B)
* **Database**: SQLite (Production-ready local instance)
* **Visualization**: Plotly Express & Graph Objects
* **Forecasting**: Prophet

---

## 💻 Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/RetailGenius.git](https://github.com/YOUR_USERNAME/RetailGenius.git)
    cd RetailGenius
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Key**
    * Open `app.py`
    * Add your Groq API Key to line 16: `GROQ_API_KEY = "gsk_..."`

4.  **Run the Application**
    ```bash
    streamlit run app.py
    ```

---

## 🔮 Future Roadmap

* **Containerization**: Docker support for cloud-agnostic deployment.
* **RFM Clustering**: Automated customer segmentation using K-Means.
* **Multi-Source ETL**: Connectors for PostgreSQL and Snowflake.