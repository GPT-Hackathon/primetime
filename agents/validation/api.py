#!/usr/bin/env python3
"""
Data Validation Agent REST API

Flask-based REST API for validating BigQuery staging data based on schema mapping rules.
Designed for deployment on Google Cloud Run.

Endpoints:
    POST /validate - Validate staging data based on schema mapping JSON
    GET /health - Health check endpoint
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel, FunctionDeclaration, Tool
import vertexai

app = Flask(__name__)

# Global variables
project_id = None
bq_client = None
initialized = False


def init_services():
    """Initialize GCP services (Vertex AI and BigQuery)."""
    global project_id, bq_client, initialized

    if initialized:
        return True

    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        return False

    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    try:
        vertexai.init(project=project_id, location=location)
        bq_client = bigquery.Client(project=project_id)
        initialized = True
        return True
    except Exception as e:
        print(f"Failed to initialize services: {e}")
        return False


def create_staging_errors_table(dataset_id: str) -> Dict:
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
        return {"success": True, "table_id": full_table_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_validation_sql_with_llm(
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

Generate validation queries now.
"""

    try:
        response = model.generate_content(prompt)

        # First check for function call
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    func_call = part.function_call
                    if func_call.name == "submit_validation_queries":
                        queries_json = func_call.args.get("queries_json", "")
                        try:
                            queries = json.loads(queries_json)
                            return queries
                        except json.JSONDecodeError:
                            return []

        # Fallback: try to extract JSON from text response
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
        print(f"LLM query generation failed: {e}")
        return []


def execute_validation_query(
    query_obj: Dict,
    source_table: str,
    target_table: str,
    run_id: str,
    dataset_id: str,
    mode: str
) -> Dict:
    """Execute a validation SQL query and return results."""
    sql_query = query_obj.get("sql_query", "")
    error_type = query_obj.get("error_type", "UNKNOWN")
    failed_column = query_obj.get("failed_column", "")
    error_message = query_obj.get("error_message", "Validation error")

    result = {
        "error_type": error_type,
        "failed_column": failed_column,
        "error_message": error_message,
        "error_count": 0,
        "status": "success",
        "logged_to_table": False
    }

    try:
        query_job = bq_client.query(sql_query)
        results = list(query_job.result())

        if not results or len(results) == 0:
            return result

        error_count = results[0].error_count if hasattr(results[0], 'error_count') else 0
        result["error_count"] = error_count

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
            result["logged_to_table"] = True

        return result

    except Exception as e:
        result["status"] = "error"
        result["error_details"] = str(e)
        return result


def validate_table_mapping(
    mapping: Dict,
    source_dataset: str,
    run_id: str,
    mode: str = "REPORT"
) -> Dict:
    """Validate a single table mapping using LLM-generated SQL queries."""
    source_table = mapping.get("source_table", "")
    target_table = mapping.get("target_table", "")
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

    result = {
        "source_table": source_table,
        "target_table": target_table,
        "column_mappings_count": len(column_mappings),
        "validation_rules_count": len(validation_rules),
        "primary_key": primary_key,
        "validations": [],
        "total_errors": 0,
        "validations_run": 0,
        "status": "success"
    }

    # Generate validation SQL queries using LLM
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
        result["status"] = "no_queries_generated"
        return result

    result["validations_run"] = len(queries)

    # Execute each validation query
    for query_obj in queries:
        validation_result = execute_validation_query(
            query_obj=query_obj,
            source_table=source_table,
            target_table=target_table,
            run_id=run_id,
            dataset_id=dataset_id,
            mode=mode
        )
        result["validations"].append(validation_result)
        result["total_errors"] += validation_result.get("error_count", 0)

    return result


