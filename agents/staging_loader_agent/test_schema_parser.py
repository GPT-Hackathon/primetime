"""Test the LLM-based schema parser with various schema formats."""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the parser
from tools.staging_loader_tools import _parse_schema_with_llm

def test_schema_formats():
    """Test the LLM parser with different schema formats."""

    # Test 1: Direct array format
    print("\n" + "="*80)
    print("TEST 1: Direct array format (BigQuery standard)")
    print("="*80)
    schema1 = json.dumps([
        {"name": "id", "type": "INTEGER", "mode": "REQUIRED"},
        {"name": "name", "type": "STRING", "mode": "NULLABLE"},
        {"name": "created_at", "type": "TIMESTAMP", "mode": "NULLABLE"}
    ], indent=2)

    result1 = _parse_schema_with_llm(schema1, "users", "schema.json")
    if result1:
        print(f"✅ Successfully parsed {len(result1)} fields")
        for field in result1:
            print(f"   - {field.name}: {field.field_type} ({field.mode})")
    else:
        print("❌ Failed to parse schema")

    # Test 2: Dictionary with table names
    print("\n" + "="*80)
    print("TEST 2: Dictionary format with table names")
    print("="*80)
    schema2 = json.dumps({
        "users": [
            {"name": "user_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "email", "type": "STRING", "mode": "NULLABLE"}
        ],
        "orders": [
            {"name": "order_id", "type": "INTEGER", "mode": "REQUIRED"},
            {"name": "user_id", "type": "STRING", "mode": "NULLABLE"}
        ]
    }, indent=2)

    result2 = _parse_schema_with_llm(schema2, "users", "multi_table_schema.json")
    if result2:
        print(f"✅ Successfully parsed {len(result2)} fields for 'users' table")
        for field in result2:
            print(f"   - {field.name}: {field.field_type} ({field.mode})")
    else:
        print("❌ Failed to parse schema")

    # Test 3: Table not found in dictionary
    print("\n" + "="*80)
    print("TEST 3: Table not found (should return None)")
    print("="*80)
    result3 = _parse_schema_with_llm(schema2, "products", "multi_table_schema.json")
    if result3 is None:
        print("✅ Correctly returned None for non-existent table")
    else:
        print(f"❌ Expected None, got {len(result3)} fields")

    # Test 4: Nested/complex format
    print("\n" + "="*80)
    print("TEST 4: Complex nested format")
    print("="*80)
    schema4 = json.dumps({
        "schemas": {
            "customers": {
                "fields": [
                    {"name": "customer_id", "type": "INTEGER", "mode": "REQUIRED"},
                    {"name": "full_name", "type": "STRING", "mode": "NULLABLE"}
                ]
            }
        }
    }, indent=2)

    result4 = _parse_schema_with_llm(schema4, "customers", "nested_schema.json")
    if result4:
        print(f"✅ Successfully parsed {len(result4)} fields from nested structure")
        for field in result4:
            print(f"   - {field.name}: {field.field_type} ({field.mode})")
    else:
        print("❌ Failed to parse nested schema")

if __name__ == "__main__":
    print("\n🧪 Testing LLM-based Schema Parser")
    print("="*80)

    # Check environment
    if not os.getenv("GCP_PROJECT_ID") and not os.getenv("GOOGLE_CLOUD_PROJECT"):
        print("❌ ERROR: GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT not set")
        exit(1)

    try:
        test_schema_formats()
        print("\n" + "="*80)
        print("✅ All tests completed!")
        print("="*80 + "\n")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

