from google.adk.agents.llm_agent import Agent
from .tools.bigquery_tools import execute_sql_from_gcs

root_agent = Agent(
    model="gemini-2.5-pro",
    name="bigquery_agent",
    description="An agent that can execute SQL queries in Google BigQuery from a .sql file in a GCS bucket.",
    instruction="You are a helpful assistant that can execute queries in BigQuery.",
    tools=[
        execute_sql_from_gcs,
    ],
)
