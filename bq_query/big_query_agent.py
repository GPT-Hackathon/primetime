import os
from google.adk import Agent
from google.adk.tools.bigquery import BigQueryToolset

# No need to manually import google.auth if using Default Credentials
# The toolset will pick them up automatically from the environment
bq_tool = BigQueryToolset()

agent = Agent(
    name="bq_analyst",
    model="gemini-1.5-flash",
    instruction="""
    You are a SQL expert for the project 'your-project-id'. 
    Answer questions by querying the 'your_dataset_name' dataset.
    Always inspect the schema first using your tools.
    """,
    tools=[bq_tool]
)

if __name__ == "__main__":
    import asyncio
    asyncio.run(agent.run_cli())