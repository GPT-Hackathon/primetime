#!/usr/bin/env python3
"""
Data Validation Agent - Validates BigQuery staging data based on schema mapping rules.

Uses LLM (Gemini 2.5 Flash) to generate SQL validation queries from mapping rules.
Stores validation errors in staging_errors table.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List
from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel, FunctionDeclaration, Tool
import vertexai

# Global variables - will be initialized in validate_schema_mapping
project_id = None
bq_client = None


def create_staging_errors_table(dataset_id: str) -> None:
    """
    Create staging_errors table if it doesn't exist.

    Schema:
    - run_id: STRING (GUID for this validation run)
    - source_table: STRING
    - target_table: STRING
    - error_message: STRING
    - error_type: STRING (UNIQUENESS, NOT_NULL, TYPE_CONVERSION, RANGE, etc.)
    - failed_column: STRING
    - row_count: INTEGER (number of rows with this error)
    - created_at: TIMESTAMP
    """
    full_table_id = f"{project_id}.{dataset_id}.staging_errors"

    schema = [
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_table", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_table", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("error_message", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("error_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("failed_column", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("row_count", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    try:
        table = bigquery.Table(full_table_id, schema=schema)
        table = bq_client.create_table(table, exists_ok=True)
        print(f"✓ Ensured staging_errors table exists: {full_table_id}")
    except Exception as e:
        print(f"✗ Error creating staging_errors table: {e}")
        raise


def generate_validation_sql_with_llm(
    source_table: str,
    target_table: str,
    column_mappings: List[Dict],
    validation_rules: List[Dict],
    unmapped_target_columns: List[str],
    primary_key: List[str],
    uniqueness_constraints: List[str]
) -> List[Dict]:
    """
    Use Gemini to generate SQL validation queries based on mapping rules.

    Returns:
        List of validation queries with metadata
    """

    # Define function for structured output
    submit_validation_func = FunctionDeclaration(
        name="submit_validation_queries",
        description="Submit generated SQL validation queries",
        parameters={
            "type": "object",
            "properties": {
                "queries_json": {
                    "type": "string",
                    "description": "JSON array of validation query objects"
                }
            },
            "required": ["queries_json"]
        }
    )

    validation_tool = Tool(function_declarations=[submit_validation_func])

    model = GenerativeModel(
        "gemini-2.5-flash",
        tools=[validation_tool]
    )

    prompt = f"""
You are a Senior Data Quality Engineer. Generate BigQuery SQL validation queries to check data quality issues.

SOURCE TABLE: {source_table}
TARGET TABLE: {target_table}

COLUMN MAPPINGS:
{json.dumps(column_mappings, indent=2)}

VALIDATION RULES:
{json.dumps(validation_rules, indent=2)}

PRIMARY KEY: {primary_key}
UNIQUENESS CONSTRAINTS: {uniqueness_constraints}
UNMAPPED TARGET COLUMNS: {unmapped_target_columns}

TASK: Generate SQL queries to validate data quality. Each query should return a count of rows with issues.

REQUIRED VALIDATIONS:

1. **UNIQUENESS CHECKS** (for primary keys and unique constraints):
   - Generate query to find duplicate rows based on primary key columns
   - Example SQL pattern:
     ```sql
     SELECT COUNT(*) as error_count
     FROM (
       SELECT column1, column2, COUNT(*) as cnt
       FROM `{source_table}`
       GROUP BY column1, column2
       HAVING COUNT(*) > 1
     )
     ```

2. **NOT_NULL CHECKS** (from validation_rules):
   - For each NOT_NULL rule, generate query to count NULL values
   - Example:
     ```sql
     SELECT COUNT(*) as error_count
     FROM `{source_table}`
     WHERE column_name IS NULL
     ```

3. **TYPE_CONVERSION CHECKS** (from column_mappings where type_conversion_needed=true):
   - Check if values can be safely converted to target type
   - Example for STRING to INTEGER:
     ```sql
     SELECT COUNT(*) as error_count
     FROM `{source_table}`
     WHERE column_name IS NOT NULL
       AND SAFE_CAST(column_name AS INT64) IS NULL
     ```

