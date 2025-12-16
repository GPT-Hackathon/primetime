"""BigQuery integration tools for schema introspection and data preview."""

from google.cloud import bigquery
from typing import Dict, List, Any, Optional
import json


def parse_table_ref(full_table_name: str) -> tuple[str, str, str]:
    """Parse a full table reference into project, dataset, and table.
    
    Args:
        full_table_name: Full table name in format 'project.dataset.table'
        
    Returns:
        Tuple of (project_id, dataset_id, table_id)
    """
    parts = full_table_name.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid table name format. Expected 'project.dataset.table', got '{full_table_name}'")
    return parts[0], parts[1], parts[2]


def get_table_schema(full_table_name: str) -> Dict[str, Any]:
    """Retrieve detailed schema information from a BigQuery table.
    
    Args:
        full_table_name: Full table name in format 'project.dataset.table'
        
    Returns:
        Dictionary containing schema information with columns, types, and metadata
    """
    try:
        project_id, dataset_id, table_id = parse_table_ref(full_table_name)
        
        client = bigquery.Client(project=project_id)
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)
        
        columns = []
        for field in table.schema:
            column_info = {
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,  # NULLABLE, REQUIRED, REPEATED
                "description": field.description or ""
            }
            columns.append(column_info)
        
        schema_info = {
            "project": project_id,
            "dataset": dataset_id,
            "table": table_id,
            "full_name": full_table_name,
            "num_rows": table.num_rows,
            "num_columns": len(columns),
            "columns": columns,
            "created": table.created.isoformat() if table.created else None,
            "modified": table.modified.isoformat() if table.modified else None
        }
        
        return schema_info
        
    except Exception as e:
        raise Exception(f"Error retrieving schema for {full_table_name}: {str(e)}")


