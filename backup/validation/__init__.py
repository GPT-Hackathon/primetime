"""
Validation Agent Package

This package contains the validation agent and infrastructure for validating
BigQuery data against defined rules.
"""

from .validation_agent import validation_agent, validate_data

__all__ = ["validation_agent", "validate_data"]
