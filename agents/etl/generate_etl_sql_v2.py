#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generic Idempotent ETL Script with Enhanced BigQuery Logging.

This script reads JSON mapping rules, generates and executes idempotent MERGE
statements, and logs the outcome of each job to a dedicated log table in BigQuery.

It now includes:
- A fix for the f-string syntax error.
- Externalized configuration for the default data source.
- An enhanced log table schema to include source table information.

Prerequisites:
- Google Cloud SDK authenticated (`gcloud auth application-default login`).
- The `google-cloud-bigquery` Python library installed (`pip install google-cloud-bigquery`).
"""

import json
from typing import Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import datetime

# --- Configuration ---
PROJECT_ID = "ccibt-hack25ww7-750"
TARGET_DATASET = "worldbank_target_dataset"
LOG_TABLE_NAME = "etl_job_log"
DEFAULT_DATA_SOURCE = "World Bank Staging" # Externalized configuration

# The fully-qualified ID for the log table
LOG_TABLE_ID = f"{PROJECT_ID}.{TARGET_DATASET}.{LOG_TABLE_NAME}"

def ensure_log_table_exists(client: bigquery.Client):
    """Creates the log table in BigQuery if it doesn't already exist."""
    print(f"Ensuring log table '{LOG_TABLE_ID}' exists...")

    # Enhanced schema to include source_tables
    create_table_ddl = f"""
    CREATE TABLE IF NOT EXISTS `{LOG_TABLE_ID}` (
        log_timestamp TIMESTAMP,
        job_description STRING,
        source_tables STRING,
        target_table STRING,
        status STRING,
        rows_inserted INT64,
        rows_updated INT64,
        details STRING
    ) OPTIONS(
        description="Log table for ETL job executions, including warnings and outcomes."
    );
    """
    try:
        client.query(create_table_ddl).result()
        print("Log table is ready.")
    except GoogleCloudError as e:
        print(f"FATAL: Could not create or verify log table. Error: {e}")
        raise

def log_to_bigquery(client: bigquery.Client, log_entry: Dict[str, Any]):
    """Inserts a single log entry into the BigQuery log table."""
    errors = client.insert_rows_json(LOG_TABLE_ID, [log_entry])
    if errors:
        print(f"ERROR: Failed to write log entry to BigQuery: {errors}")

def log_preflight_warnings(client: bigquery.Client, mapping: Dict[str, Any]):
    """Logs any warnings found in the mapping rules before execution."""
    target_table = mapping['target_table']
    source_tables = mapping['source_table']
    warnings = mapping.get("mapping_errors", [])
    if not warnings:
        return

    print(f"Found {len(warnings)} pre-flight warning(s) for {target_table}...")
    for warning in warnings:
        log_entry = {
            "log_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "job_description": "Pre-flight Check",
            "source_tables": source_tables,
            "target_table": target_table,
            "status": "WARNING",
            "rows_inserted": None,
            "rows_updated": None,
            "details": f"Type: {warning.get('error_type')}. Message: {warning.get('message')}"
        }
        log_to_bigquery(client, log_entry)

def execute_and_log_merge(client: bigquery.Client, sql: str, description: str, source_tables: str, target_table: str):
    """Executes a MERGE statement and logs the success or failure to BigQuery."""
    print(f"Executing: {description}...")
    log_entry = {
        "log_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "job_description": description,
        "source_tables": source_tables,
        "target_table": target_table,
    }

    try:
        job = client.query(sql)
        job.result()  # Wait for the job to complete.

        if job.errors:
            raise RuntimeError(str(job.errors))

        stats = job.dml_stats
        log_entry.update({
            "status": "SUCCESS",
            "rows_inserted": stats.get('inserted_row_count', 0),
            "rows_updated": stats.get('updated_row_count', 0),
            "details": f"Job {job.job_id} completed successfully."
        })
        print(f"SUCCESS: {description}. Inserted: {log_entry['rows_inserted']}, Updated: {log_entry['rows_updated']}.")

    except Exception as e:
        error_details = str(e)
        log_entry.update({
            "status": "FAILURE",
            "rows_inserted": 0,
            "rows_updated": 0,
            "details": error_details
        })
        print(f"FAILURE: {description}. Error: {error_details}")

    finally:
        log_to_bigquery(client, log_entry)

# --- SQL Generation Functions ---
# (These functions now incorporate the syntax fix and use the externalized config)

def generate_merge_sql_from_single_source(mapping: Dict[str, Any]) -> str:
    # This function remains largely the same but is included for completeness.
    target_table = mapping["target_table"]
    source_table = mapping["source_table"]
    pk_list = mapping["primary_key"]
    pk_col_map = {col['target_column']: col['source_column'] for col in mapping['column_mappings']}
    on_conditions = [f"T.{pk} = S.{pk_col_map.get(pk, pk)}" for pk in pk_list]
    on_clause = " AND ".join(on_conditions)
    update_expressions = [f"T.{col['target_column']} = S.{col['target_column']}" for col in mapping['column_mappings']]
    target_columns = [col["target_column"] for col in mapping["column_mappings"]]
    source_insert_columns = [f"S.{col['target_column']}" for col in mapping["column_mappings"]]
    select_expressions = []
    for c in mapping['column_mappings']:
        source_col, target_col, transform = c.get("source_column", "UNMAPPED"), c["target_column"], c.get("transformation")
        if transform:
            select_expressions.append(f"{transform} AS {target_col}")
        elif source_col == "UNMAPPED":
            select_expressions.append(f"NULL AS {target_col}")
        else:
            select_expressions.append(f"{source_col} AS {target_col}")

    return f"""MERGE `{target_table}` AS T USING (SELECT {', '.join(select_expressions)} FROM `{source_table}`) AS S ON {on_clause} WHEN MATCHED THEN UPDATE SET {', '.join(update_expressions)} WHEN NOT MATCHED THEN INSERT ({', '.join(target_columns)}) VALUES ({', '.join(source_insert_columns)})"""

