"""Conditional routing logic for the SQL Query Agent graph."""

from typing import Literal
from .state import SQLAgentState


def should_retry(state: SQLAgentState) -> Literal["format_results", "analyze_error", "ask_clarification"]:
    """Decide whether to retry, format results, or ask for clarification."""
    
    success = state.get("success", False)
    attempt = state.get("attempt", 1)
    max_attempts = state.get("max_attempts", 3)
    
    if success:
        return "format_results"
    elif attempt <= max_attempts:
        return "analyze_error"
    else:
        return "ask_clarification"


def is_valid_sql(state: SQLAgentState) -> Literal["execute_sql", "generate_sql"]:
    """Route based on SQL validation result."""
    
    execution_error = state.get("execution_error")
    
    # If there's a validation error, regenerate
    if execution_error and "Syntax Error" in execution_error:
        return "generate_sql"
    
    return "execute_sql"