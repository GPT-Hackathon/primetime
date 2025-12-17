"""ETL Agent - Generates and executes ETL SQL from JSON mapping rules."""

# ADK agent (for adk run)
from .agent import root_agent

# Tool functions (for backwards compatibility and orchestration)
from .tools.gen_etl_sql import (
    generate_etl_sql_from_json_string,
    execute_sql,
    save_etl_sql,
    load_etl_sql,
    list_etl_sql_scripts,
    delete_etl_sql
)

__all__ = [
    "root_agent",
    "generate_etl_sql_from_json_string",
    "execute_sql",
    "save_etl_sql",
    "load_etl_sql",
    "list_etl_sql_scripts",
    "delete_etl_sql"
]
