# What is the total sales and total profit for the year 2012?
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('sales.db')

# Write the raw SQL query manually
query = """
SELECT 
    SUM(sales) as Total_Sales,
    SUM(profit) as Total_Profit
FROM orders 
-- order_date is stored as text like '2012-12-31 00:00:00', which is > '2012-12-31',
-- so BETWEEN ... '2012-12-31' would miss the last day. Compare the year instead.
WHERE strftime('%Y', order_date) = '2012'
"""

# Run it
df = pd.read_sql(query, conn)
print("--- GROUND TRUTH (SQL) ---")
print(f"Total Sales 2012:  ${df['Total_Sales'][0]:,.2f}")
print(f"Total Profit 2012: ${df['Total_Profit'][0]:,.2f}")

conn.close()