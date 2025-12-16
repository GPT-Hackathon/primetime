"""SQL generation for schema mappings."""

from typing import Dict, List, Any
from datetime import datetime


def generate_insert_sql(mapping_analysis: Dict[str, Any], include_comments: bool = True) -> str:
    """Generate INSERT INTO ... SELECT SQL for the schema mapping.
    
    Args:
        mapping_analysis: Mapping analysis from schema_analyzer
        include_comments: Whether to include explanatory comments (default: True)
        
    Returns:
        SQL string for the mapping
    """
    source_table = mapping_analysis["source_table"]
    target_table = mapping_analysis["target_table"]
    mappings = mapping_analysis["mappings"]
    
    sql_parts = []
    
    # Header comments
    if include_comments:
        sql_parts.append(f"-- Schema Mapping: {source_table} → {target_table}")
        sql_parts.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_parts.append(f"-- Total mappings: {len(mappings)}")
        sql_parts.append("")
    
    # INSERT INTO clause
    target_columns = [m["target_column"] for m in mappings]
    sql_parts.append(f"INSERT INTO `{target_table}` (")
    sql_parts.append("  " + ",\n  ".join([f"`{col}`" for col in target_columns]))
    sql_parts.append(")")
    sql_parts.append("")
    
    # SELECT clause with mappings
    sql_parts.append("SELECT")
    
    select_lines = []
    for i, mapping in enumerate(mappings):
        is_last = (i == len(mappings) - 1)
        
        line_parts = []
        line_parts.append(f"  {mapping['sql_expression']}")
        line_parts.append(f" AS `{mapping['target_column']}`")
        
        if include_comments:
            # Add inline comment
            comment = f"-- {mapping['transformation']}"
            if mapping['confidence'] != 'high':
                comment += f" ({mapping['confidence']} confidence)"
            if not mapping['type_compatible']:
                comment += " [TYPE MISMATCH - REVIEW NEEDED]"
            line_parts.append(f"  {comment}")
        
        line = "".join(line_parts)
        if not is_last:
            line = line.replace(" AS ", " AS ", 1)  # Ensure proper spacing
            line = line.split("--")[0].rstrip() + ("," if "--" not in line else ",") + (f"  {line.split('--')[1]}" if "--" in line else "")
        
        select_lines.append(line)
    
    sql_parts.extend(select_lines)
    sql_parts.append("")
    sql_parts.append(f"FROM `{source_table}`;")
    
    # Add notes section
    if include_comments:
        sql_parts.append("")
        sql_parts.append("-- MAPPING NOTES:")
        
        # Unmapped columns
        if mapping_analysis.get("unmapped_target_columns"):
            sql_parts.append("-- ")
            sql_parts.append("-- ⚠️ Unmapped Target Columns (not populated by this query):")
            for col in mapping_analysis["unmapped_target_columns"]:
                sql_parts.append(f"--   - {col}")
        
        if mapping_analysis.get("unmapped_source_columns"):
            sql_parts.append("-- ")
            sql_parts.append("-- ℹ️ Unmapped Source Columns (not used in target):")
            for col_info in mapping_analysis["unmapped_source_columns"]:
                sql_parts.append(f"--   - {col_info['column']} ({col_info['type']})")
        
        # Low confidence mappings
        low_conf = [m for m in mappings if m['confidence'] == 'low']
        if low_conf:
            sql_parts.append("-- ")
            sql_parts.append("-- ⚠️ Low Confidence Mappings (please review):")
            for m in low_conf:
                sql_parts.append(f"--   - {m['source_column']} → {m['target_column']} (similarity: {m['similarity_score']}%)")
    
    return "\n".join(sql_parts)


