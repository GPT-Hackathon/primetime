from google.adk.agents.llm_agent import Agent
from etl_agent.tools.gen_etl_sql import generate_etl_sql_from_json_string, execute_sql

root_agent = Agent(
    model="gemini-2.5-pro",
    name="etl_agent_with_human_in_the_loop_sql_execution",
    description="An agent that generates ETL SQL scripts from JSON mapping rules and executes them in BigQuery after human confirmation.",
    instruction="You are a helpful assistant that can generate ETL SQL scripts from JSON mapping rules. After generating the SQL, you must present it to the user and ask for confirmation before executing it. If the user approves, you can then execute the SQL in BigQuery.",
    tools=[
        generate_etl_sql_from_json_string,
        execute_sql,
    ],
)