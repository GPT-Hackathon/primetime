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
    """Test the hello world agent locally."""
    print("Testing Hello World Agent locally...\n")
    
    runner = InMemoryRunner(agent=root_agent)
    
    test_queries = [
        "Hello!",
        "Greet Alice",
        "What can you do?",
    ]
    
    # Use run_debug which handles session creation automatically
    events = await runner.run_debug(
        user_messages=test_queries,
        user_id="test_user",
        session_id="test_session",
        verbose=False,  # Set to True to see tool calls
    )
    
    print("\n✅ Test completed successfully!")
    print(f"Total events generated: {len(events)}")
    
    await runner.close()


if __name__ == "__main__":
    asyncio.run(test_agent())

