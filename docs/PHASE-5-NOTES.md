# Phase 5 — Evaluating the SQL Agent

## Why this phase
"I built an LLM agent" is common. "I measured how often it's right, found
why it was wrong, fixed it, and measured again" is rare, and it's what
interviewers for AI roles look for. LLMs sound confident even when wrong, so
the only way to trust the agent is to test it against known answers.

## Design

### 1. Questions with answers from hand-written SQL
`retailgenius/evaluation.py` holds `EVAL_SET`: 20 `EvalCase`s. Each has a question,
the SQL that computes the correct answer, an answer `kind` and the **trap** it tests:

| Group | Examples | Traps |
|---|---|---|
| Simple aggregates (7) | total sales, profit in 2011, orders in Dec 2012 | dates stored as text; **orders vs rows** |
| Ranking / group-by (7) | top category, lowest-profit province, top 3 customers, best month | ascending vs descending; group by year AND month |
| Ratios / derived (6) | profit margin %, Technology share %, average order value, YoY growth, avg shipping days, customers with 10+ orders | ratio of sums vs average of ratios; AVG(sales) = average **row**, not order; date arithmetic |

The correct answer is computed **live** from `sales.db` (`ground_truth()`), so it
stays right if the ETL is re-run.

### 2. Grading is code, not an LLM judge
| kind | Passes when... |
|---|---|
| `number` | some number in the answer is within 1% of the truth (`1,234.5`, `$3.7 million`, `12K` all parsed). Counts use `tolerance=0` (exact). `percent=True` also accepts `0.102` for `10.2%`. |
| `text` | the expected name appears in the answer (case and whitespace ignored) |
| `list` | **all** expected names appear |
| `month` | `2009-01`, `January 2009`, `Jan 2009` or `01/2009` appears |

Why not ask another LLM "is this correct?": it costs more, the result can change
from run to run, and it can be fooled by confident wording. Plain code is
reproducible and easy to explain.

### 3. Runner and report
- `python -m retailgenius.evaluation` (`--only N` for a quick check, `--model X` to compare models).
- The agent now returns the **SQL it ran** (`return_intermediate_steps`); failures in
  the report show it, so you can see *why* an answer was wrong.
- One failing question never stops the run; Groq rate limits are retried with a growing wait.
- Writes `evals/results.md` (readable) and `evals/results.json` (data; the app reads the score from it).

## Results

### v1 — default LangChain SQL prompt: **18/20**
(saved as `evals/results-v1-baseline.md`)

| # | What happened | Verdict |
|---|---|---|
| 20 "How many customers have placed more than 10 orders?" | `HAVING COUNT(*) > 10` → **335**; correct is **123** | **Real agent error**: counted product rows as orders, the exact trap |
| 14 "Which month had the highest total sales?" | Grouped by calendar month across all years → "December" | **Test defect**: the question was ambiguous; the agent's reading is valid |

### The fix: tell the agent what the column names don't
`agent.py` adds `DATA_NOTES` to LangChain's default SQL prompt:
- each row is an order **line**; count orders with `COUNT(DISTINCT order_id)`
- dates are stored as text → use `strftime()` / `julianday()`
- customers are identified by `customer_name`

These are **general facts about the table**, the kind a new analyst would be told
on day one, not answers to specific test questions. Question 14 was reworded to
"Which single month (year and month, e.g. March 2010)...", openly noted in the code.

### v2 — with data notes: **20/20**
Checked that passes happened for the right reasons by reading the SQL:
- #20 now uses `HAVING COUNT(DISTINCT order_id) > 10` → 123
- #14 groups by year and month → January 2009
- #17 uses `SUM(sales) / COUNT(DISTINCT order_id)` → $2,713.90

Average time is about 25-27 s per question (gpt-oss-120b reasons before answering, and the
agent makes several calls: list tables, read schema, check the query, run it).

### Honest limits
- 20 questions is small. 20/20 means "no known failures", not "always right". Use it
  as a **regression check**: re-run after changing the model or prompt.
- LLM output can vary between runs even at temperature 0.
- One question was reworded after seeing results. That's legitimate because it was
  ambiguous, but it is disclosed, and v1 is kept for comparison.

## App changes
- Analyst tab: a **"Show SQL"** expander under every answer.
- Caption with the latest benchmark score (read from `evals/results.json`).
- Caption warning that **sidebar filters don't apply to the agent** (it queries the full DB).

## Tests (13 new → 45 total, all offline)
- Number parsing: `$14,915,600.82`, `3.72 million`, `$12K`, `10.2%`; "2 months" is **not** read as 2 million.
- Tolerance: `$14.92 million` passes, `8,399 orders` fails for 5,496 (the trap).
- Percent/fraction, text, list (all names required), month formats.
- All 20 ground-truth queries run; spot checks (5,496 orders; 123 customers).
- Runner with a **fake agent**: produces 1/2 and the report shows the bad SQL.
- Runner survives an exception from the agent.

## Interview talking points
- "I built a 20-question benchmark with answers computed by hand-written SQL and a
  deterministic grader. Baseline was 18/20; the real failure was counting line items as
  orders. I added schema notes to the system prompt and it went to 20/20. I verified the
  passes by reading the generated SQL."
- "I avoided LLM-as-judge because deterministic grading is reproducible and cheap."
- "When a test failed I first checked whether the *test* was wrong. One question was
  ambiguous, so I fixed the question and disclosed it."
