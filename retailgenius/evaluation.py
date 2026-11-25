"""Evaluate the SQL agent on questions whose correct answers come from hand-written SQL.

Run:  python -m retailgenius.evaluation            (needs GROQ_API_KEY in .streamlit/secrets.toml or env)
      python -m retailgenius.evaluation --only 3   (first 3 questions, for a quick check)

Grading is plain code, not an LLM judge: the agent's free-text answer must contain the
expected number (within a small tolerance) or the expected name(s). This keeps the score
reproducible and explainable.
"""
import argparse
import json
import os
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime

from retailgenius.data import DB_PATH, PROJECT_ROOT

RESULTS_DIR = PROJECT_ROOT / "evals"


@dataclass
class EvalCase:
    question: str
    sql: str                 # ground truth, run directly on the database
    kind: str                # "number" | "text" | "list" | "month"
    tolerance: float = 0.01  # relative tolerance for numbers (1%); 0 = exact (used for counts)
    percent: bool = False    # also accept the value written as a fraction (10.2% <-> 0.102)
    trap: str = ""           # what makes this question tricky


EVAL_SET = [
    # --- simple aggregates ---
    EvalCase("What is the total sales amount across all orders?",
             "SELECT SUM(sales) FROM orders", "number"),
    EvalCase("What was the total profit in 2011?",
             "SELECT SUM(profit) FROM orders WHERE strftime('%Y', order_date) = '2011'", "number",
             trap="dates are stored as text"),
    EvalCase("How many orders are there in total?",
             "SELECT COUNT(DISTINCT order_id) FROM orders", "number", tolerance=0,
             trap="one order has several rows: COUNT(*) gives 8,399, the right answer is distinct orders"),
    EvalCase("How many different customers are there?",
             "SELECT COUNT(DISTINCT customer_name) FROM orders", "number", tolerance=0),
    EvalCase("How many orders were placed in December 2012?",
             "SELECT COUNT(DISTINCT order_id) FROM orders WHERE strftime('%Y-%m', order_date) = '2012-12'",
             "number", tolerance=0, trap="distinct orders + month filter on text dates"),
    EvalCase("What were the total sales in the West region in 2010?",
             "SELECT SUM(sales) FROM orders WHERE region = 'West' AND strftime('%Y', order_date) = '2010'",
             "number", trap="two filters"),
    EvalCase("How many order lines have a negative profit?",
             "SELECT COUNT(*) FROM orders WHERE profit < 0", "number", tolerance=0,
             trap="here rows ARE the right unit"),
    # --- ranking / group by ---
    EvalCase("Which product category has the highest total sales?",
             "SELECT product_category FROM orders GROUP BY 1 ORDER BY SUM(sales) DESC LIMIT 1", "text"),
    EvalCase("Which region generated the most profit?",
             "SELECT region FROM orders GROUP BY 1 ORDER BY SUM(profit) DESC LIMIT 1", "text"),
    EvalCase("Which province has the lowest total profit?",
             "SELECT province FROM orders GROUP BY 1 ORDER BY SUM(profit) ASC LIMIT 1", "text",
             trap="ascending order"),
    EvalCase("Who are the top 3 customers by total sales?",
             "SELECT customer_name FROM orders GROUP BY 1 ORDER BY SUM(sales) DESC LIMIT 3", "list"),
    EvalCase("Which customer segment brought in the most profit?",
             "SELECT customer_segment FROM orders GROUP BY 1 ORDER BY SUM(profit) DESC LIMIT 1", "text"),
    EvalCase("Which product sub-category had the highest sales in 2012?",
             "SELECT product_sub_category FROM orders WHERE strftime('%Y', order_date) = '2012' "
             "GROUP BY 1 ORDER BY SUM(sales) DESC LIMIT 1", "text"),
    # v1 asked "Which month had the highest total sales?" - ambiguous: the agent reasonably summed
    # December over all years. Reworded to ask for one specific month (see docs/PHASE-5-NOTES.md).
    EvalCase("Which single month (year and month, e.g. March 2010) had the highest total sales?",
             "SELECT strftime('%Y-%m', order_date) FROM orders GROUP BY 1 ORDER BY SUM(sales) DESC LIMIT 1",
             "month", trap="must group by year AND month"),
    # --- ratios and derived metrics ---
    EvalCase("What is the overall profit margin (total profit divided by total sales) as a percentage?",
             "SELECT SUM(profit) * 100.0 / SUM(sales) FROM orders", "number", percent=True,
             trap="ratio of sums, not average of row margins"),
    EvalCase("What percentage of total sales comes from the Technology category?",
             "SELECT SUM(CASE WHEN product_category = 'Technology' THEN sales END) * 100.0 / SUM(sales) "
             "FROM orders", "number", percent=True),
    EvalCase("What is the average order value (total sales divided by number of orders)?",
             "SELECT SUM(sales) / COUNT(DISTINCT order_id) FROM orders", "number",
             trap="AVG(sales) gives the average ROW value, not order value"),
    EvalCase("By what percentage did total sales change in 2012 compared to 2011?",
             "SELECT (SUM(CASE WHEN strftime('%Y', order_date) = '2012' THEN sales END) / "
             "SUM(CASE WHEN strftime('%Y', order_date) = '2011' THEN sales END) - 1) * 100 FROM orders",
             "number", percent=True, trap="year-over-year growth"),
    EvalCase("On average, how many days does it take to ship an order after it is placed?",
             "SELECT AVG(julianday(ship_date) - julianday(order_date)) FROM orders", "number",
             trap="date arithmetic on text dates"),
    EvalCase("How many customers have placed more than 10 orders?",
             "SELECT COUNT(*) FROM (SELECT customer_name FROM orders GROUP BY 1 "
             "HAVING COUNT(DISTINCT order_id) > 10)", "number", tolerance=0,
             trap="counting rows instead of orders gives 335 instead of 123"),
]


