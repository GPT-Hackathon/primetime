"""Schema Mapping Agent - Auto-generates schema mappings using LLM."""

# ADK agent (for adk run)
from .agent import root_agent

# Original functions (for backwards compatibility)
from .schema_mapper import generate_schema_mapping

__all__ = ["root_agent", "generate_schema_mapping"]
