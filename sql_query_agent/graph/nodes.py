"""Node functions for the SQL Query Agent graph."""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate  # FIXED: Changed from langchain.prompts

from ..tools.sql_validator import SQLValidator
from ..tools.sql_executor import SQLExecutor
from ..tools.schema_analyzer import SchemaAnalyzer
from ..utils.error_analyzer import ErrorAnalyzer
from ..utils.result_formatter import ResultFormatter
from .state import SQLAgentState


llm = ChatOpenAI(model="gpt-4", temperature=0)
validator = SQLValidator()
executor = SQLExecutor()
schema_analyzer = SchemaAnalyzer()
error_analyzer = ErrorAnalyzer()
result_formatter = ResultFormatter()


def parse_intent(state: SQLAgentState) -> Dict[str, Any]:
    """Parse user's intent and prepare context for SQL generation."""
    
    user_query = state["user_query"]
    schema = state.get("schema", {})
    
    # Analyze schema if not already done
    if not schema:
        schema = schema_analyzer.get_schema()
    
    return {
        "schema": schema,
        "attempt": 1,
        "max_attempts": 3,
        "previous_errors": [],
        "previous_queries": [],
        "success": False
    }


def generate_sql(state: SQLAgentState) -> Dict[str, Any]:
    """Generate SQL query from natural language with error context."""
    
    user_query = state["user_query"]
    schema = state["schema"]
    previous_errors = state.get("previous_errors", [])
    previous_queries = state.get("previous_queries", [])
    attempt = state.get("attempt", 1)
    
    # Format schema for prompt
    schema_str = ""
    for table_name, columns in schema.items():
        col_info = ", ".join([
            f"{col['name']} ({col['type']}{'*' if col.get('primary_key') else ''})"
            for col in columns
        ])
        schema_str += f"{table_name}: [{col_info}]\n"
    
    # Build context-aware prompt
    error_context = ""
    if previous_errors:
        error_context = "\n\nPrevious attempts failed with these errors:\n"
        for i, (query, error) in enumerate(zip(previous_queries, previous_errors)):
            error_context += f"\nAttempt {i+1}:\nSQL: {query}\nError: {error}\n"
        error_context += "\nPlease fix these issues in your new query."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert SQL query generator. Generate a valid SQL query based on the user's natural language request.

Database Schema:
{schema}

Rules:
- Generate ONLY the SQL query, no explanations
- Use proper SQLite syntax
- Be specific with column names from the schema
- Use appropriate WHERE, JOIN, GROUP BY, ORDER BY clauses
{error_context}"""),
        ("user", "{user_query}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "user_query": user_query,
        "schema": schema_str,
        "error_context": error_context
    })
    
    sql_query = response.content.strip()
    
    # Clean up SQL (remove markdown, extra whitespace)
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    
    return {
        "sql_query": sql_query,
        "attempt": attempt
    }


def validate_sql(state: SQLAgentState) -> Dict[str, Any]:
    """Validate SQL syntax."""
    
    sql_query = state["sql_query"]
    is_valid, error = validator.validate(sql_query)
    
    if not is_valid:
        # Add to error history
        previous_errors = state.get("previous_errors", [])
        previous_queries = state.get("previous_queries", [])
        
        return {
            "execution_error": f"Syntax Error: {error}",
            "previous_errors": previous_errors + [f"Syntax Error: {error}"],
            "previous_queries": previous_queries + [sql_query],
            "attempt": state["attempt"] + 1
        }
    
    return {}


def execute_sql(state: SQLAgentState) -> Dict[str, Any]:
    """Execute SQL query safely."""
    
    sql_query = state["sql_query"]
    
    try:
        result = executor.execute(sql_query)
        
        # Convert to list of dicts for easier handling
        rows_as_dicts = [
            {col: val for col, val in zip(result["columns"], row)}
            for row in result["rows"]
        ]
        
        return {
            "execution_result": {
                "columns": result["columns"],
                "rows": result["rows"],
                "data": rows_as_dicts,
                "row_count": result["row_count"]
            },
            "execution_error": None,
            "success": True
        }
    except Exception as e:
        # Add to error history
        previous_errors = state.get("previous_errors", [])
        previous_queries = state.get("previous_queries", [])
        error_msg = str(e)
        
        return {
            "execution_error": error_msg,
            "previous_errors": previous_errors + [error_msg],
            "previous_queries": previous_queries + [sql_query],
            "attempt": state["attempt"] + 1,
            "success": False
        }


def analyze_error(state: SQLAgentState) -> Dict[str, Any]:
    """Analyze execution error to provide better context for retry."""
    
    error = state.get("execution_error", "")
    sql_query = state["sql_query"]
    previous_errors = state.get("previous_errors", [])
    
    # Use error analyzer to get detailed info
    analysis = ErrorAnalyzer.analyze_error(error, sql_query)
    problem_area = ErrorAnalyzer.extract_problem_area(error, sql_query)
    
    # Format enhanced error message
    enhanced_error = f"{error}\n\n"
    enhanced_error += f"Error Type: {analysis['error_type']}\n"
    enhanced_error += f"Suggestion: {analysis['suggested_fix']}\n"
    
    if problem_area:
        enhanced_error += f"Problem Area: {problem_area}\n"
    
    return {
        "execution_error": enhanced_error
    }


def format_results(state: SQLAgentState) -> Dict[str, Any]:
    """Format query results for display."""
    
    result = state["execution_result"]
    sql_query = state["sql_query"]
    
    # Use result formatter
    formatted = ResultFormatter.format_results(
        result.get("data", []),
        sql_query,
        max_rows=100
    )
    
    return {
        "formatted_result": formatted
    }


def ask_clarification(state: SQLAgentState) -> Dict[str, Any]:
    """Ask user for clarification after max attempts."""
    
    previous_errors = state["previous_errors"]
    user_query = state["user_query"]
    
    clarification = f"""Unable to generate a working SQL query after {state['max_attempts']} attempts.

Original query: {user_query}

Errors encountered:
"""
    for i, error in enumerate(previous_errors, 1):
        clarification += f"\n{i}. {error}"
    
    clarification += "\n\nPlease try:\n- Rephrasing your question\n- Being more specific about column names\n- Checking if the data you're asking for exists"
    
    return {
        "formatted_result": clarification
    }