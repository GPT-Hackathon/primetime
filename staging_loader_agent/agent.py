from google.adk.agents.llm_agent import Agent
from .tools.staging_loader_tools import load_csv_to_bigquery_from_gcs

root_agent = Agent(
    model="gemini-2.5-pro",
    name="staging_loader_agent",
    description="An agent that can  CSVs into BigQuery.",
    instruction="You are a helpful assistant that can load data into BigQuery.",
    tools=[
        load_csv_to_bigquery_from_gcs,
    ],
)
