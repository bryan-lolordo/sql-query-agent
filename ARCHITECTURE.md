# Architecture Documentation

## Overview

The SQL Query Agent is built on **LangGraph**, a framework for creating stateful, cyclical AI workflows. Unlike linear chains, LangGraph enables the agent to loop back, learn from mistakes, and retry with improved context.

## Why LangGraph?

### The Problem with Linear Workflows

Traditional LLM pipelines are linear:

```
User Query → Generate SQL → Execute → Return Result
```

If the SQL fails, the pipeline fails. No recovery. No learning.

### The LangGraph Solution

LangGraph enables **cyclical workflows**:

```
User Query → Generate SQL → Execute → Failed? → Analyze → Learn → Retry!
                                         ↑__________________________|
```

The agent can:
- Detect failures
- Analyze what went wrong
- Inject error context into the next attempt
- Retry with learned knowledge
- Give up gracefully after max attempts

## State Machine Design

### Visual Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SQL Query Agent                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐                                                  │
│   │    START     │                                                  │
│   └──────┬───────┘                                                  │
│          ↓                                                          │
│   ┌──────────────┐                                                  │
│   │ Parse Intent │  ← Analyze schema, initialize state              │
│   └──────┬───────┘                                                  │
│          ↓                                                          │
│   ┌──────────────┐                                                  │
│   │ Generate SQL │  ← LLM creates query with error context          │
│   └──────┬───────┘                                                  │
│          ↓                                                          │
│   ┌──────────────┐                                                  │
│   │ Validate SQL │  ← Check syntax, block dangerous ops             │
│   └──────┬───────┘                                                  │
│          ↓                                                          │
│   ┌─────────────────┐                                               │
│   │  is_valid_sql?  │ ─── No ──→ (loop to Generate SQL)             │
│   └────────┬────────┘                                               │
│            ↓ Yes                                                    │
│   ┌──────────────┐                                                  │
│   │  Execute SQL │  ← Run against database                          │
│   └──────┬───────┘                                                  │
│          ↓                                                          │
│   ┌─────────────────┐                                               │
│   │  should_retry?  │                                               │
│   └────────┬────────┘                                               │
│            │                                                        │
│    ┌───────┼───────┐                                                │
│    ↓       ↓       ↓                                                │
│ Success  Error   Max Attempts                                       │
│    ↓       ↓       ↓                                                │
│ ┌──────┐ ┌──────┐ ┌──────────────┐                                  │
│ │Format│ │Analyze│ │Ask Clarify  │                                  │
│ │Result│ │Error │ │             │                                  │
│ └──┬───┘ └──┬───┘ └──────┬──────┘                                  │
│    ↓        │            ↓                                          │
│   END       │           END                                         │
│             ↓                                                       │
│      (loop to Generate SQL)                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### State Definition

```python
class SQLAgentState(TypedDict):
    # User Input
    user_query: str              # Original natural language query
    
    # Current Attempt
    sql_query: str               # Generated SQL statement
    execution_result: dict       # Query results (if successful)
    execution_error: str         # Error message (if failed)
    
    # Retry Tracking
    attempt: int                 # Current attempt number (1-3)
    max_attempts: int            # Maximum retries allowed
    
    # Learning Context
    previous_errors: list        # History of errors for learning
    previous_queries: list       # History of SQL attempts
    
    # Output
    formatted_result: str        # Human-readable output
    success: bool                # Whether query succeeded
    
    # Context
    schema: dict                 # Database schema for LLM context
```

### Why This State Design?

| Field | Purpose |
|-------|---------|
| `previous_errors` | Fed back to LLM so it learns from mistakes |
| `previous_queries` | Shows LLM what was already tried |
| `attempt` | Controls retry loop termination |
| `execution_error` | Used for routing decisions |
| `schema` | Gives LLM context about valid tables/columns |

## Components

### Nodes (graph/nodes.py)

Each node is a Python function that:
1. Receives the current state
2. Performs ONE specific task
3. Returns updates to the state

```python
def node_function(state: SQLAgentState) -> Dict[str, Any]:
    # Read from state
    input_data = state["some_field"]
    
    # Do work
    result = process(input_data)
    
    # Return state updates (merged with existing state)
    return {"output_field": result}
```

#### Node Descriptions

| Node | Purpose | Key Logic |
|------|---------|-----------|
| `parse_intent` | Initialize state, get schema | Only runs once at start |
| `generate_sql` | Create SQL from natural language | Includes error context on retries |
| `validate_sql` | Check syntax & safety | Blocks dangerous operations |
| `execute_sql` | Run query against database | Catches execution errors |
| `analyze_error` | Understand what went wrong | Classifies error type, suggests fixes |
| `format_results` | Create readable output | Converts to DataFrame |
| `ask_clarification` | Request user help | Lists all errors, suggests alternatives |

