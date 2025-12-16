"""Test the agent locally before deployment."""

import os
import asyncio
from dotenv import load_dotenv
import vertexai
from google.adk.runners import InMemoryRunner
from agent import root_agent

# Load environment variables from .env file
load_dotenv()

# Initialize Vertex AI
vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
)


async def test_agent():
    """Test the staging loader agent locally."""
    print("Testing Staging Loader Agent locally...\n")
    
    runner = InMemoryRunner(agent=root_agent)
    
    # To make the DDL test work, create the following directory and file:
    # - ./staging_loader_agent/ddl/schema.sql
    # To make the CSV test work, you need a GCS bucket with a CSV file.
    # For example: gs://your-bucket/data/my_table.csv
    
    test_queries = [
        "Load all DDLs from the './staging_loader_agent/ddl' directory.",
        "Load all CSVs from the bucket 'datasets-ccibt-hack25ww7-750' with prefix 'staging_loader_agent/data/' into the 'worldbank_target_dataset' dataset. Use WRITE_TRUNCATE mode.",
    ]
    
    # Use run_debug which handles session creation automatically
    events = await runner.run_debug(
        user_messages=test_queries,
        user_id="test_user",
        session_id="test_session",
        verbose=True,  # Set to True to see tool calls
    )
    
    print("\n✅ Test completed successfully!")
    print(f"Total events generated: {len(events)}")
    
    await runner.close()


if __name__ == "__main__":
    # Create dummy files for DDL testing
    if not os.path.exists("./staging_loader_agent/ddl"):
        os.makedirs("./staging_loader_agent/ddl")
    with open("./staging_loader_agent/ddl/schema.sql", "w") as f:
        f.write("CREATE OR REPLACE TABLE my_table (id INT64);")
        
    # For CSV testing, you need to upload a file to your GCS bucket.
    # For example, create a local file 'my_table.csv' with the content:
    # id
    # 1
    # 2
    # 3
    # And then upload it to your bucket 'datasets-ccibt-hack25ww7-750' under the 'staging_loader_agent/data/' prefix.
    # You can use the following gsutil command:
    # gsutil cp my_table.csv gs://datasets-ccibt-hack25ww7-750/staging_loader_agent/data/
        
    asyncio.run(test_agent())
