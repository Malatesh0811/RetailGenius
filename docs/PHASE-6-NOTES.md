# Phase 6: README, Screenshots, CI and Deployment

## Why this phase
A recruiter spends about 30 seconds on a repo. They see the README, the screenshots and the green CI badge,
and maybe click a live demo. Phases 1-5 made the project correct; this phase makes that visible.

## What changed

| Area | Change |
|---|---|
| **README** | Rewritten. Leads with a summary table (feature → how it's checked), real screenshots, the agent benchmark (18 → 20/20), the forecast backtest table, the safety design, a "Limitations" section, and how to run things. Removed claims that weren't true or didn't mean anything: "Titanium UI", "Production-ready SQLite", "Self-correcting logic", "Enterprise". |
| **Screenshots** | `docs/screenshots/1-4`, taken from the real running app with Playwright driving Edge headlessly. The answer in the Analyst screenshot was checked against SQL. |
| **CI** | `.github/workflows/tests.yml` runs `pytest` on Python 3.12 for every push and pull request. No API key is needed because the tests never call the LLM. |
| **Deployment guide** | `docs/DEPLOYMENT.md`: step-by-step Streamlit Community Cloud setup, the secrets to paste, checks to do after deploying, and how to handle a shared key, app sleeping and model retirement. |
| **Old scripts removed** | `sanity_check.py`, `verify_answer.py`, `verify_customers.py`. They're replaced by the test suite and the 20-question benchmark, and they're still in git history. |

## Fixes found by looking at the screenshots
Taking real screenshots worked as a visual test and found things the unit tests couldn't:

| Problem seen | Fix |
|---|---|
| Net Profit card showed **"$1521.8K"** | `money()` picks the unit: $1.52M / $381.5K / $950 |
| Full date range compared against **2005-2008** (no data exists) | Caption now says there's nothing earlier to compare with |
| **"Deploy" button** (developer toolbar) visible | `client.toolbarMode = "viewer"` in `.streamlit/config.toml` |
| VIP table showed raw floats `117124.438`; Segment column cut off | Formatted columns ("Total spend" in $, "Orders", "Days since last"), and the Segment column was dropped (every row is VIP) |
| Avg Spend "$18762" | `money()` → $18.8K |
| **Clicking "Run accuracy check" made the forecast chart disappear** | Real UX bug. A Streamlit button is `True` only for the single rerun after the click, so any other click reset it. The request is now remembered in `st.session_state`, and the forecast is cached with `st.cache_data` so it isn't refitted each time. |

## Public deployment safeguard
A public app shares **one** Groq key with every visitor. The Analyst tab now allows
`MAX_QUESTIONS_PER_SESSION` questions per browser session (default 15, configurable in secrets).
Groq's free tier has no charges, and the key can be revoked and replaced at any time.

## Compatibility check
Before writing CI I created a **fresh Python 3.12 environment**, installed only `requirements-dev.txt`
and ran the tests: **45 passed**. This proves the 7-line `requirements.txt` is complete (nothing is
missing that happened to be installed locally) and that the code runs on a newer Python. CI and
deployment use 3.12.

## Final state
- 45 tests, about 10 s, offline. CI runs them on every push.
- Agent benchmark 20/20 (v1 baseline 18/20 kept for comparison).
- Forecast backtest: honest result (a baseline beats Prophet).
- 6 phase notes in `docs/`.

## Resume bullets (use the live URL once deployed)
> **RetailGenius: Retail Analytics with an LLM SQL Agent** | Python, LangChain, Groq, SQLite, Prophet, Streamlit, pytest, GitHub Actions
> - Built a natural-language-to-SQL agent over 8.4K retail order lines with a **read-only database connection**
>   (prompt-injection-safe) and visible generated SQL; created a 20-question benchmark with SQL-computed answers
>   and a deterministic grader, raising accuracy from **18/20 to 20/20** by adding schema notes to the system prompt.
> - Evaluated a Prophet sales forecast with a **rolling 3-fold backtest** against naive baselines (monthly MAPE
>   14.2% vs 12.1% for a historical average) and reported the baseline win in the app instead of overselling the model.
> - Refactored a single-file Streamlit app into a tested package (**45 pytest tests, CI**), fixing metric bugs such
>   as counting line items as orders, which had put 78 customers in the wrong RFM segment.

## Interview talking points
- "I took screenshots of the real app as a final check, and they found a bug the unit tests couldn't: Streamlit
  buttons reset on the next interaction, so the forecast disappeared. I fixed it with session state and caching."
- "Before writing CI I installed the requirements into a clean environment on a newer Python, to prove nothing
  was missing from requirements.txt."
- "The public demo shares one API key, so I cap questions per session."
