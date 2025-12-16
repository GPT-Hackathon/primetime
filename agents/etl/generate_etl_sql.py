#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generic Idempotent ETL SQL Generator from JSON Mapping Rules.

This script reads a JSON file containing data conversion rules and dynamically
generates idempotent SQL MERGE statements for a BigQuery environment.

It handles:
- Direct 1-to-1 table mappings.
- Mappings from multiple source tables into one (UNION ALL).
- Aggregation/Pivoting from a fact table into a wide table.
- Applying column-level transformations (e.g., CAST).
- Injecting default values for unmapped target columns.
- Building MERGE statements to ensure idempotency (update/insert logic).
"""

import json
from typing import Dict, Any, List

def get_select_expression(col_map: Dict[str, Any], alias: str = None) -> str:
    """
    Generates a single column expression for a SELECT statement.

    Args:
        col_map: A dictionary representing a single column mapping.
        alias: An optional alias for the source table (e.g., 'S').

    Returns:
        A string for the SELECT column expression (e.g., "S.source_col AS target_col").
    """
    source_col = col_map.get("source_column", "UNMAPPED")
    target_col = col_map["target_column"]
    transformation = col_map.get("transformation")

    source_ref = f"{alias}.{source_col}" if alias and source_col != "UNMAPPED" else source_col

    # If a transformation is explicitly defined, use it.
    if transformation:
        # Replace the base column name with the aliased version if applicable
        expression = transformation.replace(source_col, source_ref) if alias else transformation
    # Handle unmapped columns with default values
    elif source_col == "UNMAPPED":
        if "at" in target_col or "date" in target_col:
            expression = "CURRENT_TIMESTAMP() /* Default for unmapped column */"
        else:
            expression = "'Default' /* Default for unmapped column */"
    # Direct mapping
    else:
        expression = source_ref

    return f"{expression} AS {target_col}"

def generate_merge_sql_from_single_source(mapping: Dict[str, Any]) -> str:
    """
    Generates an idempotent MERGE statement for a single source table.
    """
    target_table = mapping["target_table"]
    source_table = mapping["source_table"]
    pk_list = mapping["primary_key"]

    # Build the ON clause for the MERGE
    # Assumes the source column for the PK is the first column mapping with the target PK name
    pk_col_map = {col['target_column']: col['source_column'] for col in mapping['column_mappings']}
    on_conditions = [f"T.{pk} = S.{pk_col_map[pk]}" for pk in pk_list]
    on_clause = " AND ".join(on_conditions)

    # Build the UPDATE SET clause
    update_expressions = [f"T.{col['target_column']} = S.{col['target_column']}" for col in mapping['column_mappings']]

    # Build the INSERT clauses
    target_columns = [col["target_column"] for col in mapping["column_mappings"]]
    source_insert_columns = [f"S.{col['target_column']}" for col in mapping["column_mappings"]]

    sql = f"""
-- Idempotent load for '{target_table}' from '{source_table}' using MERGE.
MERGE `{target_table}` AS T
USING (SELECT {', '.join([get_select_expression(c) for c in mapping['column_mappings']])} FROM `{source_table}`) AS S
ON {on_clause}
WHEN MATCHED THEN
  UPDATE SET {', '.join(update_expressions)}
WHEN NOT MATCHED THEN
  INSERT ({', '.join(target_columns)})
  VALUES ({', '.join(source_insert_columns)});
"""
    return sql

def generate_merge_sql_from_union(mapping: Dict[str, Any]) -> str:
    """
    Generates an idempotent MERGE statement by UNIONing multiple source tables within a CTE.
    """
    target_table = mapping["target_table"]
    source_tables = [s.strip() for s in mapping["source_table"].split(',')]
    pk_list = mapping["primary_key"]

    # Build the UNION ALL part for the source CTE
    union_parts = []
    for source_table in source_tables:
        select_expressions = []
        for col_map in mapping["column_mappings"]:
            source_col = col_map["source_column"]
            target_col = col_map["target_column"]
            transformation = col_map.get("transformation")

            if transformation and "WHERE" in transformation:
                indicator_code = transformation.split("'")[1]
                select_expressions.append(f"'{indicator_code}' AS {target_col}")
            elif transformation:
                 select_expressions.append(f"{transformation} AS {target_col}")
            elif source_col == "UNMAPPED":
                 if "at" in target_col:
                    select_expressions.append(f"CURRENT_TIMESTAMP() AS {target_col}")
                 else:
                    select_expressions.append(f"'World Bank Staging' AS {target_col}")
            else:
                select_expressions.append(f"{source_col} AS {target_col}")
        union_parts.append(f"  SELECT {', '.join(select_expressions)} FROM `{source_table}`")

    source_cte = f"(\n{' UNION ALL\n'.join(union_parts)}\n)"

    # Build the rest of the MERGE statement
    on_clause = " AND ".join([f"T.{pk} = S.{pk}" for pk in pk_list])
    target_columns = [col["target_column"] for col in mapping["column_mappings"]]
    update_expressions = [f"T.{col} = S.{col}" for col in target_columns]
    source_insert_columns = [f"S.{col}" for col in target_columns]

    sql = f"""
