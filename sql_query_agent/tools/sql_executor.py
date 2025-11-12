"""Safe SQL query executor."""

import sqlite3
from typing import Dict, List, Any
import os


class SQLExecutor:
    """Executes SQL queries safely against the database."""
    
    def __init__(self, db_path: str = "data/ecommerce.sqlite"):
        """
        Initialize executor with database path.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        
    def execute(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute SQL query and return results.
        
        Args:
            sql_query: SQL SELECT query to execute
            
        Returns:
            Dictionary with columns and rows
            
        Raises:
            Exception: If query execution fails
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        try:
            # Connect with read-only mode for safety
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Execute query
            cursor.execute(sql_query)
            
            # Fetch results
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            conn.close()
            
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {str(e)}")
        except Exception as e:
            raise Exception(f"Execution error: {str(e)}")