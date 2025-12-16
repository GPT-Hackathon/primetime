#!/usr/bin/env python3
"""
Local test script for Data Validation Agent API.

Tests the API locally before deploying to Cloud Run.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# API URL - change to Cloud Run URL after deployment
API_URL = os.getenv("VALIDATOR_API_URL", "http://localhost:8080")


def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response.status_code == 200


def test_root():
    """Test root endpoint."""
    print("Testing / endpoint...")
    response = requests.get(f"{API_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response.status_code == 200


def test_validate():
    """Test validation endpoint with sample schema mapping."""
    print("Testing /validate endpoint...")

    # Load sample schema mapping
    schema_mapping_file = "../schema_mapping/sample_api_response_fix.json"

    if not os.path.exists(schema_mapping_file):
        print(f"Schema mapping file not found: {schema_mapping_file}")
        return False

    with open(schema_mapping_file, 'r') as f:
        schema_mapping = json.load(f)

    # Make request
    payload = {
        "schema_mapping": schema_mapping,
        "mode": "REPORT"
    }

    response = requests.post(
        f"{API_URL}/validate",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print(f"Status: {response.status_code}")
    result = response.json()

    # Print summary
    print(f"\nValidation Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Run ID: {result.get('run_id')}")
    print(f"  Mode: {result.get('mode')}")

    if "summary" in result:
        summary = result["summary"]
        print(f"\nSummary:")
        print(f"  Tables Validated: {summary.get('tables_validated')}")
        print(f"  Total Validations Run: {summary.get('total_validations_run')}")
        print(f"  Total Errors Found: {summary.get('total_errors_found')}")
        print(f"  Tables With Errors: {summary.get('tables_with_errors')}")
        print(f"  Tables Skipped: {summary.get('tables_skipped')}")

    # Save full response to file
    output_file = "validation_api_response.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nFull response saved to: {output_file}")

    print()
    return response.status_code == 200


def main():
    print("=" * 60)
    print("Data Validation Agent API - Local Test")
    print("=" * 60)
    print(f"API URL: {API_URL}")
    print("=" * 60)
    print()

    results = {
        "health": test_health(),
        "root": test_root(),
        "validate": test_validate()
    }

    print("=" * 60)
    print("Test Results:")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
    print("=" * 60)

    all_passed = all(results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