# --- Ground truth ---------------------------------------------------------------------
def ground_truth(case, db_path=DB_PATH):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(case.sql).fetchall()
    if case.kind == "list":
        return [r[0] for r in rows]
    return rows[0][0]


# --- Grading (pure functions, unit-tested) -----------------------------------------------
_NUMBER = re.compile(r"(-?\d[\d,]*\.?\d*)\s*(million|thousand|billion|[mkb]\b)?", re.IGNORECASE)
_SCALE = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "billion": 1e9, "b": 1e9}


def extract_numbers(text):
    """All numbers in a text, with '1,234.5', '$3.7 million' and '12K' understood."""
    numbers = []
    for raw, unit in _NUMBER.findall(text.replace("−", "-")):  # unicode minus -> '-'
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        numbers.append(value * _SCALE.get(unit.lower(), 1) if unit else value)
    return numbers


def number_matches(answer, expected, tolerance=0.01, percent=False):
    targets = [expected] + ([expected / 100] if percent else [])
    for value in extract_numbers(answer):
        for target in targets:
            if tolerance == 0:
                if round(value) == round(target):
                    return True
            elif abs(value - target) <= tolerance * abs(target):
                return True
    return False


def _normalise(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def month_names(year_month):
    """'2009-01' -> accepted spellings: 2009-01, January 2009, Jan 2009, 01/2009."""
    dt = datetime.strptime(year_month, "%Y-%m")
    return [year_month, dt.strftime("%B %Y"), dt.strftime("%b %Y"), dt.strftime("%m/%Y")]


def grade(case, answer, expected):
    answer_n = _normalise(answer)
    if case.kind == "number":
        return number_matches(answer, float(expected), case.tolerance, case.percent)
    if case.kind == "text":
        return _normalise(str(expected)) in answer_n
    if case.kind == "list":
        return all(_normalise(str(item)) in answer_n for item in expected)
    if case.kind == "month":
        return any(_normalise(name) in answer_n for name in month_names(expected))
    raise ValueError(f"unknown kind {case.kind!r}")


# --- Runner -------------------------------------------------------------------------
@dataclass
class EvalResult:
    question: str
    expected: object
    answer: str
    passed: bool
    seconds: float
    sql: list = field(default_factory=list)
    error: str = ""
    trap: str = ""


def _is_rate_limit(error):
    return "rate" in str(error).lower() and ("limit" in str(error).lower() or "429" in str(error))


def run_eval(agent, cases=EVAL_SET, pause=2.0, retries=3, ask_fn=None):
    """Ask every question, grade it, return a list of EvalResult. Waits and retries on rate limits."""
    from retailgenius.agent import ask_with_sql
    ask_fn = ask_fn or ask_with_sql

    results = []
    for i, case in enumerate(cases, 1):
        expected = ground_truth(case)
        answer, sql, error = "", [], ""
        start = time.perf_counter()
        for attempt in range(retries + 1):
            try:
                answer, sql = ask_fn(agent, case.question)
                error = ""
                break
            except Exception as e:  # keep going: one failed question must not stop the whole run
                error = f"{type(e).__name__}: {e}"
                if _is_rate_limit(e) and attempt < retries:
                    wait = 20 * (attempt + 1)
                    print(f"   rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    break
        seconds = time.perf_counter() - start
        passed = not error and grade(case, answer, expected)
        results.append(EvalResult(case.question, expected, answer, passed, round(seconds, 1), sql, error, case.trap))
        print(f"[{i:2}/{len(cases)}] {'PASS' if passed else 'FAIL'}  {case.question}")
        time.sleep(pause)
    return results


def _fmt_expected(value):
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, list):
        return ", ".join(map(str, value))
    return str(value)


def write_report(results, model, out_dir=RESULTS_DIR):
    out_dir.mkdir(exist_ok=True)
    passed = sum(r.passed for r in results)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    avg_time = sum(r.seconds for r in results) / len(results)

    lines = [
        "# SQL Agent Evaluation",
        "",
        f"**Score: {passed}/{len(results)} ({passed / len(results):.0%})** - model `{model}` - run {stamp} "
        f"- avg {avg_time:.1f}s per question",
        "",
        "Correct answers come from hand-written SQL on `sales.db`; grading is deterministic "
        "(number within tolerance / name present), no LLM judge. Regenerate with "
        "`python -m retailgenius.evaluation`.",
        "",
        "| # | Result | Question | Expected | Trap |",
        "|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"| {i} | {'✅' if r.passed else '❌'} | {r.question} | {_fmt_expected(r.expected)} | {r.trap} |")

    failures = [(i, r) for i, r in enumerate(results, 1) if not r.passed]
    if failures:
        lines += ["", "## Failures", ""]
        for i, r in failures:
            lines += [f"### {i}. {r.question}", f"- **Expected:** {_fmt_expected(r.expected)}"]
            lines += [f"- **Error:** `{r.error}`"] if r.error else []
            lines += ["- **Agent answered:**", "", "> " + r.answer.replace("\n", "\n> "), ""]
            for q in r.sql:
                lines += ["```sql", q.strip(), "```"]
            lines.append("")

    (out_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "results.json").write_text(
        json.dumps({"model": model, "run": stamp, "passed": passed, "total": len(results),
                    "results": [asdict(r) for r in results]}, indent=2, default=str), encoding="utf-8")
    return passed


def _api_key():
    key = os.environ.get("GROQ_API_KEY")
    secrets = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if not key and secrets.exists():
        match = re.search(r'^\s*GROQ_API_KEY\s*=\s*"([^"]+)"', secrets.read_text(encoding="utf-8"), re.M)
        key = match and match.group(1)
    return key


if __name__ == "__main__":
    from retailgenius.agent import DEFAULT_MODEL, build_sql_agent

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=os.environ.get("GROQ_MODEL", DEFAULT_MODEL))
    parser.add_argument("--only", type=int, help="run only the first N questions")
    args = parser.parse_args()

    key = _api_key()
    if not key:
        raise SystemExit("No GROQ_API_KEY found (env var or .streamlit/secrets.toml).")
    cases = EVAL_SET[:args.only] if args.only else EVAL_SET
    results = run_eval(build_sql_agent(key, args.model), cases)
    score = write_report(results, args.model)
    print(f"\nScore: {score}/{len(results)}  ->  {RESULTS_DIR / 'results.md'}")