### Conditions (graph/conditions.py)

Conditions are routing functions that determine which node runs next.

#### should_retry()

```python
def should_retry(state) -> Literal["format_results", "analyze_error", "ask_clarification"]:
    if state["success"]:
        return "format_results"      # Query worked!
    elif state["attempt"] <= state["max_attempts"]:
        return "analyze_error"       # Try again
    else:
        return "ask_clarification"   # Give up gracefully
```

#### is_valid_sql()

```python
def is_valid_sql(state) -> Literal["execute_sql", "generate_sql"]:
    if state["execution_error"] and "Syntax Error" in state["execution_error"]:
        return "generate_sql"        # Invalid syntax, regenerate
    else:
        return "execute_sql"         # Valid, try executing
```

### Tools

#### SQLValidator (tools/sql_validator.py)

**Purpose:** Ensure queries are safe before execution

**Safety Checks:**
- Only SELECT queries allowed
- Blocks dangerous keywords: DROP, DELETE, UPDATE, INSERT, etc.
- Validates SQL syntax with sqlparse

```python
# Blocked keywords
dangerous_keywords = [
    "DROP", "DELETE", "TRUNCATE", "ALTER",
    "CREATE", "INSERT", "UPDATE", "GRANT",
    "REVOKE", "EXEC", "EXECUTE"
]
```

#### SQLExecutor (tools/sql_executor.py)

**Purpose:** Safely execute queries against the database

**Safety Features:**
- Opens database in **read-only mode**
- Catches all execution errors
- Returns structured results

```python
# Read-only connection
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
```

#### SchemaAnalyzer (tools/schema_analyzer.py)

**Purpose:** Provide database context to the LLM

**Output Format:**
```
customers: [customer_id (INTEGER*), name (TEXT), email (TEXT), city (TEXT)]
products: [product_id (INTEGER*), product_name (TEXT), category (TEXT), price (REAL)]
orders: [order_id (INTEGER*), customer_id (INTEGER), product_id (INTEGER), ...]
```

The `*` indicates primary key columns.

### Utils

#### ErrorAnalyzer (utils/error_analyzer.py)

**Purpose:** Classify errors and suggest fixes

**Error Types:**
| Type | Example | Suggestion |
|------|---------|------------|
| `TABLE_NOT_FOUND` | "no such table: employees" | Check table names in schema |
| `COLUMN_NOT_FOUND` | "no such column: phone" | Verify column exists |
| `SYNTAX_ERROR` | "near 'FORM': syntax error" | Check SQL syntax |
| `TYPE_MISMATCH` | "datatype mismatch" | Cast values appropriately |

#### ResultFormatter (utils/result_formatter.py)

**Purpose:** Format query results for display

**Features:**
- Converts to pandas DataFrame
- Truncates long results
- Generates summary messages
- Export to CSV/markdown

## Workflow Construction

### Graph Building (workflow.py)

```python
def build_graph():
    # 1. Create graph with state type
    workflow = StateGraph(SQLAgentState)
    
    # 2. Add nodes
    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("validate_sql", validate_sql)
    workflow.add_node("execute_sql", execute_sql)
    workflow.add_node("analyze_error", analyze_error)
    workflow.add_node("format_results", format_results)
    workflow.add_node("ask_clarification", ask_clarification)
    
    # 3. Set entry point
    workflow.set_entry_point("parse_intent")
    
    # 4. Add simple edges (always follow this path)
    workflow.add_edge("parse_intent", "generate_sql")
    workflow.add_edge("generate_sql", "validate_sql")
    workflow.add_edge("analyze_error", "generate_sql")  # Retry loop!
    
    # 5. Add conditional edges (routing based on state)
    workflow.add_conditional_edges(
        "validate_sql",
        is_valid_sql,
        {"execute_sql": "execute_sql", "generate_sql": "generate_sql"}
    )
    
    workflow.add_conditional_edges(
        "execute_sql",
        should_retry,
        {
            "format_results": "format_results",
            "analyze_error": "analyze_error",
            "ask_clarification": "ask_clarification"
        }
    )
    
    # 6. Add terminal edges
    workflow.add_edge("format_results", END)
    workflow.add_edge("ask_clarification", END)
    
    # 7. Compile and return
    return workflow.compile()
```

## Self-Correction Mechanism

### How Learning Works

The key insight: **each retry includes context from all previous failures**.

#### Prompt Structure on Retry

