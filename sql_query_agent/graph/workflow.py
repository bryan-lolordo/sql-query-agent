"""Build the LangGraph workflow for SQL Query Agent."""

from langgraph.graph import StateGraph, END
from .state import SQLAgentState
from .nodes import (
    parse_intent,
    generate_sql,
    validate_sql,
    execute_sql,
    analyze_error,
    format_results,
    ask_clarification
)
from .conditions import should_retry, is_valid_sql


def build_graph():
    """Build and compile the SQL Query Agent graph."""
    
    # Initialize the graph
    workflow = StateGraph(SQLAgentState)
    
    # Add nodes
    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("validate_sql", validate_sql)
    workflow.add_node("execute_sql", execute_sql)
    workflow.add_node("analyze_error", analyze_error)
    workflow.add_node("format_results", format_results)
    workflow.add_node("ask_clarification", ask_clarification)
    
    # Set entry point
    workflow.set_entry_point("parse_intent")
    
    # Add edges
    workflow.add_edge("parse_intent", "generate_sql")
    workflow.add_edge("generate_sql", "validate_sql")
    
    # Conditional routing after validation
    workflow.add_conditional_edges(
        "validate_sql",
        is_valid_sql,
        {
            "execute_sql": "execute_sql",
            "generate_sql": "generate_sql"
        }
    )
    
    # Conditional routing after execution
    workflow.add_conditional_edges(
        "execute_sql",
        should_retry,
        {
            "format_results": "format_results",
            "analyze_error": "analyze_error",
            "ask_clarification": "ask_clarification"
        }
    )
    
    # After error analysis, regenerate SQL
    workflow.add_edge("analyze_error", "generate_sql")
    
    # Terminal nodes
    workflow.add_edge("format_results", END)
    workflow.add_edge("ask_clarification", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app