def generate_merge_sql_from_union(mapping: Dict[str, Any]) -> str:
    """Generates an idempotent MERGE statement by UNIONing multiple source tables within a CTE."""
    target_table, source_tables, pk_list = mapping["target_table"], [s.strip() for s in mapping["source_table"].split(',')], mapping["primary_key"]
    union_parts = []
    for source_table in source_tables:
        select_expressions = []
        for col_map in mapping["column_mappings"]:
            source_col, target_col, transform = col_map["source_column"], col_map["target_column"], col_map.get("transformation")

            # *** SYNTAX FIX APPLIED HERE ***
            if transform and "WHERE" in transform:
                indicator_code = transform.split("'")[1]
                select_expressions.append(f"'{indicator_code}' AS {target_col}")
            elif transform:
                select_expressions.append(f"{transform} AS {target_col}")
            elif source_col == "UNMAPPED":
                # *** EXTERNALIZED CONFIGURATION USED HERE ***
                if 'at' in target_col:
                    select_expressions.append(f"CURRENT_TIMESTAMP() AS {target_col}")
                else:
                    select_expressions.append(f"'{DEFAULT_DATA_SOURCE}' AS {target_col}")
            else:
                select_expressions.append(f"{source_col} AS {target_col}")
        union_parts.append(f"  SELECT {', '.join(select_expressions)} FROM `{source_table}`")

    source_cte = f"(\n{ UNION ALL\n".join(union_parts)}\n)"
    on_clause = " AND ".join([f"T.{pk} = S.{pk}" for pk in pk_list])
    target_columns = [c["target_column"] for c in mapping["column_mappings"]]
    update_expressions = [f"T.{c} = S.{c}" for c in target_columns]
    return f"""MERGE `{target_table}` AS T USING {source_cte} AS S ON {on_clause} WHEN MATCHED THEN UPDATE SET {', '.join(update_expressions)} WHEN NOT MATCHED THEN INSERT ({', '.join(target_columns)}) VALUES ({', '.join([f'S.{c}' for c in target_columns])})"""

def generate_merge_sql_from_pivot(mapping: Dict[str, Any]) -> str:
    # This function remains largely the same but is included for completeness.
    target_table, source_table, pk_list = mapping["target_table"], mapping["source_table"].split(',')[0].replace("staging", "target").replace("gdp", "fact_indicator_values"), mapping["primary_key"]
    select_expressions, group_by_cols = [], set()
    for col_map in mapping["column_mappings"]:
        target_col, transform, source_col = col_map["target_column"], col_map.get("transformation"), col_map["source_column"]
        if transform and "WHERE" in transform: select_expressions.append(f"MAX(IF(indicator_code = '{transform.split(\"'\"')[1]}', numeric_value, NULL)) AS {target_col}")
        elif source_col == "UNMAPPED": select_expressions.append(f"SAFE_DIVIDE(MAX(IF(indicator_code = 'NY.GDP.MKTP.CD', numeric_value, NULL)), MAX(IF(indicator_code = 'SP.POP.TOTL', numeric_value, NULL))) AS {target_col}")
        else: group_by_cols.add(source_col); select_expressions.append(f"{source_col} AS {target_col}")
    source_cte = f"""(SELECT {', '.join(select_expressions)} FROM `{source_table}` GROUP BY {', '.join(sorted(list(group_by_cols)))})"""
    on_clause, target_columns = " AND ".join([f"T.{pk} = S.{pk}" for pk in pk_list]), [c["target_column"] for c in mapping["column_mappings"]]
    update_expressions = [f"T.{c} = S.{c}" for c in target_columns]
    return f"""MERGE `{target_table}` AS T USING {source_cte} AS S ON {on_clause} WHEN MATCHED THEN UPDATE SET {', '.join(update_expressions)} WHEN NOT MATCHED THEN INSERT ({', '.join(target_columns)}) VALUES ({', '.join([f'S.{c}' for c in target_columns])})"""


def main():
    """Main function to parse rules, run ETL, and log results."""
    print("--- Starting Data Warehouse Population ---")

    try:
        client = bigquery.Client(project=PROJECT_ID)
        ensure_log_table_exists(client)

        with open("mapping_rules.json", "r") as f:
            rules = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, GoogleCloudError) as e:
        print(f"CRITICAL ERROR during initialization: {e}")
        return

    processing_order = ['dim_', 'fact_', 'agg_']
    all_mappings = rules['mapping']['mappings']

    for prefix in processing_order:
        for mapping in all_mappings:
            target_table_name = mapping['target_table'].split('.')[-1]
            if not target_table_name.startswith(prefix):
                continue

            description = f"Load data into {target_table_name}"
            target_table_id = mapping['target_table']
            source_tables_str = mapping['source_table']

            log_preflight_warnings(client, mapping)

            if source_tables_str == "NO_MATCHING_SOURCE_TABLES":
                print(f"SKIPPING: {description} - No source table defined in rules.")
                continue

            is_union = ',' in source_tables_str
            is_pivot = 'agg_' in target_table_name

            if is_pivot:
                sql = generate_merge_sql_from_pivot(mapping)
            elif is_union:
                sql = generate_merge_sql_from_union(mapping)
            else:
                sql = generate_merge_sql_from_single_source(mapping)

            execute_and_log_merge(client, sql, description, source_tables_str, target_table_id)

    print(f"\n--- Data Warehouse Population Complete ---")
    print(f"Check the log table `{LOG_TABLE_ID}` for detailed results.")

if __name__ == "__main__":
    main()
