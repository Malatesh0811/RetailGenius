# Deploying RetailGenius to Streamlit Community Cloud (free)

Streamlit Community Cloud runs the app straight from the GitHub repo. Every push to `main`
redeploys it automatically.

## Before you start
- The repo is **public** on GitHub (the free tier deploys public repos).
- `sales.db` is committed, so the app needs no build step.
- You have your Groq API key ready. It goes into Streamlit's **Secrets** box, never into the repo.

## Steps
1. Go to **https://share.streamlit.io** and sign in with GitHub. Allow access to your repositories.
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Fill in:
   | Field | Value |
   |---|---|
   | Repository | `Malatesh0811/RetailGenius` |
   | Branch | `main` |
   | Main file path | `app.py` |
   | App URL | e.g. `retailgenius-malatesh` → `https://retailgenius-malatesh.streamlit.app` |
4. Open **Advanced settings**:
   - **Python version:** 3.12 (the same version CI tests on)
   - **Secrets:** paste
     ```toml
     GROQ_API_KEY = "gsk_your_real_key"
     # optional:
     # GROQ_MODEL = "openai/gpt-oss-120b"
     # MAX_QUESTIONS_PER_SESSION = 15
     ```
5. Click **Deploy**. The first build installs Prophet and LangChain and takes a few minutes.
6. Put the URL in the README (`**Live demo:**` line at the top) and on your resume.

## After deploying, check
- The Overview loads and shows 5,496 orders.
- Forecast → Run Simulation → Run accuracy check shows the backtest table.
- Analyst: ask "How many orders are there in total?" The answer should be 5,496, and "Show SQL" should show
  `COUNT(DISTINCT order_id)`.

## Things to know
| Topic | Detail |
|---|---|
| **Shared API key** | Every visitor uses your Groq key. Groq's free tier has rate limits but no charges unless you add billing. Keep it on the free tier. The app caps questions per session (`MAX_QUESTIONS_PER_SESSION`, default 15). If the key is ever abused, revoke it at console.groq.com and paste a new one into Secrets. |
| **Sleeping** | Free apps go to sleep after a few days without visitors. The first visit then shows "wake up" and takes about 30 s. Open the link yourself before an interview. |
| **Model retirement** | If Groq retires `openai/gpt-oss-120b`, the Analyst tab shows a `model_not_found` error. Set `GROQ_MODEL` in Secrets to a current model from https://console.groq.com/docs/models. No code change is needed. |
| **Logs** | In the app's "Manage app" panel (bottom right) you can see build and runtime logs. |
| **Updating** | `git push` to `main` → automatic redeploy. |
