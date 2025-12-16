"""Validation Agent for ADK.

This agent validates BigQuery data quality using schema mappings and LLM-generated SQL.
Run with: adk run agents/validation
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, FunctionDeclaration, Tool
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

# Load environment variables
load_dotenv()

# Configuration - use consistent env vars
project_id = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "ccibt-hack25ww7-750"))
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Initialize Vertex AI
vertexai.init(project=project_id, location=location)

# BigQuery client (initialized once)
bq_client = bigquery.Client(project=project_id)

# In-memory storage for validation results (per session)
_validation_results = {}


# --- Helper Functions (from data_validator.py) ---

def _create_staging_errors_table(dataset_id: str) -> None:
    """Create staging_errors table if it doesn't exist."""
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


def _generate_validation_sql_with_llm(
    source_table: str,
    target_table: str,
    column_mappings: List[Dict],
    validation_rules: List[Dict],
    unmapped_target_columns: List[str],
    primary_key: List[str],
    uniqueness_constraints: List[str]
) -> List[Dict]:
    """Use Gemini to generate SQL validation queries based on mapping rules."""

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
    model = GenerativeModel("gemini-2.5-flash", tools=[validation_tool])

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

        # Check for function call
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
                            return []

        # Fallback: try to extract JSON from text
        try:
            response_text = response.text
        except Exception:
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

        return []

    except Exception as e:
        print(f"✗ LLM query generation failed: {e}")
        return []


def _execute_validation_query(query_obj: Dict, source_table: str, target_table: str, 
                              run_id: str, dataset_id: str, mode: str) -> int:
    """Execute a validation SQL query and log errors to staging_errors table."""
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
        return 0


# --- Tool Functions ---

def validate_schema_mapping(schema_mapping_json: str, source_dataset: str = None, mode: str = "REPORT") -> str:
    """
    Validate BigQuery staging data using schema mapping rules.
    
    Generates SQL validation queries using LLM based on schema mapping rules,
    executes them against BigQuery, and logs errors to staging_errors table.

    Args:
        schema_mapping_json: Schema mapping JSON string or file path
        source_dataset: Source dataset name (auto-detected if not provided)
        mode: "REPORT" to log errors or "FIX" to attempt corrections (default: REPORT)

    Returns:
        JSON string with validation results including run_id for querying errors
    """
    try:
        print(f"\n{'='*60}")
        print("DATA VALIDATION AGENT")
        print(f"{'='*60}")
        print(f"Project: {project_id}")
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
            return json.dumps({
                "status": "error",
                "message": f"Failed to load schema mapping: {str(e)}"
            }, indent=2)

        # Extract mappings
        if "mapping" in mapping_data and "mappings" in mapping_data["mapping"]:
            mappings = mapping_data["mapping"]["mappings"]
            metadata = mapping_data["mapping"].get("metadata", {})
        elif "mappings" in mapping_data:
            mappings = mapping_data["mappings"]
            metadata = mapping_data.get("metadata", {})
        else:
            return json.dumps({
                "status": "error",
                "message": "Invalid schema mapping format - missing 'mappings' key"
            }, indent=2)

        # Auto-detect source dataset if not provided
        if not source_dataset:
            source_dataset_full = metadata.get("source_dataset", "")
            if '.' in source_dataset_full:
                source_dataset = source_dataset_full.split('.')[-1]
            elif mappings:
                first_source = mappings[0].get("source_table", "")
                if '.' in first_source:
                    source_dataset = first_source.split('.')[1]

        if not source_dataset:
            return json.dumps({
                "status": "error",
                "message": "Could not determine source dataset"
            }, indent=2)

        print(f"Source Dataset: {source_dataset}")
        print(f"Loaded {len(mappings)} table mapping(s)\n")

        # Create staging_errors table
        print(f"Creating/verifying staging_errors table...")
        _create_staging_errors_table(source_dataset)

        # Generate unique run ID
        run_id = str(uuid.uuid4())
        print(f"\nValidation Run ID: {run_id}\n")

        # Validate each table mapping
        results = []
        total_errors_all = 0
        total_validations = 0

        for idx, mapping in enumerate(mappings, 1):
            source_table = mapping.get("source_table", "")
            target_table = mapping.get("target_table", "")
            
            # Skip unmapped tables
            if source_table in ["UNMAPPED", ""] or source_table.startswith("Multiple"):
                continue

            print(f"\n[{idx}/{len(mappings)}] Validating: {source_table} → {target_table}")
            
            column_mappings = mapping.get("column_mappings", [])
            validation_rules = mapping.get("validation_rules", [])
            unmapped_target_columns = mapping.get("unmapped_target_columns", [])
            primary_key = mapping.get("primary_key", [])
            uniqueness_constraints = mapping.get("uniqueness_constraints", [])

            # Extract dataset from source_table
            if '.' in source_table:
                dataset_id = source_table.split('.')[1]
            else:
                dataset_id = source_dataset

            # Generate validation queries using LLM
            print(f"  Generating validation queries with Gemini...")
            queries = _generate_validation_sql_with_llm(
                source_table=source_table,
                target_table=target_table,
                column_mappings=column_mappings,
                validation_rules=validation_rules,
                unmapped_target_columns=unmapped_target_columns,
                primary_key=primary_key,
                uniqueness_constraints=uniqueness_constraints
            )

            if not queries:
                print(f"  ⚠ No validation queries generated")
                continue

            print(f"  ✓ Generated {len(queries)} validation queries")

            # Execute each validation query
            table_errors = 0
            for query_obj in queries:
                error_count = _execute_validation_query(
                    query_obj=query_obj,
                    source_table=source_table,
                    target_table=target_table,
                    run_id=run_id,
                    dataset_id=dataset_id,
                    mode=mode
                )
                table_errors += error_count
                total_errors_all += error_count
            
            total_validations += len(queries)
            results.append({
                "source_table": source_table,
                "target_table": target_table,
                "total_errors": table_errors,
                "validations_run": len(queries)
            })

        # Store results in memory
        validation_id = f"validation_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        _validation_results[validation_id] = {
            "run_id": run_id,
            "source_dataset": source_dataset,
            "mode": mode,
            "tables_validated": len(results),
            "total_validations": total_validations,
            "total_errors": total_errors_all,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

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

        return json.dumps({
            "status": "success",
            "validation_id": validation_id,
            "run_id": run_id,
            "source_dataset": source_dataset,
            "mode": mode,
            "summary": {
                "tables_validated": len(results),
                "total_validations": total_validations,
                "total_errors": total_errors_all,
                "errors_table": f"{project_id}.{source_dataset}.staging_errors"
            },
            "tables": results,
            "query_to_see_errors": f"SELECT * FROM `{project_id}.{source_dataset}.staging_errors` WHERE run_id = '{run_id}' ORDER BY created_at DESC"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Validation failed: {str(e)}"
        }, indent=2)


