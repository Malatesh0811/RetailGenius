import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect("sales.db")

# 1. Total rows
print("Total rows:")
print(pd.read_sql("SELECT COUNT(*) FROM orders", conn))

# 2. Sales by product category
print("\nSales by Product Category:")
print(pd.read_sql("""
    SELECT product_category, SUM(sales) AS total_sales
    FROM orders
    GROUP BY product_category
""", conn))

# 3. Date range
print("\nOrder date range:")
print(pd.read_sql("""
    SELECT MIN(order_date) AS start_date, MAX(order_date) AS end_date
    FROM orders
""", conn))

conn.close()
