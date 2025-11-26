"""Build the LangGraph workflow for SQL Query Agent."""

import logging
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

# Configure logging
logger = logging.getLogger(__name__)

# Observatory imports
from observatory_config import start_tracking_session, end_tracking_session


def build_graph():
    """Build and compile the SQL Query Agent graph."""
    
    logger.info("🔧 Building LangGraph workflow...")
    
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
    
    logger.info("✅ Workflow compiled successfully")
    
    return app


class TrackedWorkflow:
    """Wrapper that adds Observatory session tracking to workflow"""
    
    def __init__(self, workflow):
        self.workflow = workflow
    
    def invoke(self, state):
        """Run workflow with session tracking"""
        
        user_query = state.get("user_query", "Unknown query")
        
        logger.info("\n" + "="*80)
        logger.info("🚀 SQL QUERY AGENT - Starting Workflow")
        logger.info("="*80)
        logger.info(f"📝 Query: {user_query[:80]}...")
        logger.info("="*80 + "\n")
        
        # Start Observatory session
        session = start_tracking_session(
            operation_type="sql_query_workflow",
            metadata={
                "query": user_query[:200],
                "max_attempts": state.get("max_attempts", 3)
            }
        )
        
        try:
            # Run workflow
            result = self.workflow.invoke(state)
            
            # Determine success
            success = result.get("success", False)
            error = None if success else result.get("execution_error")
            
            logger.info("\n" + "="*80)
            logger.info("📊 WORKFLOW COMPLETE")
            logger.info("="*80)
            logger.info(f"✅ Success: {success}")
            logger.info(f"🔄 Attempts: {result.get('attempt', 'N/A')}")
            
            if success and result.get("execution_result"):
                row_count = result["execution_result"].get("row_count", 0)
                logger.info(f"📊 Rows returned: {row_count}")
            elif not success:
                logger.warning(f"❌ Final status: Failed")
                if result.get("previous_errors"):
                    logger.warning(f"   Errors encountered: {len(result['previous_errors'])}")
            
            logger.info("="*80 + "\n")
            
            # End session
            end_tracking_session(session, success=success, error=error)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow failed with exception: {e}")
            
            # End session with error
            end_tracking_session(session, success=False, error=str(e))
            
            raise


def create_graph(db_path: str = "data/ecommerce.sqlite"):
    """
    Create and return the compiled graph with database path and Observatory tracking.
    
    Note: This modifies the global instances in nodes.py.
    A better approach would be to pass db_path through state.
    """
    logger.info(f"📦 Creating SQL Query Agent workflow")
    logger.info(f"   Database: {db_path}")
    
    # Import here to avoid circular imports
    from . import nodes
    from ..tools.sql_executor import SQLExecutor
    from ..tools.schema_analyzer import SchemaAnalyzer
    
    # Update the global instances in nodes.py with the new db_path
    nodes.executor = SQLExecutor(db_path)
    nodes.schema_analyzer = SchemaAnalyzer(db_path)
    
    # Build and wrap workflow
    workflow = build_graph()
    tracked_workflow = TrackedWorkflow(workflow)
    
    logger.info("✅ SQL Query Agent ready\n")
    
    return tracked_workflow