import google.auth
from google.adk import Agent
from google.adk.tools.bigquery import BigQueryToolset, BigQueryCredentialsConfig

# 1. Load Application Default Credentials
credentials, _ = google.auth.default()
credentials_config = BigQueryCredentialsConfig(credentials=credentials)

# 2. Initialize the BigQuery Toolset
# This toolset gives the agent the ability to:
# - list_table_ids, get_table_info, execute_sql
bigquery_toolset = BigQueryToolset(credentials_config=credentials_config)

# 3. Define the Agent
agent = Agent(
    name="bigquery_expert",
    model="gemini-2.0-flash",
    description="An agent that queries BigQuery to answer data questions.",
    instruction="""
    You are a data analyst with access to BigQuery.
    - Your target project is 'ccibt-hack25ww7-750'.
    - Your target dataset is 'worldbank_dataset'.
    
    When a user asks a question:
    1. Use 'list_table_ids' to see what tables are available.
    2. Use 'get_table_info' to understand the schema of relevant tables.
    3. Generate and run a SQL query using 'execute_sql'.
    4. Provide a clear answer based on the data. Do not hallucinate.
    """,
    tools=[bigquery_toolset]
)

# Expose the agent as root_agent for ADK CLI discovery
root_agent = agent


if __name__ == "__main__":
    import asyncio
    asyncio.run(agent.run_cli())