def get_sample_data(full_table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve sample data from a BigQuery table.
    
    Args:
        full_table_name: Full table name in format 'project.dataset.table'
        limit: Number of rows to retrieve (default: 10)
        
    Returns:
        List of dictionaries containing sample data rows
    """
    try:
        project_id, dataset_id, table_id = parse_table_ref(full_table_name)
        
        client = bigquery.Client(project=project_id)
        
        query = f"""
            SELECT *
            FROM `{full_table_name}`
            LIMIT {limit}
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        rows = []
        for row in results:
            row_dict = dict(row.items())
            # Convert any non-serializable types to strings
            for key, value in row_dict.items():
                if value is not None and not isinstance(value, (str, int, float, bool)):
                    row_dict[key] = str(value)
            rows.append(row_dict)
        
        return rows
        
    except Exception as e:
        raise Exception(f"Error retrieving sample data from {full_table_name}: {str(e)}")


def analyze_column_values(full_table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
    """Analyze values in a specific column to help with mapping decisions.
    
    Args:
        full_table_name: Full table name in format 'project.dataset.table'
        column_name: Name of the column to analyze
        sample_size: Number of rows to analyze (default: 1000)
        
    Returns:
        Dictionary with value analysis (null count, distinct values, sample values)
    """
    try:
        project_id, dataset_id, table_id = parse_table_ref(full_table_name)
        client = bigquery.Client(project=project_id)
        
        query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(`{column_name}`) as non_null_count,
                COUNT(DISTINCT `{column_name}`) as distinct_count,
                ARRAY_AGG(DISTINCT `{column_name}` IGNORE NULLS LIMIT 10) as sample_values
            FROM `{full_table_name}`
            LIMIT {sample_size}
        """
        
        query_job = client.query(query)
        results = query_job.result()
        row = next(results)
        
        analysis = {
            "column": column_name,
            "total_count": row.total_count,
            "non_null_count": row.non_null_count,
            "null_count": row.total_count - row.non_null_count,
            "null_percentage": ((row.total_count - row.non_null_count) / row.total_count * 100) if row.total_count > 0 else 0,
            "distinct_count": row.distinct_count,
            "sample_values": row.sample_values
        }
        
        return analysis
        
    except Exception as e:
        raise Exception(f"Error analyzing column {column_name} in {full_table_name}: {str(e)}")


def compare_schemas(source_table: str, target_table: str) -> Dict[str, Any]:
    """Compare schemas of source and target tables.
    
    Args:
        source_table: Full source table name
        target_table: Full target table name
        
    Returns:
        Dictionary with comparison results
    """
    source_schema = get_table_schema(source_table)
    target_schema = get_table_schema(target_table)
    
    source_cols = {col["name"]: col for col in source_schema["columns"]}
    target_cols = {col["name"]: col for col in target_schema["columns"]}
    
    comparison = {
        "source": source_schema,
        "target": target_schema,
        "source_only_columns": [col for col in source_cols.keys() if col not in target_cols],
        "target_only_columns": [col for col in target_cols.keys() if col not in source_cols],
        "common_columns": [col for col in source_cols.keys() if col in target_cols]
    }
    
    return comparison


def list_tables_in_dataset(project_id: str, dataset_id: str) -> List[str]:
    """List all tables in a BigQuery dataset.
    
    Args:
        project_id: Google Cloud project ID
        dataset_id: BigQuery dataset ID
        
    Returns:
        List of table names (without project.dataset prefix)
    """
    try:
        client = bigquery.Client(project=project_id)
        dataset_ref = f"{project_id}.{dataset_id}"
        
        tables = client.list_tables(dataset_ref)
        table_names = [table.table_id for table in tables]
        
        return sorted(table_names)
        
    except Exception as e:
        raise Exception(f"Error listing tables in {project_id}.{dataset_id}: {str(e)}")


def discover_table_pairs(source_project: str, source_dataset: str,
                        target_project: str, target_dataset: str) -> List[Dict[str, str]]:
    """Discover matching table pairs between source and target datasets.
    
    This function finds tables that exist in both datasets and pairs them up.
    It uses intelligent matching to handle naming conventions like:
    - source: 'borrower' -> target: 'dim_borrower'
    - source: 'loan' -> target: 'fact_loan'
    
    Args:
        source_project: Source project ID
        source_dataset: Source dataset ID
        target_project: Target project ID
        target_dataset: Target dataset ID
        
    Returns:
        List of dictionaries with 'source_table' and 'target_table' pairs
    """
    try:
        source_tables = list_tables_in_dataset(source_project, source_dataset)
        target_tables = list_tables_in_dataset(target_project, target_dataset)
        
        pairs = []
        
        for source_table in source_tables:
            # Try exact match first
            if source_table in target_tables:
                pairs.append({
                    "source_table": f"{source_project}.{source_dataset}.{source_table}",
                    "target_table": f"{target_project}.{target_dataset}.{source_table}",
                    "match_type": "exact"
                })
                continue
            
            # Try common naming patterns
            # Pattern 1: dim_<table>, fact_<table>
            for prefix in ['dim_', 'fact_', 'bridge_']:
                target_name = f"{prefix}{source_table}"
                if target_name in target_tables:
                    pairs.append({
                        "source_table": f"{source_project}.{source_dataset}.{source_table}",
                        "target_table": f"{target_project}.{target_dataset}.{target_name}",
                        "match_type": f"prefix_{prefix}"
                    })
                    break
            
            # Pattern 2: <table> -> <table>_dim, <table>_fact
            for suffix in ['_dim', '_fact', '_bridge']:
                target_name = f"{source_table}{suffix}"
                if target_name in target_tables:
                    pairs.append({
                        "source_table": f"{source_project}.{source_dataset}.{source_table}",
                        "target_table": f"{target_project}.{target_dataset}.{target_name}",
                        "match_type": f"suffix_{suffix}"
                    })
                    break
        
        return pairs
        
    except Exception as e:
        raise Exception(f"Error discovering table pairs: {str(e)}")

