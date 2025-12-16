import os
import json
import argparse
import sys
import asyncio
import vertexai
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner

# Ensure we can import from project root
sys.path.append(os.getcwd())

try:
    from agents.validation.infrastructure.load_staging import load_staging_tables
    from agents.validation.validation_agent import validation_agent
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please run this script from the project root directory: python agents/validation/main.py")
    sys.exit(1)

# Load env (if .env exists)
load_dotenv()

async def run_agent_validation(project_id, mappings, mode):
    print(f"\n{'='*60}")
    print(f"Step 3: Running Validation Agent (Mode: {mode})")
    print(f"{'='*60}\n")

    # Initialize Vertex AI
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    try:
        vertexai.init(project=project_id, location=location)
        print(f"✓ Vertex AI initialized (Project: {project_id}, Location: {location})\n")
    except Exception as e:
        print(f"✗ Failed to initialize Vertex AI: {e}")
        return

    runner = InMemoryRunner(agent=validation_agent)

    total_errors = 0
    total_fixed = 0
    tables_processed = 0

    for idx, mapping in enumerate(mappings, 1):
        target_table = mapping["target_table"]
        rules = mapping.get("rules", [])
        bq_table_id = f"{project_id}.{target_table}"

        # Pass rules as JSON string
        rules_str = json.dumps(rules)

        print(f"\n[{idx}/{len(mappings)}] Validating: {target_table}")
        print(f"    Rules: {len(rules)} validation rule(s)")

        # Construct a natural language prompt for the agent
        prompt = f"Validate the table '{bq_table_id}' using the following rules: {rules_str}. The mode is '{mode}'."

        try:
            # We use run_debug for simple local execution.
            # In a real scenario, we might want to inspect tool calls directly or parse the output.
            # The tool `validate_data` returns a JSON string. The agent will likely include this in its response.
            events = await runner.run_debug(
                user_messages=[prompt],
                user_id="validation_user",
                verbose=False  # Set to True for detailed debugging
            )

            # Try to extract results from agent output
            # The agent should return a response containing the JSON result
            if events and len(events) > 0:
                last_event = events[-1]
                if hasattr(last_event, 'content'):
                    try:
                        # Try to parse JSON from the response
                        content_str = str(last_event.content)
                        if '{' in content_str and '}' in content_str:
                            json_start = content_str.index('{')
                            json_end = content_str.rindex('}') + 1
                            result = json.loads(content_str[json_start:json_end])

                            if result.get('status') == 'success':
                                if mode == 'REPORT':
                                    errors = result.get('errors_found', 0)
                                    total_errors += errors
                                    print(f"    ✓ Found {errors} error(s)")
                                else:
                                    fixed = result.get('rows_corrected', 0)
                                    total_fixed += fixed
                                    print(f"    ✓ Fixed {fixed} row(s)")
                            else:
                                print(f"    ✗ Validation status: {result.get('status')}")
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"    ⚠ Could not parse validation results")

            tables_processed += 1

        except Exception as e:
            print(f"    ✗ Agent execution failed: {e}")

    await runner.close()

    print(f"\n{'='*60}")
    print(f"Validation Summary")
    print(f"{'='*60}")
    print(f"Tables Processed: {tables_processed}/{len(mappings)}")
    if mode == 'REPORT':
        print(f"Total Errors Found: {total_errors}")
        print(f"\nCheck staging.staging_errors table for error details.")
    else:
        print(f"Total Rows Corrected: {total_fixed}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validation Agent Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in REPORT mode (find errors)
  python agents/validation/main.py --mode REPORT

  # Run in FIX mode (auto-correct errors)
  python agents/validation/main.py --mode FIX

  # Skip loading data (use existing tables)
  python agents/validation/main.py --mode REPORT --skip-load

Environment Variables:
  GCP_PROJECT_ID          - Google Cloud Project ID
  GOOGLE_CLOUD_LOCATION   - GCP region (default: us-central1)
  GOOGLE_APPLICATION_CREDENTIALS - Path to service account key
        """
    )
    parser.add_argument("--mode", type=str, choices=["REPORT", "FIX"], required=True,
                        help="Mode: REPORT (find errors) or FIX (auto-correct)")
    parser.add_argument("--skip-load", action="store_true",
                        help="Skip loading staging data (use existing tables)")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("VALIDATION AGENT")
    print("="*60)

    # Determine Project ID
    project_id = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "primetime-hackathon"))
    print(f"Project ID: {project_id}")
    print(f"Mode: {args.mode}")
    print("="*60 + "\n")

    # Paths
    base_dir = os.getcwd()
    schema_path = os.path.join(base_dir, "agents/validation/mock/mock_schema.json")
    data_dir = os.path.join(base_dir, "dataSets/Sample-DataSet-WorldBankData/SourceSchemaData")

    # Validate paths
    if not os.path.exists(schema_path):
        print(f"✗ Error: Schema file not found at {schema_path}")
        print(f"  Please ensure you're running from the project root directory.")
        return 1

    if not args.skip_load and not os.path.exists(data_dir):
        print(f"✗ Error: Data directory not found at {data_dir}")
        print(f"  Please ensure the World Bank dataset exists.")
        return 1

    # 1. Load Staging Data
    print("="*60)
    print("Step 1: Loading Staging Data")
    print("="*60)
    if not args.skip_load:
        try:
            load_staging_tables(schema_path, data_dir, project_id)
            print(f"\n✓ Staging data loaded successfully\n")
        except Exception as e:
            print(f"\n✗ Failed to load staging data: {e}")
            print(f"  Check your GCP credentials and project permissions.")
            return 1
    else:
        print("SKIPPED (using existing tables)\n")

    # 2. Load Rules
    print("="*60)
    print("Step 2: Loading Validation Rules")
    print("="*60)
    try:
        with open(schema_path, "r") as f:
            config = json.load(f)

        mappings = config.get("mappings", [])
        print(f"✓ Loaded {len(mappings)} table mapping(s)\n")

    except Exception as e:
        print(f"✗ Failed to load schema: {e}")
        return 1

    # 3. Run Async Agent
    try:
        asyncio.run(run_agent_validation(project_id, mappings, args.mode))
        return 0
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