-- Idempotent load for '{target_table}' from a UNION of sources using MERGE.
MERGE `{target_table}` AS T
USING {source_cte} AS S
ON {on_clause}
WHEN MATCHED THEN
  UPDATE SET {', '.join(update_expressions)}
WHEN NOT MATCHED THEN
  INSERT ({', '.join(target_columns)})
  VALUES ({', '.join(source_insert_columns)});
"""
    return sql

def generate_merge_sql_from_pivot(mapping: Dict[str, Any]) -> str:
    """
    Generates an idempotent MERGE statement by PIVOTing data from a source table within a CTE.
    """
    target_table = mapping["target_table"]
    # In this pattern, the source is typically the fact table we just populated
    source_table = mapping["source_table"].split(',')[0].replace("staging", "target").replace("gdp", "fact_indicator_values")
    pk_list = mapping["primary_key"]

    # Build the PIVOT logic for the source CTE
    select_expressions = []
    group_by_cols = set()
    for col_map in mapping["column_mappings"]:
        target_col = col_map["target_column"]
        transformation = col_map.get("transformation")

        if transformation and "WHERE" in transformation:
            indicator_code = transformation.split("'")[1]
            expression = f"MAX(IF(indicator_code = '{indicator_code}', numeric_value, NULL))"
            select_expressions.append(f"{expression} AS {target_col}")
        elif col_map["source_column"] == "UNMAPPED":
            gdp_expr = "MAX(IF(indicator_code = 'NY.GDP.MKTP.CD', numeric_value, NULL))"
            pop_expr = "MAX(IF(indicator_code = 'SP.POP.TOTL', numeric_value, NULL))"
            expression = f"SAFE_DIVIDE({gdp_expr}, {pop_expr})"
            select_expressions.append(f"{expression} AS {target_col}")
        else:
            group_by_cols.add(col_map["source_column"])
            select_expressions.append(f"{col_map['source_column']} AS {target_col}")

    source_cte = f"""(
  SELECT
    {', '.join(select_expressions)}
  FROM
    `{source_table}`
  GROUP BY
    {', '.join(sorted(list(group_by_cols)))}
)"""

    # Build the rest of the MERGE statement
    on_clause = " AND ".join([f"T.{pk} = S.{pk}" for pk in pk_list])
    target_columns = [col["target_column"] for col in mapping["column_mappings"]]
    update_expressions = [f"T.{col} = S.{col}" for col in target_columns]
    source_insert_columns = [f"S.{col}" for col in target_columns]

    sql = f"""
-- Idempotent load for '{target_table}' by PIVOTING from '{source_table}' using MERGE.
MERGE `{target_table}` AS T
USING {source_cte} AS S
ON {on_clause}
WHEN MATCHED THEN
  UPDATE SET {', '.join(update_expressions)}
WHEN NOT MATCHED THEN
  INSERT ({', '.join(target_columns)})
  VALUES ({', '.join(source_insert_columns)});
"""
    return sql


def generate_sql_from_rules(rules: Dict[str, Any]):
    """
    Main function to parse the entire JSON rules object and generate all SQL.
    """
    print("-- ####################################################")
    print("-- #     Generated Idempotent ETL SQL Script (MERGE)  #")
    print("-- ####################################################\n")

    processing_order = ['dim_', 'fact_', 'agg_']
    all_mappings = rules['mapping']['mappings']

    for prefix in processing_order:
        for mapping in all_mappings:
            target_table_name = mapping['target_table'].split('.')[-1]
            if not target_table_name.startswith(prefix):
                continue

            source_table = mapping["source_table"]

            if source_table == "NO_MATCHING_SOURCE_TABLES":
                print(f"-- WARNING: No source table found for target '{mapping['target_table']}'.")
                print(f"-- A placeholder INSERT statement is generated below.\n")
                target_columns = [col["target_column"] for col in mapping["column_mappings"]]
                print(f"INSERT INTO `{mapping['target_table']}` ({', '.join(target_columns)})")
                print(f"SELECT ... ;\n")
                continue

            is_union = ',' in source_table
            is_pivot = 'agg_' in target_table_name

            if is_pivot:
                sql = generate_merge_sql_from_pivot(mapping)
            elif is_union:
                sql = generate_merge_sql_from_union(mapping)
            else:
                sql = generate_merge_sql_from_single_source(mapping)

            print(sql)
            print("-- ------------------------------------------------------------------\n")


if __name__ == "__main__":
    try:
        with open("mapping_rules.json", "r") as f:
            data_mapping_rules = json.load(f)

        generate_sql_from_rules(data_mapping_rules)

    except FileNotFoundError:
        print("Error: 'mapping_rules.json' not found.")
        print("Please ensure the JSON file with mapping rules is in the same directory.")
    except json.JSONDecodeError:
        print("Error: Could not decode 'mapping_rules.json'. Please ensure it is a valid JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

