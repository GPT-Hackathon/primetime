#!/usr/bin/env python3
"""
Schema Mapping Agent using Gemini 2.0 Flash.

Fetches schemas from BigQuery staging and target datasets, uses LLM to map columns,
and outputs a JSON mapping file with validation rules.
"""

import os
import json
from datetime import datetime
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
from dotenv import load_dotenv

# Load environment variables
load_dotenv('agents/validation/.env')

# BigQuery client
project_id = os.getenv("GCP_PROJECT_ID", "ccibt-hack25ww7-750")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
bq_client = bigquery.Client(project=project_id)

# Initialize Vertex AI
vertexai.init(project=project_id, location=location)


# --- 1. BIGQUERY SCHEMA FETCHER ---
def fetch_table_schema(full_table_id: str) -> dict:
    """
    Fetch schema information from BigQuery table.

    Args:
        full_table_id: Format: "project.dataset.table"

    Returns:
        Dictionary with table metadata and column info
    """
    try:
        table = bq_client.get_table(full_table_id)

        columns = []
        for field in table.schema:
            columns.append({
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,  # REQUIRED, NULLABLE, REPEATED
                "description": field.description or ""
            })

        return {
            "table_id": full_table_id,
            "num_rows": table.num_rows,
            "columns": columns
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_dataset_schemas(dataset_id: str) -> dict:
    """
    Fetch all table schemas from a BigQuery dataset.

    Args:
        dataset_id: Format: "project.dataset" or just "dataset"

    Returns:
        Dictionary mapping table names to their schemas
    """
    if '.' not in dataset_id:
        dataset_id = f"{project_id}.{dataset_id}"

    try:
        tables = bq_client.list_tables(dataset_id)
        schemas = {}

        for table in tables:
            full_table_id = f"{dataset_id}.{table.table_id}"
            schemas[table.table_id] = fetch_table_schema(full_table_id)

        return schemas
    except Exception as e:
        return {"error": str(e)}


# --- 2. LLM-BASED SCHEMA MAPPING ---
def generate_schema_mapping_with_llm(source_schemas: dict, target_schemas: dict,
                                     source_dataset: str, target_dataset: str, mode: str = "REPORT") -> dict:
    """
    Use Gemini to analyze schemas and generate mapping JSON.

    Args:
        source_schemas: Dict of source table schemas
        target_schemas: Dict of target table schemas
        source_dataset: Source dataset name
        target_dataset: Target dataset name
        mode: "REPORT" to flag unmapped columns as errors, "FIX" to suggest defaults

    Returns:
        Mapping dictionary
    """

    # Define the tool/function declaration for structured output
    submit_mapping_func = FunctionDeclaration(
        name="submit_schema_mapping",
        description="Submit the final schema mapping JSON with all table and column mappings",
        parameters={
            "type": "object",
            "properties": {
                "mapping_json": {
                    "type": "string",
                    "description": "Complete JSON string containing schema mappings"
                }
            },
            "required": ["mapping_json"]
        }
    )

    mapping_tool = Tool(function_declarations=[submit_mapping_func])

    # Create model with function calling
    model = GenerativeModel(
        "gemini-2.5-flash",
        tools=[mapping_tool]
    )

    # Prepare the prompt
    prompt = f"""
You are a Senior Data Engineer specializing in schema mapping and data migration.

TASK: Generate a comprehensive schema mapping between source and target BigQuery datasets.

SOURCE DATASET: {project_id}.{source_dataset}
SOURCE TABLES & SCHEMAS:
{json.dumps(source_schemas, indent=2)}

TARGET DATASET: {project_id}.{target_dataset}
TARGET TABLES & SCHEMAS:
{json.dumps(target_schemas, indent=2)}

REQUIREMENTS:

1. TABLE MATCHING:
   - Match source tables to target tables (consider name similarity and purpose)
   - Note: Target may have dimensional model (fact/dim tables) while source has flat tables
   - Consider how multiple source tables might map to single target tables

2. COLUMN MAPPING MODE: {mode}

   **REPORT MODE**:
   - For target columns with NO matching source column, set:
     * source_column: "UNMAPPED"
     * source_type: "MISSING"
     * transformation: null
     * notes: "No source column found - requires manual mapping or default value"
   - Add these unmapped columns to "unmapped_target_columns" list
   - Add to "mapping_errors" array for reporting

   **FIX MODE**:
   - For target columns with NO matching source column, suggest best defaults:
     * source_column: "GENERATED"
     * source_type: "EXPRESSION"
     * transformation: Provide DEFAULT value expression with clear prefix
       - Format: "DEFAULT: <expression>"
       - Examples:
         * "DEFAULT: CURRENT_TIMESTAMP()" (not just "CURRENT_TIMESTAMP()")
         * "DEFAULT: 'staging_gdp'" (not just "'staging_gdp'")
         * "DEFAULT: UUID()" (not just "UUID()")
         * "DEFAULT: 0" (not just "0")
     * notes: Explain why this default is appropriate
   - Use intelligent defaults based on column type and name:
     * timestamp/loaded_at columns → "DEFAULT: CURRENT_TIMESTAMP()"
     * data_source/source columns → "DEFAULT: 'source_table_name'"
     * id columns → "DEFAULT: UUID()" or "DEFAULT: ROW_NUMBER() OVER (ORDER BY ...)"
     * audit columns (created_by, etc.) → "DEFAULT: 'SYSTEM'"
     * numeric columns → "DEFAULT: 0"
     * string columns → "DEFAULT: 'UNKNOWN'"

   For all modes:
   - Map each source column to appropriate target column(s)
   - Consider: exact name match, similar names, data types, business meaning
   - NEVER use null for source_column or source_type

3. TYPE CONVERSION:
   - Identify where source and target types differ
   - Note if safe (STRING→STRING) or needs casting (STRING→INT64)

4. VALIDATION RULES:
   Generate rules based on:
   - Target column mode (REQUIRED → NOT_NULL rule)
   - Data type constraints (INTEGER/FLOAT → NUMERIC rule)
   - Reasonable ranges (year: 1900-2100, percentage: 0-100)
   - ID fields should have uniqueness

5. PRIMARY KEYS:
   - Identify likely primary keys (columns with "id", "code", "key")
   - Note composite keys if needed

OUTPUT: Call submit_schema_mapping with a VALID JSON STRING (not Python dict syntax).

CRITICAL JSON FORMATTING RULES:
- Use "true"/"false" NOT "True"/"False"
- Use "null" NOT "None"
- Use double quotes for all strings
- NEVER wrap JSON in Python variables (NO `mapping_json = ...`)
- NEVER use Python functions (NO `print()`, `json.dumps()`, etc.)
- NO Python code whatsoever - provide pure JSON string only
- NO comments in JSON (no # or //)
- Call submit_schema_mapping with ONLY the JSON string, nothing else

JSON structure:

{{
  "metadata": {{
    "source_dataset": "{project_id}.{source_dataset}",
    "target_dataset": "{project_id}.{target_dataset}",
    "generated_at": "2025-12-16T00:00:00Z",
    "confidence": "high",
    "mode": "{mode}"
  }},
  "mappings": [
    {{
      "source_table": "{source_dataset}.table_name",
      "target_table": "{target_dataset}.table_name",
      "match_confidence": 0.95,
      "column_mappings": [
        {{
          "source_column": "col1",
          "target_column": "col1",
          "source_type": "STRING",
          "target_type": "STRING",
          "type_conversion_needed": false,
          "transformation": null,
          "notes": "Direct mapping"
        }},
        {{
          "source_column": "GENERATED",
          "target_column": "loaded_at",
          "source_type": "EXPRESSION",
          "target_type": "TIMESTAMP",
          "type_conversion_needed": false,
          "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
          "notes": "Auto-generated timestamp for audit purposes"
        }}
      ],
      "unmapped_source_columns": [],
      "unmapped_target_columns": [],
      "mapping_errors": [
        {{
          "error_type": "UNMAPPED_TARGET_COLUMN",
          "target_column": "column_name",
          "severity": "WARNING",
          "message": "Description of issue"
        }}
      ],
      "validation_rules": [
        {{
          "column": "col1",
          "type": "NOT_NULL",
          "reason": "Target column is REQUIRED"
        }}
      ],
      "primary_key": ["col1"],
      "uniqueness_constraints": ["col1"]
    }}
  ]
}}

Call the submit_schema_mapping function with the complete mapping JSON now.
"""

    print("Calling Gemini 2.0 Flash to generate schema mapping...")

    # Generate content with function calling
    chat = model.start_chat()
    response = chat.send_message(prompt)

    # Extract function call
    if response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                func_call = part.function_call
                if func_call.name == "submit_schema_mapping":
                    mapping_json_str = func_call.args["mapping_json"]

                    # Parse and validate JSON
                    try:
                        mapping_data = json.loads(mapping_json_str)
                        print("✓ LLM generated valid mapping JSON")
                        return mapping_data
                    except json.JSONDecodeError as e:
                        print(f"✗ LLM generated invalid JSON: {e}")
                        return {"error": f"Invalid JSON: {e}"}

    # If no function call, try to extract JSON from text
    print("⚠ No function call found, trying to extract JSON from response text...")
    response_text = response.text

    # Try to find JSON in response
    if "{" in response_text and "}" in response_text:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        json_str = response_text[start:end]
        try:
            mapping_data = json.loads(json_str)
            return mapping_data
        except:
            pass

    return {"error": "Failed to extract mapping from LLM response", "response": response_text}


# --- 3. MAIN EXECUTION FUNCTION ---
def generate_schema_mapping(
    source_dataset: str,
    target_dataset: str,
    output_file: str = "schema_mapping_output.json",
    mode: str = "REPORT"
) -> dict:
    """
    Generate schema mapping between source and target BigQuery datasets.

    Args:
        source_dataset: Source dataset ID (e.g., "worldbank_staging_dataset")
        target_dataset: Target dataset ID (e.g., "worldbank_target_dataset")
        output_file: Path to save output JSON
        mode: "REPORT" to flag unmapped columns, "FIX" to suggest defaults

    Returns:
        Dictionary with mapping results
    """
    print(f"\n{'='*60}")
    print("SCHEMA MAPPING AGENT")
    print(f"{'='*60}")
    print(f"Source Dataset: {source_dataset}")
    print(f"Target Dataset: {target_dataset}")
    print(f"Output File: {output_file}")
    print(f"Mode: {mode}")
    print(f"Model: Gemini 2.5 Flash")
    print(f"{'='*60}\n")

    # Step 1: Fetch schemas from BigQuery
    print("Step 1: Fetching source dataset schemas...")
    source_schemas = fetch_dataset_schemas(source_dataset)
    if "error" in source_schemas:
        print(f"✗ Error fetching source schemas: {source_schemas['error']}")
        return {"status": "error", "message": source_schemas['error']}
    print(f"✓ Found {len(source_schemas)} source tables\n")

    print("Step 2: Fetching target dataset schemas...")
    target_schemas = fetch_dataset_schemas(target_dataset)
    if "error" in target_schemas:
        print(f"✗ Error fetching target schemas: {target_schemas['error']}")
        return {"status": "error", "message": target_schemas['error']}
    print(f"✓ Found {len(target_schemas)} target tables\n")

    # Step 2: Generate mapping with LLM
    print("Step 3: Generating schema mapping with Gemini...\n")

    mapping_data = generate_schema_mapping_with_llm(
        source_schemas,
        target_schemas,
        source_dataset,
        target_dataset,
        mode
    )

    if "error" in mapping_data:
        print(f"\n✗ Failed to generate mapping: {mapping_data['error']}")
        return {"status": "error", "message": mapping_data['error']}

    # Step 3: Save output
    # Handle absolute paths (for API usage) and relative paths (for CLI usage)
    if os.path.isabs(output_file):
        output_path = output_file
    else:
        output_path = os.path.join(os.getcwd(), "agents/schema_mapping", output_file)

    with open(output_path, "w") as f:
        json.dump(mapping_data, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ Schema mapping saved to: {output_file}")
    print(f"{'='*60}\n")

    # Print summary
    num_mappings = len(mapping_data.get("mappings", []))
    print(f"Summary:")
    print(f"  - Tables mapped: {num_mappings}")
    for mapping in mapping_data.get("mappings", []):
        num_cols = len(mapping.get("column_mappings", []))
        num_rules = len(mapping.get("validation_rules", []))
        print(f"  - {mapping.get('source_table', 'unknown')} → {mapping.get('target_table', 'unknown')}")
        print(f"    Columns: {num_cols}, Rules: {num_rules}")

    return {"status": "success", "mapping": mapping_data, "output_file": output_path}


if __name__ == "__main__":
    # Example usage
    result = generate_schema_mapping(
        source_dataset="worldbank_staging_dataset",
        target_dataset="worldbank_target_dataset",
        output_file="worldbank_schema_mapping.json"
    )

    if result.get("status") == "success":
        print("\n✅ Schema mapping completed successfully!")
    else:
        print(f"\n❌ Schema mapping failed: {result.get('message')}")