def validate_schema_mapping(
    schema_mapping_json: str,
    source_dataset: str,
    mode: str = "REPORT"
) -> Dict:
    """Validate all table mappings from schema mapping JSON."""

    if not init_services():
        return {
            "status": "error",
            "message": "Failed to initialize GCP services. Check GCP_PROJECT_ID environment variable."
        }

    response = {
        "status": "success",
        "message": None,
        "run_id": str(uuid.uuid4()),
        "project_id": project_id,
        "source_dataset": source_dataset,
        "mode": mode,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "completed_at": None,
        "summary": {
            "tables_validated": 0,
            "total_validations_run": 0,
            "total_errors_found": 0,
            "tables_with_errors": 0,
            "tables_skipped": 0
        },
        "table_results": [],
        "errors_table": None
    }

    # Parse schema mapping
    try:
        if isinstance(schema_mapping_json, str):
            mapping_data = json.loads(schema_mapping_json)
        else:
            mapping_data = schema_mapping_json
    except json.JSONDecodeError as e:
        response["status"] = "error"
        response["message"] = f"Invalid JSON: {str(e)}"
        return response

    # Extract mappings
    if "mapping" in mapping_data and "mappings" in mapping_data["mapping"]:
        mappings = mapping_data["mapping"]["mappings"]
    elif "mappings" in mapping_data:
        mappings = mapping_data["mappings"]
    else:
        response["status"] = "error"
        response["message"] = "Invalid schema mapping format - missing 'mappings' key"
        return response

    # Extract dataset from first source table if not provided
    if not source_dataset and mappings:
        first_source = mappings[0].get("source_table", "")
        if '.' in first_source:
            source_dataset = first_source.split('.')[1]

    # Create staging_errors table
    table_result = create_staging_errors_table(source_dataset)
    if not table_result["success"]:
        response["status"] = "error"
        response["message"] = f"Failed to create staging_errors table: {table_result.get('error')}"
        return response

    response["errors_table"] = table_result["table_id"]

    # Validate each table mapping
    for mapping in mappings:
        source_table = mapping.get("source_table", "")

        # Skip unmapped or multi-table sources
        if source_table in ["UNMAPPED", ""] or source_table.startswith("Multiple"):
            response["summary"]["tables_skipped"] += 1
            response["table_results"].append({
                "source_table": source_table,
                "target_table": mapping.get("target_table", ""),
                "status": "skipped",
                "reason": "Unmapped or multi-source table"
            })
            continue

        result = validate_table_mapping(
            mapping=mapping,
            source_dataset=source_dataset,
            run_id=response["run_id"],
            mode=mode
        )

        response["table_results"].append(result)
        response["summary"]["tables_validated"] += 1
        response["summary"]["total_validations_run"] += result.get("validations_run", 0)
        response["summary"]["total_errors_found"] += result.get("total_errors", 0)

        if result.get("total_errors", 0) > 0:
            response["summary"]["tables_with_errors"] += 1

    response["completed_at"] = datetime.utcnow().isoformat() + "Z"

    return response


# Flask Routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run."""
    return jsonify({
        "status": "healthy",
        "service": "data-validation-agent",
        "version": "1.0.0"
    })


@app.route('/validate', methods=['POST'])
def validate():
    """
    Validate staging data based on schema mapping JSON.

    Request Body:
        {
            "schema_mapping": { ... },  // Schema mapping JSON object or string
            "mode": "REPORT" | "FIX"    // Validation mode (default: REPORT)
        }

    Returns:
        JSON response with validation results
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        schema_mapping = data.get("schema_mapping")
        mode = data.get("mode", "REPORT").upper()

        if not schema_mapping:
            return jsonify({
                "status": "error",
                "message": "schema_mapping is required"
            }), 400

        if mode not in ["REPORT", "FIX"]:
            return jsonify({
                "status": "error",
                "message": "mode must be 'REPORT' or 'FIX'"
            }), 400

        # Convert to JSON string if dict
        if isinstance(schema_mapping, dict):
            schema_mapping_str = json.dumps(schema_mapping)
        else:
            schema_mapping_str = schema_mapping

        # Extract source dataset from mapping
        try:
            mapping_data = json.loads(schema_mapping_str) if isinstance(schema_mapping_str, str) else schema_mapping
            if "mapping" in mapping_data and "metadata" in mapping_data["mapping"]:
                source_dataset = mapping_data["mapping"]["metadata"].get("source_dataset", "").split(".")[-1]
            elif "metadata" in mapping_data:
                source_dataset = mapping_data["metadata"].get("source_dataset", "")
            else:
                source_dataset = ""
        except:
            source_dataset = ""

        # Run validation
        result = validate_schema_mapping(
            schema_mapping_json=schema_mapping_str,
            source_dataset=source_dataset,
            mode=mode
        )

        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API info."""
    return jsonify({
        "service": "Data Validation Agent API",
        "version": "1.0.0",
        "endpoints": {
            "POST /validate": "Validate staging data based on schema mapping",
            "GET /health": "Health check endpoint"
        },
        "usage": {
            "method": "POST",
            "url": "/validate",
            "body": {
                "schema_mapping": "Schema mapping JSON object",
                "mode": "REPORT or FIX (default: REPORT)"
            }
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
