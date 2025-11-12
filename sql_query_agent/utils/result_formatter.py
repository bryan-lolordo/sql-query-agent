"""Result formatter for SQL query outputs."""

from typing import List, Dict, Any, Optional
import pandas as pd


class ResultFormatter:
    """Formats SQL query results for display."""
    
    @staticmethod
    def format_results(
        results: List[Dict[str, Any]], 
        query: str,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Format SQL query results for display.
        
        Args:
            results: List of result rows (each row is a dict)
            query: The SQL query that produced these results
            max_rows: Maximum number of rows to display
            
        Returns:
            Dictionary containing formatted results
        """
        if not results:
            return {
                "success": True,
                "row_count": 0,
                "message": "Query executed successfully but returned no results.",
                "data": [],
                "dataframe": None
            }
        
        # Convert to DataFrame for better formatting
        df = pd.DataFrame(results)
        
        if max_rows and len(df) > max_rows:
            df_display = df.head(max_rows)
            truncated = True
        else:
            df_display = df
            truncated = False
        
        return {
            "success": True,
            "row_count": len(results),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "data": results if not max_rows else results[:max_rows],
            "dataframe": df_display,
            "truncated": truncated,
            "message": ResultFormatter._create_summary_message(len(results), truncated, max_rows)
        }
    
    @staticmethod
    def _create_summary_message(row_count: int, truncated: bool, max_rows: Optional[int]) -> str:
        """Create a summary message for the results."""
        if row_count == 0:
            return "Query executed successfully but returned no results."
        elif row_count == 1:
            return "Query returned 1 row."
        elif truncated:
            return f"Query returned {row_count} rows. Displaying first {max_rows} rows."
        else:
            return f"Query returned {row_count} rows."
    
    @staticmethod
    def format_error(error: str, query: str) -> Dict[str, Any]:
        """
        Format an error message.
        
        Args:
            error: The error message
            query: The SQL query that caused the error
            
        Returns:
            Dictionary containing formatted error
        """
        return {
            "success": False,
            "error": error,
            "query": query,
            "message": f"Query execution failed: {error}"
        }
    
    @staticmethod
    def format_for_display(formatted_result: Dict[str, Any]) -> str:
        """
        Format results as a human-readable string.
        
        Args:
            formatted_result: Result dictionary from format_results()
            
        Returns:
            Human-readable string representation
        """
        if not formatted_result["success"]:
            return f"❌ Error: {formatted_result['error']}"
        
        if formatted_result["row_count"] == 0:
            return "✅ Query executed successfully but returned no results."
        
        output = f"✅ {formatted_result['message']}\n\n"
        
        if formatted_result["dataframe"] is not None:
            output += formatted_result["dataframe"].to_string(index=False)
        
        return output
    
    @staticmethod
    def to_markdown_table(results: List[Dict[str, Any]], max_rows: Optional[int] = 10) -> str:
        """
        Convert results to a markdown table.
        
        Args:
            results: List of result rows
            max_rows: Maximum number of rows to include
            
        Returns:
            Markdown-formatted table string
        """
        if not results:
            return "_No results_"
        
        df = pd.DataFrame(results)
        
        if max_rows and len(df) > max_rows:
            df = df.head(max_rows)
            truncated_note = f"\n\n_Showing {max_rows} of {len(results)} rows_"
        else:
            truncated_note = ""
        
        return df.to_markdown(index=False) + truncated_note
    
    @staticmethod
    def to_csv(results: List[Dict[str, Any]]) -> str:
        """
        Convert results to CSV format.
        
        Args:
            results: List of result rows
            
        Returns:
            CSV-formatted string
        """
        if not results:
            return ""
        
        df = pd.DataFrame(results)
        return df.to_csv(index=False)
    
    @staticmethod
    def get_summary_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics for numeric columns.
        
        Args:
            results: List of result rows
            
        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {}
        
        df = pd.DataFrame(results)
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if not numeric_cols:
            return {"message": "No numeric columns to summarize"}
        
        summary = {}
        for col in numeric_cols:
            summary[col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "std": float(df[col].std()) if len(df) > 1 else 0
            }
        
        return summary