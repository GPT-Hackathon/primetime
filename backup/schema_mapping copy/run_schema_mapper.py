#!/usr/bin/env python3
"""
CLI runner for Schema Mapping Agent.

Usage:
    python agents/schema_mapping/run_schema_mapper.py \
        --source worldbank_staging_dataset \
        --target worldbank_target_dataset \
        --output worldbank_mapping.json
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.getcwd())

from agents.schema_mapping.schema_mapper import generate_schema_mapping


def main():
    parser = argparse.ArgumentParser(
        description="Generate schema mapping between BigQuery datasets using LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate mapping for World Bank datasets
  python agents/schema_mapping/run_schema_mapper.py \\
      --source worldbank_staging_dataset \\
      --target worldbank_target_dataset \\
      --output worldbank_mapping.json

  # Generate mapping for test datasets
  python agents/schema_mapping/run_schema_mapper.py \\
      --source test_staging_dataset \\
      --target test_target_dataset \\
      --output test_mapping.json
        """
    )

    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Source BigQuery dataset name (e.g., worldbank_staging_dataset)"
    )

    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Target BigQuery dataset name (e.g., worldbank_target_dataset)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="schema_mapping_output.json",
        help="Output JSON file name (default: schema_mapping_output.json)"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["REPORT", "FIX"],
        default="REPORT",
        help="Mode: REPORT (flag unmapped columns) or FIX (suggest defaults)"
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("SCHEMA MAPPING AGENT - CLI")
    print("="*60)
    print(f"Source: {args.source}")
    print(f"Target: {args.target}")
    print(f"Output: {args.output}")
    print(f"Mode: {args.mode}")
    print("="*60 + "\n")

    # Run the mapping generator
    try:
        result = generate_schema_mapping(
            source_dataset=args.source,
            target_dataset=args.target,
            output_file=args.output,
            mode=args.mode
        )

        if result and result.get("status") == "success":
            print("\n✓ Schema mapping completed successfully!")
            return 0
        else:
            print(f"\n✗ Schema mapping failed: {result}")
            return 1

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
