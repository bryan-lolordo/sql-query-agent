"""Node functions for the SQL Query Agent graph."""

import logging
import time
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..tools.sql_validator import SQLValidator
from ..tools.sql_executor import SQLExecutor
from ..tools.schema_analyzer import SchemaAnalyzer
from ..utils.error_analyzer import ErrorAnalyzer
from ..utils.result_formatter import ResultFormatter
from .state import SQLAgentState

# Configure logging
logger = logging.getLogger(__name__)

# Observatory imports
from observatory_config import track_llm_call, create_routing_decision, create_cache_metadata

# Initialize tools
llm = ChatOpenAI(model="gpt-4", temperature=0)
validator = SQLValidator()
executor = SQLExecutor()
schema_analyzer = SchemaAnalyzer()
error_analyzer = ErrorAnalyzer()
result_formatter = ResultFormatter()


def parse_intent(state: SQLAgentState) -> Dict[str, Any]:
    """Parse user's intent and prepare context for SQL generation."""
    
    logger.info("="*80)
    logger.info("🔍 NODE 1: Parse Intent")
    logger.info("="*80)
    
    user_query = state["user_query"]
    schema = state.get("schema", {})
    
    logger.info(f"   Query: {user_query[:60]}...")
    
    # Analyze schema if not already done
    if not schema:
        logger.info("   📊 Extracting database schema...")
        schema = schema_analyzer.get_schema()
        logger.info(f"   ✅ Schema extracted: {len(schema)} tables")
    
    # ONLY initialize these if they don't exist (first run)
    updates = {"schema": schema}
    
    # Don't overwrite attempt if it already exists
    if "attempt" not in state:
        updates["attempt"] = 1
    if "max_attempts" not in state:
        updates["max_attempts"] = 3
    if "previous_errors" not in state:
        updates["previous_errors"] = []
    if "previous_queries" not in state:
        updates["previous_queries"] = []
    if "success" not in state:
        updates["success"] = False
    
    logger.info(f"   ✅ Intent parsed - Ready for attempt {updates.get('attempt', state.get('attempt', 1))}")
    
    return updates


def generate_sql(state: SQLAgentState) -> Dict[str, Any]:
    """Generate SQL query from natural language with error context."""
    
    user_query = state["user_query"]
    schema = state["schema"]
    previous_errors = state.get("previous_errors", [])
    previous_queries = state.get("previous_queries", [])
    attempt = state.get("attempt", 1)

    logger.info("-"*80)
    logger.info(f"⚙️  NODE 2: Generate SQL (Attempt {attempt})")
    logger.info("-"*80)
    
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
        logger.info(f"   📚 Learning from {len(previous_errors)} previous error(s)")
        error_context = "\n\nPrevious attempts failed with these errors:\n"
        for i, (query, error) in enumerate(zip(previous_queries, previous_errors)):
            error_context += f"\nAttempt {i+1}:\nSQL: {query}\nError: {error}\n"
        error_context += "\nPlease fix these issues in your new query."
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert SQL query generator. Generate a valid SQL query based on the user's natural language request.

Database Schema:
{schema}

