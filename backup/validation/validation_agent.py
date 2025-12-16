from google.cloud import bigquery
import json
import os
from google.adk.agents.llm_agent import Agent

# We need to maintain a client instance or initialize it inside the tool.
# To keep the tool function stateless/clean for ADK, we can initialize client inside or use a global.
# Given the previous class structure, let's use a function that initializes the client.

def validate_data(bq_table_id: str, rules_str: str, mode: str) -> str:
    """
    Validates data in a BigQuery table based on provided rules.
    
    Args:
        bq_table_id: The ID of the BigQuery table (e.g., 'project.dataset.table').
        rules_str: JSON string of rules list.
        mode: 'REPORT' or 'FIX'.
        
    Returns:
        JSON string summary of operations.
    """
    try:
        rules = json.loads(rules_str)
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Invalid rules JSON"})

    # Determine Project ID from table ID or environment
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id and "." in bq_table_id:
        project_id = bq_table_id.split(".")[0]
    
    if not project_id:
         return json.dumps({"status": "error", "message": "Could not determine Project ID"})

    try:
        client = bigquery.Client(project=project_id)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"BQ Client Init Failed: {str(e)}"})
    
    # --- Logic from previous ValidationAgent ---
    results = {"status": "success", "mode": mode, "errors_found": 0, "rows_corrected": 0}
    
    # Extract dataset name from the table ID
    dataset_name = bq_table_id.split('.')[1] if '.' in bq_table_id else 'staging'

    # Ensure errors table exists
    def _create_errors_table_if_not_exists(table_name):
        full_table_id = f"{project_id}.{dataset_name}.{table_name}"
        schema = [
            bigquery.SchemaField("source_table", "STRING"),
            bigquery.SchemaField("failed_column", "STRING"),
            bigquery.SchemaField("violation_type", "STRING"),
            bigquery.SchemaField("row_data", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
        ]
        try:
            table = bigquery.Table(full_table_id, schema=schema)
            client.create_table(table, exists_ok=True)
        except Exception as e:
            print(f"Error creating error table: {e}")

    def _generate_sql_condition(column, rule):
        rule_type = rule.get("type")
        if rule_type == "NOT_NULL":
            return f"{column} IS NULL"
        elif rule_type == "NUMERIC":
            # Check if value is NOT numeric (when it should be)
            return f"SAFE_CAST({column} AS FLOAT64) IS NULL AND {column} IS NOT NULL"
        elif rule_type == "RANGE":
            min_val = rule.get("min")
            max_val = rule.get("max")
            conditions = []
            if min_val is not None:
                conditions.append(f"({column} IS NOT NULL AND {column} < {min_val})")
            if max_val is not None:
                conditions.append(f"({column} IS NOT NULL AND {column} > {max_val})")
            return " OR ".join(conditions) if conditions else None
        return None

    def _report_errors(source_table, condition, error_table, violation_label):
        dataset = source_table.split('.')[1]
        full_error_table = f"{project_id}.{dataset}.{error_table}"
        query = f"""
            INSERT INTO `{full_error_table}` (source_table, failed_column, violation_type, row_data, timestamp)
            SELECT '{source_table}', '{violation_label}', '{violation_label}', TO_JSON_STRING(t), CURRENT_TIMESTAMP()
            FROM `{source_table}` AS t WHERE {condition}
        """
        try:
            job = client.query(query)
            job.result()
            return job.num_dml_affected_rows or 0
        except Exception as e:
            print(f"Report query failed: {e}")
            return 0

    def _fix_errors(table, condition, column, fix_value, rule_type):
        # For RANGE violations, we don't fix automatically - too risky
        if rule_type == "RANGE":
            print(f"Skipping auto-fix for RANGE violations on {column} - manual review needed")
            return 0

        query = f"""
            UPDATE `{table}` SET {column} = {fix_value} WHERE {condition}
        """
        try:
            job = client.query(query)
            job.result()
            return job.num_dml_affected_rows or 0
        except Exception as e:
            print(f"Fix query failed: {e}")
            return 0

    if mode == "REPORT":
        _create_errors_table_if_not_exists("staging_errors")

    for rule in rules:
        column = rule.get("column")
        rule_type = rule.get("type")
        if not column or not rule_type: continue
        
        condition = _generate_sql_condition(column, rule)
        if not condition: continue

        if mode == "REPORT":
            count = _report_errors(bq_table_id, condition, "staging_errors", f"{column}_{rule_type}")
            results["errors_found"] += count
        elif mode == "FIX":
            # Determine appropriate fix value based on rule type
            if rule_type == "NOT_NULL":
                # For NOT_NULL violations, set to a default safe value
                fix_val = "'UNKNOWN'" if column in ["country_code", "iso3", "indicator_code"] else "0"
            elif rule_type == "NUMERIC":
                # For non-numeric values in numeric columns, set to NULL
                fix_val = "NULL"
            else:
                fix_val = "NULL"

            count = _fix_errors(bq_table_id, condition, column, fix_val, rule_type)
            results["rows_corrected"] += count
            
    return json.dumps(results)

# Define the Agent
validation_agent = Agent(
    model='gemini-2.5-flash',
    name='validation_agent',
    description='An agent that validates BigQuery data against defined rules.',
    instruction='You are a validation orchestrator. Use the validate_data tool to validate tables when requested.',
    tools=[validate_data],
)
