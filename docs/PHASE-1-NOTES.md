# Phase 1 — Repo Cleanup & Secret Handling

## Why this phase
A recruiter opening the repo sees the file list first. Junk files, a 100-line
`requirements.txt`, and "paste your API key into app.py" make the project look
unfinished — and the key instruction is a real security problem (keys pushed
to GitHub get scraped by bots within minutes).

## What we changed

| File | Change | Why |
|---|---|---|
| `2.0.1` | **Deleted** | Accidental file. Running `pip install xlrd>=2.0.1` without quotes makes the shell treat `>` as "redirect output to a file named 2.0.1". |
| `requirements.txt` | 103 lines → 7 packages | The old file was a `pip freeze` dump (every sub-dependency). Now it lists only what the code imports; pip pulls the rest automatically. `langchain` was removed — the agent comes from `langchain-community`, which already depends on `langchain-classic`. |
| `.gitignore` | Added `.streamlit/secrets.toml`, `.env` | So the real key can never be committed by accident. |
| `.streamlit/secrets.toml.example` | **New** | A template showing the expected format, with a fake key. Common pattern: commit the example, ignore the real file. |
| `app.py` | New `get_groq_api_key()` | Reads the key from Streamlit secrets, falling back to the `GROQ_API_KEY` env var. No placeholder string in the code, and the bare `except:` is replaced by `except FileNotFoundError` (a bare except also swallows typos and Ctrl+C). |
| `README.md` | Fixed clone URL + setup steps | Removed `YOUR_USERNAME`, added venv steps, and the key goes in `secrets.toml` instead of the code. |

## Main code
```python
def get_groq_api_key():
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except FileNotFoundError:
        pass  # no secrets.toml at all -> use env var
    return os.environ.get("GROQ_API_KEY")
```
Streamlit raises `StreamlitSecretNotFoundError` when there is no secrets file —
it subclasses `FileNotFoundError`, which is why that catch works.

## Checkpoint test (passed)
Ran the app headlessly with `streamlit.testing.v1.AppTest`:
1. App loads with no key → no crash, all 4 tabs render.
2. Asking the analyst a question with no key → clear error explaining where to put it.
3. Key supplied via env var → app picks it up.

## Extra fix found while testing: retired model
With a real key, the Analyst tab failed with `404 model_not_found`:
Groq had retired `llama-3.3-70b-versatile`. Two changes:

1. **Model is now a setting** — `GROQ_MODEL` (secrets or env var), default
   `openai/gpt-oss-120b`, the strongest chat model the key could access. The
   next retirement is a config change, not a code change. (`get_groq_api_key()`
   became a general `get_setting(name, default)`.)
2. **`agent_type="tool-calling"`** — the old default agent is "ReAct": the model
   writes tool calls as plain text (`Action: sql_db_query ...`) that LangChain
   parses. Newer models like gpt-oss use *native* tool calling instead, which
   crashed with `Tool choice is none, but model called a tool`. The tool-calling
   agent uses the API's structured tool calls, so no text parsing (and no
   `handle_parsing_errors` hack) is needed.

Verified: "What were the total sales in 2012?" → agent answered **3,719,963.86**,
identical to the hand-written SQL.

## Interview talking point
"I keep secrets out of source control: the app reads the key from Streamlit
secrets or an environment variable, the real file is git-ignored, and an
example file documents the format."
