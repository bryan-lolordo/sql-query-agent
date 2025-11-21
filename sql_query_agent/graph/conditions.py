"""Conditional routing logic for the SQL Query Agent graph."""

from typing import Literal
from .state import SQLAgentState


def should_retry(state: SQLAgentState) -> Literal["format_results", "analyze_error", "ask_clarification"]:
    """Decide whether to retry, format results, or ask for clarification."""
    
    success = state.get("success", False)
    attempt = state.get("attempt", 1)
    max_attempts = state.get("max_attempts", 3)

    print(f"\n🔀 SHOULD_RETRY: success={success}, attempt={attempt}/{max_attempts}")

    if success:
        print("   → format_results")
        return "format_results"
    elif attempt <= max_attempts:
        print("   → analyze_error") 
        return "analyze_error"
    else:
        print("   → ask_clarification")
        return "ask_clarification"


def is_valid_sql(state: SQLAgentState) -> Literal["execute_sql", "generate_sql"]:
    """Route based on SQL validation result."""
    
    execution_error = state.get("execution_error", "")
    
    print(f"\n🔀 IS_VALID_SQL: Has error: {bool(execution_error)}")
    
    # Check if this is a validation error (indicated by "Syntax Error:" prefix)
    if execution_error and execution_error.startswith("Syntax Error:"):
        print("   → generate_sql (validation failed)")
        return "generate_sql"
    
    print("   → execute_sql (validation passed)")
    return "execute_sql"