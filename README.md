# 📊 RetailGenius: AI-Powered Supply Chain Analytics

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)
![AI](https://img.shields.io/badge/AI-Llama3%20%2F%20Groq-purple)
![Status](https://img.shields.io/badge/Status-Live-success)

### 🚀 **Project Overview**
**RetailGenius** is an end-to-end analytics suite designed to bridge the gap between raw data and business decision-making. 

It solves two critical business problems:
1.  **The "Ad-Hoc Query" Bottleneck:** Non-technical managers often wait days for analysts to answer simple questions like *"What was the sales trend in 2023?"*. RetailGenius solves this with a **Text-to-SQL AI Agent**.
2.  **Inventory Planning:** It uses **Machine Learning (Facebook Prophet)** to forecast demand 90 days into the future, helping supply chain teams avoid stockouts.

### 🎥 **Demo**
*(Add a screenshot of your dashboard here later)*

### 🏗️ **Architecture**
The application follows a modern **Lakehouse-style** architecture:

1.  **ETL Layer:** Python scripts (`pandas`) clean raw Excel data, normalize schema, and load it into a SQL database.
2.  **Predictive Layer:** **Facebook Prophet** (Time-Series ML) trains on historical data to predict future sales trends.
3.  **Prescriptive Layer:** **LangChain** + **Llama 3 (via Groq)** acts as an autonomous agent that translates Natural Language into SQL queries.
4.  **UI Layer:** A generic **Streamlit** interface for accessibility.

### 🛠️ **Tech Stack**
* **Language:** Python
* **Database:** SQLite (Scalable to PostgreSQL)
* **LLM Engine:** Llama 3 (70B) via Groq API
* **Orchestration:** LangChain
* **Visualization:** Plotly & Streamlit

### ⚡ **Key Features**
* **📈 Smart Dashboard:** Real-time KPIs (Sales, Profit, Orders) and category-wise breakdown.
* **🔮 ML Forecasting:** 90-day rolling sales prediction with confidence intervals.
* **🤖 AI Analyst:**
    * *User:* "Who are the top 5 customers by profit in 2012?"
    * *AI:* Generates SQL `SELECT ... ORDER BY profit DESC LIMIT 5`, runs it, and explains the result.

### 💻 **How to Run Locally**

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/yourusername/retail-genius.git](https://github.com/yourusername/retail-genius.git)
    cd retail-genius
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the ETL Pipeline** (Loads the data)
    ```bash
    python 1_etl_pipeline.py
    ```

4.  **Launch the App**
    ```bash
    streamlit run app.py
    ```

---
*Built by [Your Name] as a showcase of Modern Data Stack engineering.*