4. **RANGE CHECKS** (from validation_rules with type="RANGE"):
   - Validate values are within expected ranges
   - Example:
     ```sql
     SELECT COUNT(*) as error_count
     FROM `{source_table}`
     WHERE column_name IS NOT NULL
       AND (column_name < min_value OR column_name > max_value)
     ```

5. **NUMERIC CHECKS** (from validation_rules with type="NUMERIC"):
   - Ensure numeric columns contain valid numbers
   - Example:
     ```sql
     SELECT COUNT(*) as error_count
     FROM `{source_table}`
     WHERE column_name IS NOT NULL
       AND SAFE_CAST(column_name AS FLOAT64) IS NULL
     ```

OUTPUT FORMAT: Call submit_validation_queries with a JSON string containing an array of query objects.

Each query object must have:
- error_type: One of ["UNIQUENESS", "NOT_NULL", "TYPE_CONVERSION", "RANGE", "NUMERIC"]
- failed_column: Column name being validated (or comma-separated list for composite keys)
- sql_query: Complete BigQuery SQL query that returns a single column "error_count"
- error_message: Human-readable description of what this validation checks

Example output structure:
[
  {{
    "error_type": "UNIQUENESS",
    "failed_column": "country_code,year",
    "sql_query": "SELECT COUNT(*) as error_count FROM (SELECT country_code, year, COUNT(*) as cnt FROM `{source_table}` GROUP BY country_code, year HAVING COUNT(*) > 1)",
    "error_message": "Duplicate rows found for primary key (country_code, year)"
  }},
  {{
    "error_type": "NOT_NULL",
    "failed_column": "country_code",
    "sql_query": "SELECT COUNT(*) as error_count FROM `{source_table}` WHERE country_code IS NULL",
    "error_message": "NULL values found in required column country_code"
  }}
]

CRITICAL RULES:
- Each SQL query MUST return exactly one column named "error_count"
- Use fully qualified table names with backticks: `{source_table}`
- Use SAFE_CAST for type conversions to avoid errors
- Only generate queries for rules that apply to the SOURCE table (not target)
- Provide pure JSON string only - NO Python code, NO comments
- Use "true"/"false" NOT "True"/"False"
- Use "null" NOT "None"

