#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generic ETL SQL Generator from JSON Mapping Rules.

This script reads a JSON file containing data conversion rules and dynamically
generates the appropriate SQL INSERT statements for a BigQuery environment.

It handles:
- Direct 1-to-1 table mappings.
- Mappings from multiple source tables into one (UNION ALL).
- Aggregation/Pivoting from a fact table into a wide table.
- Applying column-level transformations (e.g., CAST).
- Injecting default values for unmapped target columns.
"""

import json
from typing import Dict, Any, List

def generate_select_expression(col_map: Dict[str, Any]) -> str:
    """
    Generates a single column expression for a SELECT statement.

    Args:
        col_map: A dictionary representing a single column mapping.

    Returns:
        A string for the SELECT column expression (e.g., "source_col AS target_col").
    """
    source_col = col_map.get("source_column", "UNMAPPED")
    target_col = col_map["target_column"]
    transformation = col_map.get("transformation")

    # If a transformation is explicitly defined, use it.
    if transformation:
        expression = transformation
    # Handle unmapped columns with default values
    elif source_col == "UNMAPPED":
        if "at" in target_col or "date" in target_col:
            expression = f"CURRENT_TIMESTAMP() /* Default for unmapped column */"
        else:
            expression = f"'Default' /* Default for unmapped column */"
    # Direct mapping
    else:
        expression = source_col

    return f"{expression} AS {target_col}"

def generate_single_source_sql(mapping: Dict[str, Any]) -> str:
    """
    Generates an INSERT statement for a single source table.
    """
    target_table = mapping["target_table"]
    source_table = mapping["source_table"]

    target_columns = [col["target_column"] for col in mapping["column_mappings"]]
    select_expressions = [generate_select_expression(col) for col in mapping["column_mappings"]]

    sql = f"""
-- Populating '{target_table}' from '{source_table}'
INSERT INTO `{target_table}` (
    {', '.join(target_columns)}
)
SELECT
    {', '.join(select_expressions)}
FROM
    `{source_table}`;
"""
    return sql

def generate_union_sql(mapping: Dict[str, Any]) -> str:
    """
    Generates an INSERT statement by UNIONing multiple source tables.
    This is used for un-pivoting data into a fact table or combining similar data.
    """
    target_table = mapping["target_table"]
    source_tables = [s.strip() for s in mapping["source_table"].split(',')]

    target_columns = [col["target_column"] for col in mapping["column_mappings"]]

    union_parts = []
    for source_table in source_tables:
        select_expressions = []
        for col_map in mapping["column_mappings"]:
            source_col = col_map["source_column"]
            target_col = col_map["target_column"]
            transformation = col_map.get("transformation")

            # Handle specific transformations noted in the JSON
            if transformation and "WHERE" in transformation:
                # This pattern indicates a value specific to an indicator code
                indicator_code = transformation.split("'")[1]
                select_expressions.append(f"'{indicator_code}' AS {target_col}")
            elif transformation:
                 select_expressions.append(f"{transformation} AS {target_col}")
            elif source_col == "UNMAPPED":
                 if "at" in target_col or "date" in target_col:
                    select_expressions.append(f"CURRENT_TIMESTAMP() AS {target_col}")
                 else:
                    select_expressions.append(f"'World Bank Staging' AS {target_col}")
            # For UNIONs, source columns are often the same across tables
            else:
                select_expressions.append(f"{source_col} AS {target_col}")

        union_parts.append(f"SELECT {', '.join(select_expressions)} FROM `{source_table}`")

    sql = f"""
-- Populating '{target_table}' by UNIONing multiple sources
INSERT INTO `{target_table}` (
    {', '.join(target_columns)}
)
{' UNION ALL '.join(union_parts)};
"""
    return sql

def generate_pivot_sql(mapping: Dict[str, Any]) -> str:
    """
    Generates an INSERT statement by PIVOTing data from a source table.
    This is used for creating wide, aggregated tables.
    """
    target_table = mapping["target_table"]
    # In this pattern, the source is typically the fact table we just populated
    source_table = mapping["source_table"].split(',')[0].replace("staging", "target").replace("gdp", "fact_indicator_values")

    target_columns = [col["target_column"] for col in mapping["column_mappings"]]

    select_expressions = []
    group_by_cols = set()

    for col_map in mapping["column_mappings"]:
        target_col = col_map["target_column"]
        transformation = col_map.get("transformation")

        if transformation and "WHERE" in transformation:
            # PIVOT logic: MAX(IF(condition, value, NULL))
            indicator_code = transformation.split("'")[1]
            expression = f"MAX(IF(indicator_code = '{indicator_code}', numeric_value, NULL))"
            select_expressions.append(f"{expression} AS {target_col}")
        elif col_map["source_column"] == "UNMAPPED":
            # Calculated field like gdp_per_capita
            gdp_expr = "MAX(IF(indicator_code = 'NY.GDP.MKTP.CD', numeric_value, NULL))"
            pop_expr = "MAX(IF(indicator_code = 'SP.POP.TOTL', numeric_value, NULL))"
            expression = f"SAFE_DIVIDE({gdp_expr}, {pop_expr})"
            select_expressions.append(f"{expression} AS {target_col}")
        else:
            # These are the columns to group by
            group_by_cols.add(col_map["target_column"])
            select_expressions.append(f"{col_map['source_column']} AS {target_col}")

    sql = f"""
-- Populating '{target_table}' by PIVOTING from '{source_table}'
INSERT INTO `{target_table}` (
    {', '.join(target_columns)}
)
SELECT
    {', '.join(select_expressions)}
FROM
    `{source_table}`
GROUP BY
    {', '.join(sorted(list(group_by_cols)))};
"""
    return sql

def generate_sql_from_rules(rules: Dict[str, Any]):
    """
    Main function to parse the entire JSON rules object and generate all SQL.
    """
    print("-- ####################################################")
    print("-- #          Generated ETL SQL Script                #")
    print("-- ####################################################\n")

    # A simple way to handle dependencies: process simple tables first, then facts, then aggregates.
    # A more robust system might use a graph to resolve dependencies.
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
                print(f"-- Please define the source and complete the query below.\n")
                target_columns = [col["target_column"] for col in mapping["column_mappings"]]
                print(f"INSERT INTO `{mapping['target_table']}` ({', '.join(target_columns)})")
                print(f"SELECT ... ;\n")
                continue

            # Heuristic to decide the generation strategy
            is_union = ',' in source_table
            is_pivot = 'agg_' in target_table_name

            if is_pivot:
                sql = generate_pivot_sql(mapping)
            elif is_union:
                sql = generate_union_sql(mapping)
            else:
                sql = generate_single_source_sql(mapping)

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

