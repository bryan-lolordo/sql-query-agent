"""Error analyzer for parsing and understanding SQL execution errors."""

from typing import Dict, Optional
import re


class ErrorAnalyzer:
    """Analyzes SQL errors and provides helpful context for fixing queries."""
    
    @staticmethod
    def analyze_error(error: str, sql_query: str) -> Dict[str, any]:
        """
        Analyze a SQL error and extract useful information.
        
        Args:
            error: The error message from SQL execution
            sql_query: The SQL query that caused the error
            
        Returns:
            Dictionary containing error analysis
        """
        analysis = {
            "error_type": ErrorAnalyzer._classify_error(error),
            "error_message": error,
            "suggested_fix": ErrorAnalyzer._suggest_fix(error),
            "problematic_query": sql_query
        }
        
        return analysis
    
    @staticmethod
    def _classify_error(error: str) -> str:
        """Classify the type of SQL error."""
        error_lower = error.lower()
        
        if "no such table" in error_lower:
            return "TABLE_NOT_FOUND"
        elif "no such column" in error_lower:
            return "COLUMN_NOT_FOUND"
        elif "syntax error" in error_lower:
            return "SYNTAX_ERROR"
        elif "ambiguous column" in error_lower:
            return "AMBIGUOUS_COLUMN"
        elif "datatype mismatch" in error_lower or "type mismatch" in error_lower:
            return "TYPE_MISMATCH"
        elif "constraint" in error_lower:
            return "CONSTRAINT_VIOLATION"
        elif "function" in error_lower and "does not exist" in error_lower:
            return "FUNCTION_NOT_SUPPORTED"
        else:
            return "UNKNOWN_ERROR"
    
    @staticmethod
    def _suggest_fix(error: str) -> str:
        """Provide a suggestion for fixing the error."""
        error_lower = error.lower()
        
        suggestions = {
            "no such table": "Verify the table name exists in the database schema. Check for typos or case sensitivity.",
            "no such column": "Check that the column name is spelled correctly and exists in the specified table.",
            "syntax error": "Review SQL syntax. Common issues: missing commas, incorrect keyword order, or unmatched parentheses.",
            "ambiguous column": "Prefix column names with table names or aliases to clarify which table the column belongs to.",
            "datatype mismatch": "Ensure data types match between compared values. Cast values if necessary.",
            "type mismatch": "Ensure data types match between compared values. Cast values if necessary.",
            "constraint": "Check for constraint violations like NOT NULL, UNIQUE, or FOREIGN KEY constraints.",
            "function": "The function may not be supported in this database. Check database-specific function syntax (e.g., SQLite vs PostgreSQL)."
        }
        
        for key, suggestion in suggestions.items():
            if key in error_lower:
                return suggestion
        
        return "Review the error message and SQL query carefully. Consult database documentation if needed."
    
    @staticmethod
    def extract_problem_area(error: str, sql_query: str) -> Optional[str]:
        """
        Try to extract the specific part of the query causing the issue.
        
        Args:
            error: The error message
            sql_query: The SQL query
            
        Returns:
            The problematic part of the query if identifiable, None otherwise
        """
        # Try to extract table name from "no such table" errors
        table_match = re.search(r'no such table:\s*(\w+)', error, re.IGNORECASE)
        if table_match:
            return f"Table: {table_match.group(1)}"
        
        # Try to extract column name from "no such column" errors
        column_match = re.search(r'no such column:\s*(\w+)', error, re.IGNORECASE)
        if column_match:
            return f"Column: {column_match.group(1)}"
        
        # Try to extract function name from function errors
        function_match = re.search(r'no such function:\s*(\w+)', error, re.IGNORECASE)
        if function_match:
            return f"Function: {function_match.group(1)}"
        
        return None
    
    @staticmethod
    def format_error_for_llm(error: str, sql_query: str, previous_errors: list) -> str:
        """
        Format error information for feeding back to the LLM.
        
        Args:
            error: Current error message
            sql_query: The SQL query that failed
            previous_errors: List of previous error messages
            
        Returns:
            Formatted string for LLM context
        """
        analysis = ErrorAnalyzer.analyze_error(error, sql_query)
        problem_area = ErrorAnalyzer.extract_problem_area(error, sql_query)
        
        context = f"""
Previous Query Failed:
{sql_query}

Error Type: {analysis['error_type']}
Error Message: {error}
"""
        
        if problem_area:
            context += f"Problem Area: {problem_area}\n"
        
        context += f"Suggestion: {analysis['suggested_fix']}\n"
        
        if previous_errors:
            context += f"\nPrevious Attempts: {len(previous_errors)}\n"
            context += "Learn from these past errors:\n"
            for i, prev_error in enumerate(previous_errors[-2:], 1):  # Show last 2 errors
                context += f"{i}. {prev_error}\n"
        
        return context