```
System: You are an expert SQL query generator.

Database Schema:
customers: [customer_id, name, email, city, country]
products: [product_id, product_name, category, price]
orders: [order_id, customer_id, product_id, order_date, quantity, total_amount, status]

Previous attempts failed with these errors:

Attempt 1:
SQL: SELECT * FROM employees
Error: Database error: no such table: employees

Attempt 2:
SQL: SELECT * FROM staff
Error: Database error: no such table: staff

Please fix these issues in your new query.

User: Show me all employees and their salaries
```

The LLM sees:
1. What tables actually exist (schema)
2. What was tried before (previous_queries)
3. Why each attempt failed (previous_errors)
4. Clear instruction to fix the issues

### Why This Works

| Attempt | LLM Knowledge | Behavior |
|---------|--------------|----------|
| 1 | Only schema | May guess wrong table names |
| 2 | Schema + 1 error | Knows one guess was wrong |
| 3 | Schema + 2 errors | Has enough context to adapt |

By attempt 3, the LLM has learned:
- "employees" doesn't exist
- "staff" doesn't exist
- Only "customers", "products", "orders" exist

It can then make a reasonable choice (map to closest table) or admit the data doesn't exist.

## Error Handling Patterns

### Validation Errors

```
validate_sql ─→ Error ─→ is_valid_sql ─→ generate_sql (retry)
```

Caught before execution. Fast feedback loop.

### Execution Errors

```
execute_sql ─→ Error ─→ should_retry ─→ analyze_error ─→ generate_sql (retry)
```

Error is analyzed first, then used to improve next attempt.

### Max Attempts Reached

```
execute_sql ─→ Error ─→ should_retry ─→ ask_clarification ─→ END
```

Graceful degradation with helpful error messages.

## Design Decisions

### Why 3 Max Attempts?

- **1 attempt:** No self-correction (just a chain)
- **2 attempts:** Often not enough to converge
- **3 attempts:** Usually sufficient; more adds latency without benefit
- **5+ attempts:** Diminishing returns, user frustration

3 is the sweet spot for most queries.

### Why Separate Validation and Execution?

**Separation of concerns:**
- Validation is fast (no DB call)
- Execution can be slow
- Different error types need different handling

**Fail fast:** Syntax errors are caught before wasting a DB call.

### Why Analyze Before Retry?

The `analyze_error` node enriches the error context:

**Raw error:** `"no such table: employees"`

**Analyzed error:**
```
Error: no such table: employees

Error Type: TABLE_NOT_FOUND
Suggestion: Verify the table name exists in the database schema.
Problem Area: Table: employees
```

This gives the LLM more actionable information for the retry.

## Performance Considerations

### Current Approach
- Synchronous execution
- One LLM call per attempt
- Schema fetched once per session

### Optimization Opportunities
- Cache schema lookups
- Stream LLM responses
- Parallel validation + execution
- Use faster models for simple queries

## Extension Points

### Adding New Node Types

```python
# 1. Define the node function
def new_node(state: SQLAgentState) -> Dict[str, Any]:
    # ... do work ...
    return {"new_field": result}

# 2. Add to graph
workflow.add_node("new_node", new_node)

# 3. Connect with edges
workflow.add_edge("existing_node", "new_node")
```

### Adding New Conditions

```python
# 1. Define the condition
def my_condition(state) -> Literal["option_a", "option_b"]:
    if state["some_field"]:
        return "option_a"
    return "option_b"

# 2. Use in graph
workflow.add_conditional_edges(
    "source_node",
    my_condition,
    {"option_a": "node_a", "option_b": "node_b"}
)
```

### Adding New State Fields

```python
# 1. Update state definition
class SQLAgentState(TypedDict):
    # ... existing fields ...
    new_field: str  # Add new field

# 2. Initialize in parse_intent or app.py
# 3. Use in nodes as needed
```

## Testing Strategy

### Unit Tests
- Each node function independently
- Condition functions with mock state
- Tool classes with sample data

### Integration Tests
- Full graph execution with known queries
- Error recovery scenarios
- Max attempts behavior

### E2E Tests
- Streamlit UI interactions
- Various query types
- Database edge cases

## Conclusion

This architecture demonstrates:

1. **State Machines for AI** - Complex workflows as graphs
2. **Self-Correction** - Learning from failures within a conversation
3. **Graceful Degradation** - Helpful responses when all attempts fail
4. **Safety First** - Multiple validation layers before execution
5. **Separation of Concerns** - Nodes do one thing well

The patterns here apply beyond SQL:
- Code generation with test validation
- Content creation with quality checks
- Data extraction with format validation
- Any task that benefits from "try, learn, retry"