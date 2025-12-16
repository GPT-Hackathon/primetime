"""Staging Loader Agent - Loads CSV data from GCS to BigQuery staging tables."""

# ADK agent (for adk run)
from .agent import root_agent

# Tool functions (for backwards compatibility)
from .tools.staging_loader_tools import load_csv_to_bigquery_from_gcs, find_schema_files_in_gcs

__all__ = ["root_agent", "load_csv_to_bigquery_from_gcs", "find_schema_files_in_gcs"]

