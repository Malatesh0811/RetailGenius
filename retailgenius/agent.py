"""Natural-language-to-SQL agent (LangChain + Groq) over a read-only database."""
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

from retailgenius.data import DB_PATH, TABLE

DEFAULT_MODEL = "openai/gpt-oss-120b"  # Groq retires models; override with the GROQ_MODEL setting


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
    return create_sql_agent(llm=llm, toolkit=toolkit, agent_type="tool-calling", verbose=False)


def ask(agent, question):
    return agent.invoke({"input": question})["output"]
