from google.adk.agents.llm_agent import Agent
from .tools.staging_loader_tools import load_csv_to_bigquery_from_gcs, find_schema_files_in_gcs

root_agent = Agent(
    model="gemini-2.5-pro",
    name="staging_loader_agent",
    description="An agent that can load CSVs into BigQuery with flexible schema detection.",
    instruction="""You are a helpful assistant that loads CSV data from Google Cloud Storage into BigQuery.

Your capabilities:
1. **load_csv_to_bigquery_from_gcs**: Load a CSV file from GCS to BigQuery
   - Automatically finds schema files (any file with 'schema' in the name)
   - Uses schema if found, otherwise auto-detects
   - Creates or appends to tables

2. **find_schema_files_in_gcs**: List all schema files in a GCS bucket/folder
   - Helps users discover what schema files are available
   - Searches for any .json file with 'schema' in the name

When loading data:
- Always look for schema files first (flexible naming: schema.json, source_schema.json, etc.)
- If multiple schema files exist, use the first one found
- Fall back to auto-detection if no schema file or table not in schema
- Explain what schema was used (or if auto-detected)

Be helpful and explain the loading process to users!""",
    tools=[
        load_csv_to_bigquery_from_gcs,
        find_schema_files_in_gcs,
    ],
)