Rules:
- Generate ONLY the SQL query, no explanations or text
- If the requested table doesn't exist in the schema, create a SELECT query anyway using the closest matching table
- Use proper SQLite syntax
- Be specific with column names from the schema
- Use appropriate WHERE, JOIN, GROUP BY, ORDER BY clauses
- NEVER respond with explanatory text - ONLY SQL code
{error_context}"""),
        ("user", "{user_query}")
    ])
    
    prompt_text = f"Generate SQL for: {user_query}\nSchema: {schema_str[:200]}..."
    
    logger.info("   🤖 Calling GPT-4 to generate SQL...")
    
    # Routing decision (always GPT-4 for SQL generation)
    routing = create_routing_decision(
        chosen_model="gpt-4",
        alternative_models=["gpt-4o-mini"],
        reasoning="Complex SQL generation requires premium model"
    )
    
    chain = prompt_template | llm
    
    start_time = time.time()
    response = chain.invoke({
        "user_query": user_query,
        "schema": schema_str,
        "error_context": error_context
    })
    latency_ms = (time.time() - start_time) * 1000
    
    sql_query = response.content.strip()
    
    # Clean up SQL (remove markdown, extra whitespace)
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    
    logger.info(f"   ✅ SQL Generated in {latency_ms:.0f}ms")
    logger.info(f"   📝 Query: {sql_query[:100]}...")
    
    # Track in Observatory
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=len(prompt_text.split()) * 1.3,  # Estimate
        completion_tokens=len(sql_query.split()) * 1.3,
        latency_ms=latency_ms,
        agent_name="SQLGenerator",
        operation="generate_sql",
        prompt=prompt_text,
        response_text=sql_query,
        routing_decision=routing
    )
    
    return {
        "sql_query": sql_query,
        "attempt": attempt
    }


def validate_sql(state: SQLAgentState) -> Dict[str, Any]:
    """Validate SQL syntax."""
    
    sql_query = state["sql_query"]
    attempt = state.get("attempt", 1)
    
    logger.info("-"*80)
    logger.info("✅ NODE 3: Validate SQL")
    logger.info("-"*80)
    
    is_valid, error = validator.validate(sql_query)
    
    if not is_valid:
        logger.warning(f"   ❌ Validation failed: {error}")
        
        # Add to error history
        previous_errors = state.get("previous_errors", [])
        previous_queries = state.get("previous_queries", [])
        
        return {
            "execution_error": f"Syntax Error: {error}",
            "previous_errors": previous_errors + [f"Syntax Error: {error}"],
            "previous_queries": previous_queries + [sql_query],
            "attempt": attempt + 1,
            "success": False
        }
    
    logger.info("   ✅ Syntax valid")
    return {
        "execution_error": None
    }


def execute_sql(state: SQLAgentState) -> Dict[str, Any]:
    """Execute SQL query safely."""
    
    sql_query = state["sql_query"]
    attempt = state.get("attempt", 1)

    logger.info("-"*80)
    logger.info(f"🚀 NODE 4: Execute SQL (Attempt {attempt})")
    logger.info("-"*80)
    logger.info(f"   Executing: {sql_query[:80]}...")
    
    start_time = time.time()
    
    try:
        result = executor.execute(sql_query)
        
        execution_time = (time.time() - start_time) * 1000
        
        logger.info(f"   ✅ SUCCESS in {execution_time:.0f}ms!")
        logger.info(f"   📊 Rows returned: {result['row_count']}")
        
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
        execution_time = (time.time() - start_time) * 1000
        
        logger.error(f"   ❌ FAILED after {execution_time:.0f}ms")
        logger.error(f"   Error: {str(e)[:100]}")
        
        # Add to error history
        previous_errors = state.get("previous_errors", [])
        previous_queries = state.get("previous_queries", [])
        error_msg = str(e)
        
        return {
            "execution_error": error_msg,
            "previous_errors": previous_errors + [error_msg],
            "previous_queries": previous_queries + [sql_query],
            "attempt": attempt + 1,
            "success": False
        }


def analyze_error(state: SQLAgentState) -> Dict[str, Any]:
    """Analyze execution error to provide better context for retry."""
    
    error = state.get("execution_error", "")
    sql_query = state["sql_query"]
    attempt = state.get("attempt", 1)
    
    logger.info("-"*80)
    logger.info(f"🔍 NODE 5: Analyze Error (Attempt {attempt})")
    logger.info("-"*80)
    logger.info(f"   Error: {error[:80]}...")
    
    # Use error analyzer to get detailed info
    analysis = ErrorAnalyzer.analyze_error(error, sql_query)
    problem_area = ErrorAnalyzer.extract_problem_area(error, sql_query)
    
    logger.info(f"   🧠 Error Type: {analysis['error_type']}")
    logger.info(f"   💡 Suggestion: {analysis['suggested_fix'][:60]}...")
    
    # Format enhanced error message
    enhanced_error = f"{error}\n\n"
    enhanced_error += f"Error Type: {analysis['error_type']}\n"
    enhanced_error += f"Suggestion: {analysis['suggested_fix']}\n"
    
    if problem_area:
        enhanced_error += f"Problem Area: {problem_area}\n"
        logger.info(f"   🎯 Problem Area: {problem_area}")
    
    logger.info("   ✅ Error analyzed, will retry with improvements")
    
    return {
        "execution_error": enhanced_error,
        "attempt": attempt
    }


def format_results(state: SQLAgentState) -> Dict[str, Any]:
    """Format query results for display."""
    
    logger.info("-"*80)
    logger.info("📝 NODE 6: Format Results")
    logger.info("-"*80)
    
    result = state["execution_result"]
    sql_query = state["sql_query"]
    
    # Use result formatter
    formatted = ResultFormatter.format_results(
        result.get("data", []),
        sql_query,
        max_rows=100
    )
    
    logger.info("   ✅ Results formatted for display")
    logger.info("="*80)
    
    return {
        "formatted_result": formatted
    }


def ask_clarification(state: SQLAgentState) -> Dict[str, Any]:
    """Ask user for clarification after max attempts."""
    
    logger.info("-"*80)
    logger.info("❌ NODE 7: Ask Clarification (Max Attempts Reached)")
    logger.info("-"*80)
    
    previous_errors = state["previous_errors"]
    user_query = state["user_query"]
    
    logger.warning(f"   Failed after {state['max_attempts']} attempts")
    logger.warning(f"   Errors: {len(previous_errors)}")
    
    clarification = f"""Unable to generate a working SQL query after {state['max_attempts']} attempts.

Original query: {user_query}

Errors encountered:
"""
    for i, error in enumerate(previous_errors, 1):
        clarification += f"\n{i}. {error}"
    
    clarification += "\n\nPlease try:\n- Rephrasing your question\n- Being more specific about column names\n- Checking if the data you're asking for exists"
    
    logger.info("="*80)
    
    return {
        "formatted_result": clarification
    }