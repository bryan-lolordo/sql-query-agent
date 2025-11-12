"""Database schema analyzer."""

import sqlite3
from typing import Dict, List
import os


class SchemaAnalyzer:
    """Analyzes database schema to provide context for SQL generation."""
    
    def __init__(self, db_path: str = "sample_data/sample_db.sqlite"):
        """
        Initialize analyzer with database path.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
    
    def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get complete database schema.
        
        Returns:
            Dictionary mapping table names to their column definitions
        """
        if not os.path.exists(self.db_path):
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            schema = {}
            
            for (table_name,) in tables:
                # Get column info for each table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                schema[table_name] = [
                    {
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "primary_key": bool(col[5])
                    }
                    for col in columns
                ]
            
            conn.close()
            
            return schema
            
        except sqlite3.Error as e:
            print(f"Error reading schema: {e}")
            return {}
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names."""
        schema = self.get_schema()
        return list(schema.keys())
    
    def get_columns(self, table_name: str) -> List[str]:
        """Get column names for a specific table."""
        schema = self.get_schema()
        if table_name in schema:
            return [col["name"] for col in schema[table_name]]
        return []
    
    def format_schema_for_llm(self) -> str:
        """Format schema in a readable way for LLM context."""
        schema = self.get_schema()
        
        if not schema:
            return "No schema available"
        
        formatted = []
        for table_name, columns in schema.items():
            col_info = ", ".join([
                f"{col['name']} ({col['type']}{'*' if col['primary_key'] else ''})"
                for col in columns
            ])
            formatted.append(f"{table_name}: [{col_info}]")
        
        return "\n".join(formatted)