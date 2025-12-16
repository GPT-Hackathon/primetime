#!/usr/bin/env python3
"""
Test script for Data Validation Agent.

Uses schema mapping JSON from schema_mapping agent to validate staging data.
"""

import os
import sys
from dotenv import load_dotenv
import vertexai

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.validation.data_validator import validate_schema_mapping

load_dotenv()

def main():
    # Configuration
    project_id = os.getenv("GCP_PROJECT_ID", "ccibt-hack25ww7-750")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    # Initialize Vertex AI
    print("Initializing Vertex AI...")
    vertexai.init(project=project_id, location=location)
    print(f"✓ Vertex AI initialized (Project: {project_id}, Location: {location})\n")

    # Path to schema mapping JSON (from schema_mapping agent)
    # You can use either:
    # 1. JSON file from schema_mapper.py output
    # 2. JSON file from API response sample

    schema_mapping_file = "agents/schema_mapping/sample_api_response_fix.json"

    # Alternative: use direct output from schema_mapper
    # schema_mapping_file = "agents/schema_mapping/worldbank_mapping_fix.json"

    if not os.path.exists(schema_mapping_file):
        print(f"✗ Error: Schema mapping file not found: {schema_mapping_file}")
        print(f"\nPlease run schema_mapper.py first to generate the mapping:")
        print(f"  cd agents/schema_mapping")
        print(f"  python run_schema_mapper.py")
        return 1

    # Source dataset name
    source_dataset = "worldbank_staging_dataset"

    # Mode: REPORT or FIX
    mode = "REPORT"

    # Run validation
    print(f"Using schema mapping from: {schema_mapping_file}\n")

    result = validate_schema_mapping(
        schema_mapping_json=schema_mapping_file,
        source_dataset=source_dataset,
        mode=mode
    )

    if result.get("status") == "success":
        print("\n✓ Validation completed successfully!")
        print(f"\nTo view errors, run:")
        print(f"  SELECT * FROM `{project_id}.{source_dataset}.staging_errors`")
        print(f"  WHERE run_id = '{result.get('run_id')}'")
        print(f"  ORDER BY created_at DESC")
        return 0
    else:
        print(f"\n✗ Validation failed: {result.get('message')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
