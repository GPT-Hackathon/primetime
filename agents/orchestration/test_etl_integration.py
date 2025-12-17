#!/usr/bin/env python3
"""
Test script for ETL Agent integration with Orchestration Agent.

This demonstrates the complete 4-stage workflow:
1. Load staging data (optional)
2. Generate schema mapping
3. Validate data
4. Generate and execute ETL SQL
"""

import os
from dotenv import load_dotenv
from google.adk.runners.in_memory_runner import InMemoryRunner

# Load environment variables
load_dotenv()

# Import the orchestration agent
from agents.orchestration.agent import root_agent


def test_etl_workflow():
    """Test the complete workflow including ETL generation and execution."""
    
    print("=" * 80)
    print("Testing ETL Agent Integration with Orchestration")
    print("=" * 80)
    
    runner = InMemoryRunner(root_agent)
    
    # Test 1: Generate Schema Mapping
    print("\n" + "=" * 80)
    print("TEST 1: Generate Schema Mapping")
    print("=" * 80)
    
    response = runner.run("""
        Generate a schema mapping from worldbank_staging_dataset to worldbank_target_dataset.
        Use FIX mode to generate comprehensive mappings.
    """)
    print(response)
    
    # Test 2: List Mappings
    print("\n" + "=" * 80)
    print("TEST 2: List Available Mappings")
    print("=" * 80)
    
    response = runner.run("List all schema mappings")
    print(response)
    
    # Test 3: Generate ETL SQL
    print("\n" + "=" * 80)
    print("TEST 3: Generate ETL SQL from Mapping")
    print("=" * 80)
    
    response = runner.run("""
        Generate ETL SQL scripts from the schema mapping we just created.
        Use the mapping ID: worldbank_staging_dataset_to_worldbank_target_dataset
    """)
    print(response)
    
    # Test 4: List ETL Scripts
    print("\n" + "=" * 80)
    print("TEST 4: List Generated ETL Scripts")
    print("=" * 80)
    
    response = runner.run("List all ETL scripts")
    print(response)
    
    # Test 5: Get ETL SQL Details
    print("\n" + "=" * 80)
    print("TEST 5: Get ETL SQL Details")
    print("=" * 80)
    
    response = runner.run("""
        Show me the generated ETL SQL scripts.
        ETL ID: worldbank_staging_dataset_to_worldbank_target_dataset_etl
    """)
    print(response)
    
    # Test 6: Execute ETL (with confirmation)
    print("\n" + "=" * 80)
    print("TEST 6: Execute ETL SQL (Simulated)")
    print("=" * 80)
    
    print("\nNOTE: In a real scenario, you would:")
    print("1. Review the SQL scripts carefully")
    print("2. Confirm execution with the user")
    print("3. Then execute with:")
    print("   execute_etl_sql(etl_id='...', target_dataset='worldbank_target_dataset')")
    print("\nFor this test, we're skipping actual execution to avoid modifying data.")
    
    # Test 7: Workflow Status
    print("\n" + "=" * 80)
    print("TEST 7: Check Workflow Status")
    print("=" * 80)
    
    response = runner.run("List all workflows and show their status")
    print(response)
    
    print("\n" + "=" * 80)
    print("ETL Integration Test Complete!")
    print("=" * 80)


def test_step_by_step_etl():
    """Test step-by-step ETL workflow with user interaction."""
    
    print("\n\n" + "=" * 80)
    print("Testing Step-by-Step ETL Workflow")
    print("=" * 80)
    
    runner = InMemoryRunner(root_agent)
    
    # Simulate user conversation
    conversation = [
        "I want to map worldbank_staging to worldbank_target",
        "Now validate the mapping",
        "Generate ETL SQL from the mapping",
        "Show me the SQL scripts",
        # "Execute the ETL SQL in worldbank_target_dataset"  # Commented out for safety
    ]
    
    for i, user_message in enumerate(conversation, 1):
        print(f"\n{'=' * 80}")
        print(f"Step {i}: User says: '{user_message}'")
        print('=' * 80)
        
        response = runner.run(user_message)
        print(f"\nOrchestrator response:\n{response}")


if __name__ == "__main__":
    # Check environment variables
    if not os.getenv("GCP_PROJECT_ID") and not os.getenv("GOOGLE_CLOUD_PROJECT"):
        print("⚠️  Warning: GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT not set")
        print("Set one of these environment variables before running tests.")
        print("\nExample:")
        print("  export GCP_PROJECT_ID=your-project-id")
        print("  python test_etl_integration.py")
        exit(1)
    
    try:
        # Run the tests
        test_etl_workflow()
        test_step_by_step_etl()
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

