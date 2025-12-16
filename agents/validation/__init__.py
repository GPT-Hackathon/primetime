"""Validation Agent - Validates BigQuery data quality using schema mappings."""

# ADK agent (for adk run)
from .agent import root_agent

# Original function (for backwards compatibility)
from .data_validator import validate_schema_mapping

__all__ = ["root_agent", "validate_schema_mapping"]