def generate_merge_sql(mapping_analysis: Dict[str, Any], 
                       key_columns: List[str],
                       include_comments: bool = True) -> str:
    """Generate MERGE SQL for incremental updates.
    
    Args:
        mapping_analysis: Mapping analysis from schema_analyzer
        key_columns: List of key columns for matching
        include_comments: Whether to include explanatory comments
        
    Returns:
        SQL string for MERGE operation
    """
    source_table = mapping_analysis["source_table"]
    target_table = mapping_analysis["target_table"]
    mappings = mapping_analysis["mappings"]
    
    sql_parts = []
    
    if include_comments:
        sql_parts.append(f"-- MERGE Statement: {source_table} → {target_table}")
        sql_parts.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_parts.append(f"-- Key columns: {', '.join(key_columns)}")
        sql_parts.append("")
    
    # MERGE clause
    sql_parts.append(f"MERGE `{target_table}` AS target")
    sql_parts.append("USING (")
    sql_parts.append("  SELECT")
    
    # SELECT with mappings
    select_lines = []
    for i, mapping in enumerate(mappings):
        is_last = (i == len(mappings) - 1)
        line = f"    {mapping['sql_expression']} AS `{mapping['target_column']}`"
        if not is_last:
            line += ","
        select_lines.append(line)
    
    sql_parts.extend(select_lines)
    sql_parts.append(f"  FROM `{source_table}`")
    sql_parts.append(") AS source")
    sql_parts.append("")
    
    # ON clause
    on_conditions = [f"target.`{col}` = source.`{col}`" for col in key_columns]
    sql_parts.append("ON " + " AND ".join(on_conditions))
    sql_parts.append("")
    
    # WHEN MATCHED
    sql_parts.append("WHEN MATCHED THEN")
    sql_parts.append("  UPDATE SET")
    update_lines = []
    update_cols = [m["target_column"] for m in mappings if m["target_column"] not in key_columns]
    for i, col in enumerate(update_cols):
        is_last = (i == len(update_cols) - 1)
        line = f"    target.`{col}` = source.`{col}`"
        if not is_last:
            line += ","
        update_lines.append(line)
    sql_parts.extend(update_lines)
    sql_parts.append("")
    
    # WHEN NOT MATCHED
    sql_parts.append("WHEN NOT MATCHED THEN")
    target_columns = [m["target_column"] for m in mappings]
    sql_parts.append("  INSERT (")
    sql_parts.append("    " + ",\n    ".join([f"`{col}`" for col in target_columns]))
    sql_parts.append("  )")
    sql_parts.append("  VALUES (")
    sql_parts.append("    " + ",\n    ".join([f"source.`{col}`" for col in target_columns]))
    sql_parts.append("  );")
    
    return "\n".join(sql_parts)


def generate_dbt_model(mapping_analysis: Dict[str, Any]) -> str:
    """Generate a DBT model for the mapping.
    
    Args:
        mapping_analysis: Mapping analysis from schema_analyzer
        
    Returns:
        DBT model SQL string
    """
    source_table = mapping_analysis["source_table"]
    target_table = mapping_analysis["target_table"]
    mappings = mapping_analysis["mappings"]
    
    # Extract table name for model
    target_name = target_table.split(".")[-1]
    
    sql_parts = []
    
    # DBT config
    sql_parts.append("{{")
    sql_parts.append("  config(")
    sql_parts.append("    materialized='table',")
    sql_parts.append(f"    schema='{target_table.split('.')[1]}',")
    sql_parts.append(f"    alias='{target_name}'")
    sql_parts.append("  )")
    sql_parts.append("}}")
    sql_parts.append("")
    
    # SELECT
    sql_parts.append("SELECT")
    select_lines = []
    for i, mapping in enumerate(mappings):
        is_last = (i == len(mappings) - 1)
        line = f"  {mapping['sql_expression']} AS `{mapping['target_column']}`"
        if not is_last:
            line += ","
        select_lines.append(line)
    
    sql_parts.extend(select_lines)
    sql_parts.append(f"FROM `{source_table}`")
    
    return "\n".join(sql_parts)