Generate validation queries now.
"""

    try:
        response = model.generate_content(prompt)

        # First check for function call (before accessing .text which may throw)
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    func_call = part.function_call
                    if func_call.name == "submit_validation_queries":
                        queries_json = func_call.args.get("queries_json", "")
                        try:
                            queries = json.loads(queries_json)
                            return queries
                        except json.JSONDecodeError as e:
                            print(f"✗ Failed to parse LLM JSON response: {e}")
                            print(f"Response: {queries_json[:500]}")
                            return []

        # Fallback: try to extract JSON from text response
        try:
            response_text = response.text
        except Exception:
            print(f"✗ No text response and no valid function call found")
            return []

        if '{' in response_text and '[' in response_text:
            json_start = response_text.index('[')
            json_end = response_text.rindex(']') + 1
            json_str = response_text[json_start:json_end]
            try:
                queries = json.loads(json_str)
                return queries
            except:
                pass

        print(f"✗ Failed to extract validation queries from LLM response")
        print(f"Response: {response_text[:500]}")
        return []

    except Exception as e:
        print(f"✗ LLM query generation failed: {e}")
        return []


def execute_validation_query(query_obj: Dict, source_table: str, target_table: str, run_id: str, dataset_id: str, mode: str) -> int:
    """
    Execute a validation SQL query and log errors to staging_errors table.

    Returns:
        Number of errors found
    """
    sql_query = query_obj.get("sql_query", "")
    error_type = query_obj.get("error_type", "UNKNOWN")
    failed_column = query_obj.get("failed_column", "")
    error_message = query_obj.get("error_message", "Validation error")

    try:
        # Execute the validation query
        query_job = bq_client.query(sql_query)
        results = list(query_job.result())

        if not results or len(results) == 0:
            return 0

        error_count = results[0].error_count if hasattr(results[0], 'error_count') else 0

        if error_count > 0:
            # Log to staging_errors table
            errors_table = f"{project_id}.{dataset_id}.staging_errors"

            insert_query = f"""
            INSERT INTO `{errors_table}`
            (run_id, source_table, target_table, error_message, error_type, failed_column, row_count, created_at)
            VALUES (
                '{run_id}',
                '{source_table}',
                '{target_table}',
                '{error_message}',
                '{error_type}',
                {'NULL' if not failed_column else f"'{failed_column}'"},
                {error_count},
                CURRENT_TIMESTAMP()
            )
            """

            bq_client.query(insert_query).result()
            print(f"  ✗ {error_type}: {error_count} row(s) - {error_message}")

            return error_count
        else:
            print(f"  ✓ {error_type}: No issues found")
            return 0

    except Exception as e:
        print(f"  ✗ Query execution failed for {error_type}: {e}")
        print(f"  SQL: {sql_query[:200]}")
        return 0


def validate_table_mapping(
    mapping: Dict,
    source_dataset: str,
    run_id: str,
    mode: str = "REPORT"
) -> Dict:
    """
    Validate a single table mapping using LLM-generated SQL queries.

    Args:
        mapping: Schema mapping object for one table
        source_dataset: Source dataset name (e.g., "worldbank_staging_dataset")
        run_id: Unique identifier for this validation run
        mode: "REPORT" to log errors, "FIX" to attempt corrections (not implemented)

    Returns:
        Validation results dict
    """
    source_table = mapping.get("source_table", "")
    target_table = mapping.get("target_table", "")
    column_mappings = mapping.get("column_mappings", [])
    validation_rules = mapping.get("validation_rules", [])
    unmapped_target_columns = mapping.get("unmapped_target_columns", [])
    primary_key = mapping.get("primary_key", [])
    uniqueness_constraints = mapping.get("uniqueness_constraints", [])

    # Extract dataset from source_table (format: project.dataset.table)
    if '.' in source_table:
        dataset_id = source_table.split('.')[1]
    else:
        dataset_id = source_dataset

    print(f"\n{'='*60}")
    print(f"Validating: {source_table} → {target_table}")
    print(f"{'='*60}")
    print(f"Column mappings: {len(column_mappings)}")
    print(f"Validation rules: {len(validation_rules)}")
    print(f"Primary key: {primary_key}")
    print(f"Uniqueness constraints: {uniqueness_constraints}")

    # Generate validation SQL queries using LLM
    print("\n🤖 Generating validation queries with Gemini...")
    queries = generate_validation_sql_with_llm(
        source_table=source_table,
        target_table=target_table,
        column_mappings=column_mappings,
        validation_rules=validation_rules,
        unmapped_target_columns=unmapped_target_columns,
        primary_key=primary_key,
        uniqueness_constraints=uniqueness_constraints
    )

    if not queries:
        print("⚠ No validation queries generated")
        return {
            "source_table": source_table,
            "target_table": target_table,
            "total_errors": 0,
            "validations_run": 0,
            "status": "no_queries"
        }

    print(f"✓ Generated {len(queries)} validation queries\n")

    # Execute each validation query
    total_errors = 0
    for idx, query_obj in enumerate(queries, 1):
        print(f"[{idx}/{len(queries)}] Running {query_obj.get('error_type')} check...")
        error_count = execute_validation_query(
            query_obj=query_obj,
            source_table=source_table,
            target_table=target_table,
            run_id=run_id,
            dataset_id=dataset_id,
            mode=mode
        )
        total_errors += error_count

    return {
        "source_table": source_table,
        "target_table": target_table,
        "total_errors": total_errors,
        "validations_run": len(queries),
        "status": "success"
    }


def validate_schema_mapping(
    schema_mapping_json: str,
    source_dataset: str,
    mode: str = "REPORT"
) -> Dict:
    """
    Validate all table mappings from schema mapping JSON.

    Args:
        schema_mapping_json: Path to schema mapping JSON file OR JSON string
        source_dataset: Source dataset name (e.g., "worldbank_staging_dataset")
        mode: "REPORT" or "FIX"

    Returns:
        Validation summary dict
    """
    global project_id, bq_client

    # Initialize BigQuery client with project ID from environment
    if project_id is None:
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            return {"status": "error", "message": "GCP_PROJECT_ID environment variable not set"}

    if bq_client is None:
        bq_client = bigquery.Client(project=project_id)

    print(f"\n{'='*60}")
    print("DATA VALIDATION AGENT")
    print(f"{'='*60}")
    print(f"Project: {project_id}")
    print(f"Source Dataset: {source_dataset}")
    print(f"Mode: {mode}")
    print(f"Model: Gemini 2.5 Flash")
    print(f"{'='*60}\n")

    # Load schema mapping
    try:
        if os.path.isfile(schema_mapping_json):
            with open(schema_mapping_json, 'r') as f:
                mapping_data = json.load(f)
        else:
            mapping_data = json.loads(schema_mapping_json)
    except Exception as e:
        print(f"✗ Failed to load schema mapping: {e}")
        return {"status": "error", "message": str(e)}

    # Extract mappings (handle both API response format and direct mapping format)
    if "mapping" in mapping_data and "mappings" in mapping_data["mapping"]:
        # API response format
        mappings = mapping_data["mapping"]["mappings"]
    elif "mappings" in mapping_data:
        # Direct mapping format
        mappings = mapping_data["mappings"]
    else:
        print(f"✗ Invalid schema mapping format - missing 'mappings' key")
        return {"status": "error", "message": "Invalid schema mapping format"}

    print(f"Loaded {len(mappings)} table mapping(s)")

    # Extract dataset from first source table if not provided
    if not source_dataset and mappings:
        first_source = mappings[0].get("source_table", "")
        if '.' in first_source:
            source_dataset = first_source.split('.')[1]

    # Create staging_errors table
    print(f"\nCreating/verifying staging_errors table in {source_dataset}...")
    create_staging_errors_table(source_dataset)

    # Generate unique run ID
    run_id = str(uuid.uuid4())
    print(f"\nValidation Run ID: {run_id}\n")

    # Validate each table mapping
    results = []
    total_errors_all = 0
    total_validations = 0

    for idx, mapping in enumerate(mappings, 1):
        print(f"\n[{idx}/{len(mappings)}] Processing table mapping...")

        result = validate_table_mapping(
            mapping=mapping,
            source_dataset=source_dataset,
            run_id=run_id,
            mode=mode
        )

        results.append(result)
        total_errors_all += result.get("total_errors", 0)
        total_validations += result.get("validations_run", 0)

    # Print summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Run ID: {run_id}")
    print(f"Tables Validated: {len(results)}")
    print(f"Total Validations Run: {total_validations}")
    print(f"Total Errors Found: {total_errors_all}")
    print(f"\nErrors logged to: {project_id}.{source_dataset}.staging_errors")
    print(f"Filter by run_id: {run_id}")
    print(f"{'='*60}\n")

    return {
        "status": "success",
        "run_id": run_id,
        "tables_validated": len(results),
        "total_validations": total_validations,
        "total_errors": total_errors_all,
        "results": results
    }


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    # Get project ID
    proj_id = os.getenv("GCP_PROJECT_ID")
    if not proj_id:
        print("Error: GCP_PROJECT_ID environment variable not set")
        sys.exit(1)

    # Initialize Vertex AI
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    vertexai.init(project=proj_id, location=location)

    if len(sys.argv) < 3:
        print("Usage: python data_validator.py <schema_mapping_json_file> <source_dataset> [mode]")
        print("Example: python data_validator.py worldbank_mapping.json worldbank_staging_dataset REPORT")
        sys.exit(1)

    schema_mapping_file = sys.argv[1]
    source_dataset = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "REPORT"

    result = validate_schema_mapping(
        schema_mapping_json=schema_mapping_file,
        source_dataset=source_dataset,
        mode=mode
    )

    if result.get("status") == "success":
        sys.exit(0)
    else:
        sys.exit(1)
