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
    """Test the bigquery agent locally."""
    print("Testing BigQuery Agent locally...\n")
    
    runner = InMemoryRunner(agent=root_agent)
    
    test_queries = [
        "Execute the SQL file 'datasets/uc2-multi-agent-workflow-for-intelligent-data-integration/Sample-DataSet-CommercialLending/Target-Schema/fact_payments.sql' from the bucket 'datasets-ccibt-hack25ww7-750' on the 'worldbank_target_dataset' dataset. The file uses 'analytics' as a hardcoded dataset name.",
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
    asyncio.run(test_agent())

