"""Schema analysis and mapping logic."""

from typing import Dict, List, Any, Tuple
from thefuzz import fuzz
import re


def normalize_column_name(name: str) -> str:
    """Normalize column name for comparison."""
    return name.lower().strip().replace('_', '').replace('-', '')


def calculate_similarity(source_col: str, target_col: str) -> int:
    """Calculate similarity score between two column names.
    
    Args:
        source_col: Source column name
        target_col: Target column name
        
    Returns:
        Similarity score (0-100)
    """
    # Exact match after normalization
    if normalize_column_name(source_col) == normalize_column_name(target_col):
        return 100
    
    # Use fuzzy matching
    return fuzz.ratio(normalize_column_name(source_col), normalize_column_name(target_col))


def are_types_compatible(source_type: str, target_type: str) -> Tuple[bool, str]:
    """Check if source and target types are compatible.
    
    Args:
        source_type: Source column type
        target_type: Target column type
        
    Returns:
        Tuple of (is_compatible, transformation_needed)
    """
    source_type = source_type.upper()
    target_type = target_type.upper()
    
    # Exact match
    if source_type == target_type:
        return True, "DIRECT"
    
    # String types
    if source_type in ["STRING", "TEXT", "VARCHAR", "CHAR"]:
        if target_type in ["STRING", "TEXT", "VARCHAR", "CHAR"]:
            return True, "DIRECT"
        elif target_type in ["INT64", "INTEGER", "BIGINT"]:
            return True, "CAST_TO_INT64"
        elif target_type in ["NUMERIC", "DECIMAL", "FLOAT64", "FLOAT"]:
            return True, "CAST_TO_NUMERIC"
        elif target_type == "DATE":
            return True, "PARSE_DATE"
        elif target_type == "TIMESTAMP":
            return True, "PARSE_TIMESTAMP"
        elif target_type == "BOOLEAN":
            return True, "CAST_TO_BOOL"
    
    # Numeric types
    if source_type in ["INT64", "INTEGER", "BIGINT", "INT"]:
        if target_type in ["INT64", "INTEGER", "BIGINT", "INT"]:
            return True, "DIRECT"
        elif target_type in ["NUMERIC", "DECIMAL", "FLOAT64", "FLOAT"]:
            return True, "CAST_TO_NUMERIC"
        elif target_type in ["STRING", "TEXT"]:
            return True, "CAST_TO_STRING"
    
    if source_type in ["NUMERIC", "DECIMAL", "FLOAT64", "FLOAT"]:
        if target_type in ["NUMERIC", "DECIMAL", "FLOAT64", "FLOAT"]:
            return True, "DIRECT"
        elif target_type in ["INT64", "INTEGER", "BIGINT"]:
            return True, "CAST_TO_INT64"
        elif target_type in ["STRING", "TEXT"]:
            return True, "CAST_TO_STRING"
    
    # Date/Time types
    if source_type in ["DATE", "TIMESTAMP", "DATETIME"]:
        if target_type in ["DATE", "TIMESTAMP", "DATETIME"]:
            return True, "CAST_DATE_TYPE"
        elif target_type in ["STRING", "TEXT"]:
            return True, "CAST_TO_STRING"
    
    # Boolean
    if source_type == "BOOLEAN" and target_type == "BOOLEAN":
        return True, "DIRECT"
    
    return False, "INCOMPATIBLE"


