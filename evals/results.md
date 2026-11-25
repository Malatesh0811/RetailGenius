# SQL Agent Evaluation

**Score: 20/20 (100%)** - model `openai/gpt-oss-120b` - run 2026-11-25 19:33 - avg 27.2s per question

Correct answers come from hand-written SQL on `sales.db`; grading is deterministic (number within tolerance / name present), no LLM judge. Regenerate with `python -m retailgenius.evaluation`.

| # | Result | Question | Expected | Trap |
|---|---|---|---|---|
| 1 | ✅ | What is the total sales amount across all orders? | 14,915,600.82 |  |
| 2 | ✅ | What was the total profit in 2011? | 381,455.99 | dates are stored as text |
| 3 | ✅ | How many orders are there in total? | 5496 | one order has several rows: COUNT(*) gives 8,399, the right answer is distinct orders |
| 4 | ✅ | How many different customers are there? | 795 |  |
| 5 | ✅ | How many orders were placed in December 2012? | 96 | distinct orders + month filter on text dates |
| 6 | ✅ | What were the total sales in the West region in 2010? | 851,790.43 | two filters |
| 7 | ✅ | How many order lines have a negative profit? | 4264 | here rows ARE the right unit |
| 8 | ✅ | Which product category has the highest total sales? | Technology |  |
| 9 | ✅ | Which region generated the most profit? | Ontario |  |
| 10 | ✅ | Which province has the lowest total profit? | Nunavut | ascending order |
| 11 | ✅ | Who are the top 3 customers by total sales? | Emily Phan, Deborah Brumfield, Roy Skaria |  |
| 12 | ✅ | Which customer segment brought in the most profit? | Corporate |  |
| 13 | ✅ | Which product sub-category had the highest sales in 2012? | Office Machines |  |
| 14 | ✅ | Which single month (year and month, e.g. March 2010) had the highest total sales? | 2009-01 | must group by year AND month |
| 15 | ✅ | What is the overall profit margin (total profit divided by total sales) as a percentage? | 10.20 | ratio of sums, not average of row margins |
| 16 | ✅ | What percentage of total sales comes from the Technology category? | 40.12 |  |
| 17 | ✅ | What is the average order value (total sales divided by number of orders)? | 2,713.90 | AVG(sales) gives the average ROW value, not order value |
| 18 | ✅ | By what percentage did total sales change in 2012 compared to 2011? | 8.24 | year-over-year growth |
| 19 | ✅ | On average, how many days does it take to ship an order after it is placed? | 2.03 | date arithmetic on text dates |
| 20 | ✅ | How many customers have placed more than 10 orders? | 123 | counting rows instead of orders gives 335 instead of 123 |
