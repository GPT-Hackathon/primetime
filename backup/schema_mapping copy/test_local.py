#!/usr/bin/env python3
"""
Test the Schema Mapping Agent locally with ADK runner.

Usage:
    python test_local.py

This will run the agent with test queries and display the results.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Vertex AI
import vertexai
vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT_ID", "ccibt-hack25ww7-750")),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
)

from agent import root_agent
from google.adk.runners import InMemoryRunner


async def test_schema_mapping_agent():
    """Test the schema mapping agent locally."""
    print("\n" + "="*70)
    print("TESTING SCHEMA MAPPING AGENT LOCALLY")
    print("="*70 + "\n")

    runner = InMemoryRunner(agent=root_agent)

    # Test queries - demonstrating state management
    test_queries = [
        "Hello! What can you do?",
        "Can you fetch the schema for the table ccibt-hack25ww7-750.worldbank_staging_dataset.staging_countries?",
        "Generate a schema mapping between worldbank_staging_dataset and worldbank_target_dataset in FIX mode",
        "Save that mapping as 'worldbank_v1'",
        "List all saved mappings",
        "Extract validation rules from worldbank_v1 for the dim_country table",
    ]

    print("Running test queries:")
    for i, query in enumerate(test_queries, 1):
        print(f"  {i}. {query}")
    print()

    # Run agent with debug mode
    events = await runner.run_debug(
        user_messages=test_queries,
        user_id="test_user",
        session_id="test_session",
        verbose=True,  # Set to True to see tool calls
    )

    print("\n" + "="*70)
    print(f"✅ Test completed successfully!")
    print(f"Total events generated: {len(events)}")
    print("="*70 + "\n")

    # Print conversation summary
    print("Conversation Summary:")
    print("-" * 70)
    for i, event in enumerate(events, 1):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text = part.text
                    # Truncate long responses
                    if len(text) > 200:
                        text = text[:200] + "..."
                    print(f"\n[{event.author}] {text}")

    await runner.close()
    return events


def main():
    """Main entry point."""
    try:
        print("\n🚀 Starting Schema Mapping Agent test...\n")
        events = asyncio.run(test_schema_mapping_agent())
        print(f"\n✨ Generated {len(events)} events\n")
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

