# Who are the top 5 customers by sales?
import sqlite3
import pandas as pd

conn = sqlite3.connect('sales.db')

print("--- VERIFYING TOP 5 CUSTOMERS ---")
query = """
SELECT 
    customer_name, 
    SUM(sales) as Total_Sales 
FROM orders 
GROUP BY customer_name 
ORDER BY Total_Sales DESC 
LIMIT 5
"""

df = pd.read_sql(query, conn)
print(df)
conn.close()