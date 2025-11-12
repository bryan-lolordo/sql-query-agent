"""State definition for the SQL Query Agent."""

from typing import TypedDict, Optional, List


class SQLAgentState(TypedDict):
    """State maintained throughout the agent's execution."""
    
    user_query: str
    sql_query: str
    execution_result: Optional[dict]
    execution_error: Optional[str]
    attempt: int
    max_attempts: int
    previous_errors: List[str]
    previous_queries: List[str]
    formatted_result: Optional[str]
    success: bool
    schema: dict