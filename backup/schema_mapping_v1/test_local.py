"""Local testing script for the Schema Mapping Agent."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema_mapping.agent import root_agent


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def test_schema_mapping():
    """Test the schema mapping functionality."""
    
    print_header("Schema Mapping Agent - Local Test")
    
    print("This agent helps create schema mappings between BigQuery tables.")
    print("It will analyze source and target schemas, suggest mappings, and generate SQL.\n")
    
    # Default test tables (Commercial Lending dataset)
    default_source = "ccibt-hack25ww7-750.test_staging_dataset.borrower"
    default_target = "ccibt-hack25ww7-750.test_dataset.dim_borrower"
    
    print("Example tables:")
    print(f"  Source: {default_source}")
    print(f"  Target: {default_target}\n")
    
    # Check for authentication
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS not set.")
        print("   Make sure you're authenticated with BigQuery:")
        print("   1. Run: gcloud auth application-default login")
        print("   2. Or set GOOGLE_APPLICATION_CREDENTIALS to your service account key\n")
    
    # Interactive mode
    print_header("Interactive Mode")
    print("You can now chat with the agent to create schema mappings.\n")
    print("Example prompts:")
    print("  - Create a schema mapping from <source> to <target>")
    print("  - Show me details about table <table_name>")
    print("  - Get sample data from <table_name>")
    print("  - Analyze column <column_name> in <table_name>")
    print("  - Change the mapping for column X to column Y")
    print("  - Generate a MERGE statement instead")
    print("\nType 'quit' or 'exit' to stop.\n")
    
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for using the Schema Mapping Agent!")
                break
            
            # Quick start option
            if user_input.lower() in ['default', 'test', 'demo']:
                user_input = f"Create a schema mapping from {default_source} to {default_target}"
                print(f"You: {user_input}")
            
            # Add to history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Get agent response
            print("\n🤖 Agent: ", end="", flush=True)
            
            response = root_agent.generate_response(
                message=user_input,
                conversation_history=conversation_history[:-1]  # Exclude current message
            )
            
            print(response)
            
            # Add response to history
            conversation_history.append({"role": "agent", "content": response})
            
            print()  # Empty line for readability
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again or type 'quit' to exit.\n")


def test_direct_function_calls():
    """Test the agent's functions directly (non-interactive)."""
    
    print_header("Direct Function Test")
    
    source = "ccibt-hack25ww7-750.test_staging_dataset.borrower"
    target = "ccibt-hack25ww7-750.test_dataset.dim_borrower"
    
    print(f"Testing direct schema mapping:")
    print(f"  Source: {source}")
    print(f"  Target: {target}\n")
    
    try:
        from schema_mapping.agent import map_schemas
        
        result = map_schemas(source, target)
        print(result)
        
        print("\n✅ Direct function test completed!")
        print("   Check the schema_mapping/output/ directory for generated files.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Ensure you're authenticated with BigQuery")
        print("  2. Verify the tables exist")
        print("  3. Check that table names are correct")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test the Schema Mapping Agent')
    parser.add_argument('--mode', choices=['interactive', 'direct'], default='interactive',
                       help='Test mode: interactive (chat) or direct (function call)')
    parser.add_argument('--source', help='Source table name (for direct mode)')
    parser.add_argument('--target', help='Target table name (for direct mode)')
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        test_schema_mapping()
    else:
        if args.source and args.target:
            # Override defaults for direct test
            from schema_mapping.agent import map_schemas
            print_header("Direct Function Test")
            print(f"Source: {args.source}")
            print(f"Target: {args.target}\n")
            result = map_schemas(args.source, args.target)
            print(result)
        else:
            test_direct_function_calls()


if __name__ == "__main__":
    main()

