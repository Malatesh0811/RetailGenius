"""Natural-language-to-SQL agent (LangChain + Groq) over a read-only database."""
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.prompt import SQL_PREFIX
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

from retailgenius.data import DB_PATH, TABLE

DEFAULT_MODEL = "openai/gpt-oss-120b"  # Groq retires models; override with the GROQ_MODEL setting

# Facts about the data that the column names alone don't reveal. Added after the first evaluation
# run (evals/results-v1-baseline.md): the agent counted product rows as orders (335 vs 123).
# These describe the table in general - they are not answers to specific test questions.
DATA_NOTES = """
Notes about the `orders` table:
- Each row is one order LINE (one product within an order). An order can span several rows.
  To count orders, use COUNT(DISTINCT order_id), never COUNT(*). Use COUNT(*) only when asked about rows/lines.
- order_date and ship_date are stored as TEXT like '2012-12-31 00:00:00'. Use strftime() or substr()
  for year/month filters, and julianday() for date differences.
- Customers are identified by customer_name. `region` holds regions such as 'West' or 'Ontario'.
"""


def read_only_db(db_path=DB_PATH):
    """SQLDatabase opened with SQLite's mode=ro, so INSERT/UPDATE/DELETE/DROP are refused by SQLite itself.

    Least privilege: even a wrong or prompt-injected query from the LLM cannot change the data.
    """
    uri = f"sqlite:///file:{db_path.resolve().as_posix()}?mode=ro&uri=true"
    return SQLDatabase.from_uri(uri, include_tables=[TABLE])


def build_sql_agent(api_key, model=DEFAULT_MODEL, db_path=DB_PATH):
    from langchain_groq import ChatGroq

    llm = ChatGroq(temperature=0, groq_api_key=api_key, model_name=model)
    toolkit = SQLDatabaseToolkit(db=read_only_db(db_path), llm=llm)
    # "tool-calling" uses the API's structured tool calls; newer models (gpt-oss) don't
    # work with the old text-parsing ReAct agent.
    # return_intermediate_steps lets us see which SQL the agent actually ran.
    return create_sql_agent(llm=llm, toolkit=toolkit, agent_type="tool-calling", verbose=False,
                            prefix=SQL_PREFIX + DATA_NOTES,
                            agent_executor_kwargs={"return_intermediate_steps": True})


def ask(agent, question):
    return ask_with_sql(agent, question)[0]


def ask_with_sql(agent, question):
    """Returns (answer text, list of SQL queries the agent executed)."""
    result = agent.invoke({"input": question})
    queries = [action.tool_input.get("query", "") for action, _ in result.get("intermediate_steps", [])
               if action.tool == "sql_db_query" and isinstance(action.tool_input, dict)]
    return result["output"], queries