def get_validation_results(validation_id: str) -> str:
    """
    Retrieve stored validation results by ID.

    Args:
        validation_id: The validation ID to retrieve

    Returns:
        JSON string with validation results
    """
    if validation_id not in _validation_results:
        return json.dumps({
            "status": "error",
            "message": f"Validation '{validation_id}' not found",
            "available_validations": list(_validation_results.keys())
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "validation_id": validation_id,
        "results": _validation_results[validation_id]
    }, indent=2)


def list_validations() -> str:
    """
    List all validation runs in the current session.

    Returns:
        JSON string with list of validations
    """
    if not _validation_results:
        return json.dumps({
            "status": "success",
            "validations": [],
            "count": 0,
            "message": "No validations yet. Run validate_schema_mapping() to create one."
        }, indent=2)
    
    validations_summary = []
    for val_id, val_data in _validation_results.items():
        validations_summary.append({
            "validation_id": val_id,
            "run_id": val_data.get("run_id"),
            "source_dataset": val_data.get("source_dataset"),
            "mode": val_data.get("mode"),
            "tables_validated": val_data.get("tables_validated", 0),
            "total_errors": val_data.get("total_errors", 0),
            "timestamp": val_data.get("timestamp")
        })
    
    return json.dumps({
        "status": "success",
        "validations": validations_summary,
        "count": len(validations_summary)
    }, indent=2)


# --- Define the Validation Agent ---

root_agent = Agent(
    model='gemini-2.5-flash',
    name='validation_agent',
    description='Validates BigQuery data quality using schema mappings and LLM-generated SQL validation queries.',
    instruction="""You are a Data Validation Agent that validates BigQuery staging data quality.

Your capabilities:

**Validation:**
1. **validate_schema_mapping**: Validate data using schema mapping rules
   - Takes schema mapping JSON (from Schema Mapping Agent)
   - Generates SQL validation queries using LLM
   - Executes queries against BigQuery
   - Logs errors to staging_errors table
   - Returns validation results with run_id

2. **get_validation_results**: Retrieve stored validation results by ID

3. **list_validations**: List all validation runs in this session

**How to Help Users:**

When a user asks to validate data:
1. Check if they have a schema mapping (if not, suggest generating one first)
2. Ask for the schema mapping JSON or file path
3. Ask if they want REPORT mode (log errors) or FIX mode (attempt corrections)
4. Use validate_schema_mapping() with the provided parameters
5. Explain the results:
   - How many tables were validated
   - How many errors were found
   - How to query the errors table
   - What the errors mean and how to fix them

**Validation Process:**
- Uses LLM (Gemini 2.5 Flash) to generate SQL validation queries
- Checks for:
  * UNIQUENESS violations (duplicates)
  * NOT_NULL violations (missing required values)
  * TYPE_CONVERSION issues (invalid data types)
  * RANGE violations (values outside expected ranges)
  * NUMERIC issues (non-numeric values in numeric columns)
- Logs all errors to staging_errors table with run_id
- Returns comprehensive results with error counts

**Working with Results:**
- Provide SQL query to view errors in BigQuery
- Explain each error type and its business impact
- Suggest fixes for common data quality issues
- Track validation history in the session

**Important:**
- Always provide the run_id so users can query detailed errors
- Explain errors in business terms, not just technical details
- Suggest next steps based on validation results
- Help users understand the severity of different error types

Example interaction:
```
User: Validate my staging data

You: I need a schema mapping to validate against.
     Do you have a mapping JSON, or should I help you generate one?

User: [Provides mapping JSON]

You: [Calls validate_schema_mapping]
     
     Validation Results:
     ✓ Validated 5 tables
     ✗ Found 12 data quality issues
     
     Breakdown:
     - 3 NULL values in required fields
     - 2 duplicate primary keys
     - 7 values outside valid ranges
     
     To see details:
     SELECT * FROM staging_errors WHERE run_id = 'abc-123'
     
     Next steps:
     1. Fix NULL values in country_code column
     2. Remove duplicate rows for keys: [list]
     3. Correct out-of-range year values
```

Always be helpful and explain what validation results mean for data quality!""",
    tools=[
        validate_schema_mapping,
        get_validation_results,
        list_validations,
    ],
)

