#!/usr/bin/env python3
"""
Quick test runner for schema_mapper.py

This script runs the schema mapper with the worldbank datasets
and displays a preview of the results.
"""

import sys
import os

# Add parent directory to path so we can import schema_mapper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_mapper import generate_schema_mapping
import json

def test_schema_mapper():
    """Run a test of the schema mapper with worldbank datasets."""

    print("\n" + "="*70)
    print("SCHEMA MAPPER TEST RUN")
    print("="*70 + "\n")

    print("This will:")
    print("  1. Fetch schemas from BigQuery")
    print("  2. Use Gemini 1.5 Pro to generate mappings")
    print("  3. Save output to JSON file")
    print("  4. Display summary\n")

    # Use absolute path for output file to avoid path resolution issues
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "test_worldbank_mapping.json")

    print(f"Output will be saved to: {output_file}\n")

    # Run the schema mapper
    result = generate_schema_mapping(
        source_dataset="worldbank_staging_dataset",
        target_dataset="worldbank_target_dataset",
        output_file=output_file,
        mode="REPORT"  # Start with REPORT to see what's unmapped
    )

    if result.get("status") == "success":
        print("\n" + "="*70)
        print("✅ SUCCESS!")
        print("="*70)

        # Load and display key info
        mapping_data = result["mapping"]

        print(f"\n📊 Mapping Statistics:")
        print(f"   • Total table mappings: {len(mapping_data.get('mappings', []))}")
        print(f"   • Output file: {result['output_file']}")
        print(f"   • Confidence: {mapping_data.get('metadata', {}).get('confidence', 'unknown')}")

        print(f"\n📋 Table Mappings:")
        for i, mapping in enumerate(mapping_data.get('mappings', []), 1):
            print(f"\n   {i}. {mapping.get('source_table', 'N/A')}")
            print(f"      → {mapping.get('target_table', 'N/A')}")
            print(f"      • Column mappings: {len(mapping.get('column_mappings', []))}")
            print(f"      • Validation rules: {len(mapping.get('validation_rules', []))}")
            print(f"      • Unmapped target columns: {len(mapping.get('unmapped_target_columns', []))}")

            # Show first unmapped column as example
            unmapped = mapping.get('unmapped_target_columns', [])
            if unmapped:
                print(f"      • Example unmapped: {unmapped[0]}")

        print(f"\n💡 Next Steps:")
        print(f"   1. Review the mapping file: {result['output_file']}")
        print(f"   2. Check unmapped columns and validation rules")
        print(f"   3. Try FIX mode to see default suggestions:")
        print(f"      Change mode='REPORT' to mode='FIX' in test_runner.py")

        return True

    else:
        print("\n" + "="*70)
        print("❌ FAILED")
        print("="*70)
        print(f"\nError: {result.get('message', 'Unknown error')}")

        print("\n🔧 Troubleshooting:")
        print("   • Verify GCP_PROJECT_ID in .env file")
        print("   • Check: gcloud auth application-default login")
        print("   • Verify datasets exist: bq ls")
        print("   • Enable Vertex AI: gcloud services enable aiplatform.googleapis.com")

        return False


if __name__ == "__main__":
    try:
        success = test_schema_mapper()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

