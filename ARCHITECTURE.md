# Architecture Documentation

## State Machine Flow

```
START → Parse Intent → Generate SQL → Validate SQL
                                          ↓
                                    Valid? ┬─ No → Fix Syntax (loop back)
                                           └─ Yes ↓
                                    Execute SQL
                                          ↓
                           Success? ┬─ Yes → Format Results → END
                                    └─ No ↓
                                    Analyze Error
                                          ↓
                              Attempts < 3? ┬─ Yes → Generate SQL (loop with learned context)
                                           └─ No → Ask Clarification → END
```

## State Definition

The agent maintains state across iterations:

- `user_query`: Original natural language query
- `sql_query`: Generated SQL statement
- `execution_result`: Query results (if successful)
- `execution_error`: Error message (if failed)
- `attempt`: Current attempt number
- `max_attempts`: Maximum retries (default: 3)
- `previous_errors`: List of past errors for learning
- `previous_queries`: List of past SQL attempts
- `formatted_result`: Human-readable output
- `success`: Whether query succeeded
- `schema`: Database schema context

## Components

### Nodes (graph/nodes.py)
- `parse_intent()`: Understand user query
- `generate_sql()`: Create SQL with error context
- `validate_sql()`: Check syntax
- `execute_sql()`: Run query safely
- `analyze_error()`: Understand failures
- `format_results()`: Present data
- `ask_clarification()`: Request user help

### Conditions (graph/conditions.py)
- `should_retry()`: Decide next action
- `is_valid_sql()`: Route based on validation

### Tools
- **SQLValidator**: Syntax checking
- **SQLExecutor**: Safe query execution
- **SchemaAnalyzer**: Provide DB context

## Self-Correction Loop

1. Generate SQL from natural language
2. If syntax error → fix and regenerate
3. If execution error → analyze, learn, regenerate
4. Each attempt includes context from previous failures
5. Maximum 3 attempts before requesting clarification