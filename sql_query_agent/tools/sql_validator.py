"""SQL syntax validator."""

import sqlparse
from typing import Tuple


class SQLValidator:
    """Validates SQL query syntax."""
    
    def __init__(self):
        self.dangerous_keywords = [
            "DROP", "DELETE", "TRUNCATE", "ALTER", 
            "CREATE", "INSERT", "UPDATE", "GRANT", 
            "REVOKE", "EXEC", "EXECUTE"
        ]
    
    def validate(self, sql_query: str) -> Tuple[bool, str]:
        """
        Validate SQL syntax and safety.
        
        Args:
            sql_query: SQL query string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql_query or not sql_query.strip():
            return False, "Empty query"
        
        # Check for dangerous operations
        sql_upper = sql_query.upper()
        for keyword in self.dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Dangerous operation detected: {keyword}. Only SELECT queries are allowed."
        
        # Parse SQL
        try:
            parsed = sqlparse.parse(sql_query)
            
            if not parsed:
                return False, "Unable to parse SQL query"
            
            # Check if it's a SELECT statement
            statement = parsed[0]
            if statement.get_type() != "SELECT":
                return False, f"Only SELECT queries are allowed. Found: {statement.get_type()}"
            
            return True, ""
            
        except Exception as e:
            return False, f"SQL parsing error: {str(e)}"