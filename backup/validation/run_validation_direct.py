#!/usr/bin/env python3
"""
Direct validation runner - bypasses ADK agent and calls validation functions directly.
This is simpler and more reliable for the hackathon use case.
"""

import os
import json
import sys
import argparse
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from agents.validation.infrastructure.load_staging import load_directory
from agents.validation.validation_agent import validate_data

# Load environment variables
load_dotenv('agents/validation/.env')

def run_validation(project_id, mappings, mode):
    """Run validation directly without ADK agent."""
    print(f"\n{'='*60}")
    print(f"Step 3: Running Validation (Mode: {mode})")
    print(f"{'='*60}\n")

    total_errors = 0
    total_fixed = 0
    tables_processed = 0

    for idx, mapping in enumerate(mappings, 1):
        target_table = mapping["target_table"]
        rules = mapping.get("rules", [])
        bq_table_id = f"{project_id}.{target_table}"

        # Pass rules as JSON string
        rules_str = json.dumps(rules)

        print(f"[{idx}/{len(mappings)}] Validating: {target_table}")
        print(f"    Rules: {len(rules)} validation rule(s)")

        try:
            # Call validation function directly
            result_json = validate_data(bq_table_id, rules_str, mode)
            result = json.loads(result_json)

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
                print(f"    ✗ Validation status: {result.get('status')} - {result.get('message', 'Unknown error')}")

            tables_processed += 1

        except Exception as e:
            print(f"    ✗ Validation failed: {e}")

    print(f"\n{'='*60}")
    print(f"Validation Summary")
    print(f"{'='*60}")
    print(f"Tables Processed: {tables_processed}/{len(mappings)}")
    if mode == 'REPORT':
        print(f"Total Errors Found: {total_errors}")
        if total_errors > 0:
            print(f"\n💡 Check {project_id}.test_staging_dataset.staging_errors table for details.")
    else:
        print(f"Total Rows Corrected: {total_fixed}")
    print(f"{'='*60}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Direct Validation Runner (No Agent)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", type=str, choices=["REPORT", "FIX"], required=True,
                        help="Mode: REPORT (find errors) or FIX (auto-correct)")
    parser.add_argument("--skip-load", action="store_true",
                        help="Skip loading staging data (use existing tables)")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("VALIDATION RUNNER (Direct Mode)")
    print("="*60)

    # Get project ID
    project_id = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "ccibt-hack25ww7-750"))
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
        return 1

    # 1. Load Staging Data (optional)
    print("="*60)
    print("Step 1: Loading Staging Data")
    print("="*60)
    if not args.skip_load:
        if not os.path.exists(data_dir):
            print(f"✗ Error: Data directory not found at {data_dir}")
            return 1
        try:
            dataset_id = os.getenv("BQ_DATASET_ID", "test_staging_dataset")
            load_directory(data_dir, project_id, dataset_id)
            print(f"\n✓ Staging data loaded successfully\n")
        except Exception as e:
            print(f"\n✗ Failed to load staging data: {e}")
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

    # 3. Run Validation
    try:
        run_validation(project_id, mappings, args.mode)
        return 0
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