def generate_transformation_sql(source_col: str, source_type: str, target_col: str, 
                                target_type: str, transformation: str) -> str:
    """Generate SQL transformation expression.
    
    Args:
        source_col: Source column name
        source_type: Source column type
        target_col: Target column name
        target_type: Target column type
        transformation: Transformation type
        
    Returns:
        SQL expression for the transformation
    """
    if transformation == "DIRECT":
        return f"`{source_col}`"
    
    elif transformation == "CAST_TO_INT64":
        return f"SAFE_CAST(`{source_col}` AS INT64)"
    
    elif transformation == "CAST_TO_NUMERIC":
        return f"SAFE_CAST(`{source_col}` AS NUMERIC)"
    
    elif transformation == "CAST_TO_STRING":
        return f"CAST(`{source_col}` AS STRING)"
    
    elif transformation == "CAST_TO_BOOL":
        return f"SAFE_CAST(`{source_col}` AS BOOLEAN)"
    
    elif transformation == "PARSE_DATE":
        # Try common date formats
        return f"SAFE.PARSE_DATE('%Y-%m-%d', `{source_col}`)"
    
    elif transformation == "PARSE_TIMESTAMP":
        return f"SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', `{source_col}`)"
    
    elif transformation == "CAST_DATE_TYPE":
        if target_type.upper() == "DATE":
            return f"DATE(`{source_col}`)"
        elif target_type.upper() == "TIMESTAMP":
            return f"TIMESTAMP(`{source_col}`)"
        return f"CAST(`{source_col}` AS {target_type})"
    
    else:
        return f"/* TODO: Manual mapping needed */ `{source_col}`"


def analyze_mapping(source_schema: Dict[str, Any], target_schema: Dict[str, Any], 
                    similarity_threshold: int = 80) -> Dict[str, Any]:
    """Analyze and suggest mappings between source and target schemas.
    
    Args:
        source_schema: Source table schema
        target_schema: Target table schema
        similarity_threshold: Minimum similarity score for automatic mapping (default: 80)
        
    Returns:
        Dictionary containing mapping suggestions and analysis
    """
    source_cols = {col["name"]: col for col in source_schema["columns"]}
    target_cols = {col["name"]: col for col in target_schema["columns"]}
    
    mappings = []
    unmapped_source = []
    unmapped_target = list(target_cols.keys())
    
    # Find mappings for each source column
    for source_name, source_info in source_cols.items():
        best_match = None
        best_score = 0
        
        for target_name, target_info in target_cols.items():
            score = calculate_similarity(source_name, target_name)
            if score > best_score:
                best_score = score
                best_match = (target_name, target_info)
        
        if best_match and best_score >= similarity_threshold:
            target_name, target_info = best_match
            compatible, transformation = are_types_compatible(
                source_info["type"], 
                target_info["type"]
            )
            
            sql_expr = generate_transformation_sql(
                source_name,
                source_info["type"],
                target_name,
                target_info["type"],
                transformation
            )
            
            mapping = {
                "source_column": source_name,
                "source_type": source_info["type"],
                "target_column": target_name,
                "target_type": target_info["type"],
                "similarity_score": best_score,
                "type_compatible": compatible,
                "transformation": transformation,
                "sql_expression": sql_expr,
                "confidence": "high" if best_score >= 95 and compatible else "medium" if best_score >= 80 and compatible else "low"
            }
            mappings.append(mapping)
            
            if target_name in unmapped_target:
                unmapped_target.remove(target_name)
        else:
            unmapped_source.append({
                "column": source_name,
                "type": source_info["type"],
                "best_match": best_match[0] if best_match else None,
                "best_score": best_score
            })
    
    analysis = {
        "source_table": source_schema["full_name"],
        "target_table": target_schema["full_name"],
        "mappings": mappings,
        "unmapped_source_columns": unmapped_source,
        "unmapped_target_columns": unmapped_target,
        "mapping_stats": {
            "total_source_columns": len(source_cols),
            "total_target_columns": len(target_cols),
            "mapped_columns": len(mappings),
            "unmapped_source": len(unmapped_source),
            "unmapped_target": len(unmapped_target),
            "high_confidence": sum(1 for m in mappings if m["confidence"] == "high"),
            "medium_confidence": sum(1 for m in mappings if m["confidence"] == "medium"),
            "low_confidence": sum(1 for m in mappings if m["confidence"] == "low")
        }
    }
    
    return analysis

