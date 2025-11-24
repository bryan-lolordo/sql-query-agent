# SQL Query Agent with LangGraph

A self-correcting SQL query agent powered by LangGraph that converts natural language to SQL, executes queries, and automatically fixes errors through iterative refinement loops.

## ✨ Key Features

- 🔄 **Self-Correcting SQL Generation** - Automatically fixes errors and retries
- 🧠 **Learns from Mistakes** - Each retry includes context from previous failures
- 🛡️ **Safe Execution** - Read-only queries with SQL injection prevention
- 📊 **Interactive UI** - Streamlit interface with real-time feedback
- 🎯 **Quality-Based Routing** - Smart decision-making on when to retry vs. clarify

## 🤖 Why LangGraph?

This project demonstrates **production-ready agentic AI patterns** using LangGraph:

| Pattern | Implementation |
|---------|----------------|
| ✅ **Cyclical Workflows** | Retry loops with learned context |
| ✅ **State Management** | Track attempts, errors, and query history |
| ✅ **Conditional Routing** | Smart decisions based on success/failure |
| ✅ **Iterative Refinement** | Each attempt improves on previous failures |
| ✅ **Graceful Degradation** | Ask for clarification after max attempts |

### LangGraph vs LangChain

**LangChain** (Linear): `Input → Process → Output`

**LangGraph** (Cyclical): `Input → Try → Fail → Learn → Retry → Success!`

This agent needs **cycles** - the ability to loop back and try again with new information. That's what makes LangGraph the right choice.

## 🎬 Demo

```
User: "Show me revenue by month for 2024"

🔵 Attempt 1:
   Generated: SELECT strftime('%Y-%m', order_date) as Month, SUM(total_amount)...
   ✅ Success!

📊 Results:
   | Month   | Revenue   |
   |---------|-----------|
   | 2024-10 | $4,329.88 |
   | 2024-11 | $3,244.85 |
```

### Self-Correction in Action

```
User: "Calculate revenue growth rate compared to last quarter"

🔵 Attempt 1:
   Generated: "This requires multiple steps..." (explanatory text)
   ❌ Validation failed: Only SELECT queries allowed

🔵 Attempt 2:
   Generated: SELECT ... ; SELECT ... (multiple statements)
   ❌ Execution failed: Can only execute one statement

🔵 Attempt 3:
   Reached max attempts
   → Asking for clarification with suggestions
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph State Machine                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  START → Parse Intent → Generate SQL → Validate SQL         │
│                                            ↓                │
│                                      Valid? ─┬─ No → Loop   │
│                                              ↓              │
│                                      Execute SQL            │
│                                            ↓                │
│                         Success? ─┬─ Yes → Format → END     │
│                                   ↓                         │
│                            Analyze Error                    │
│                                   ↓                         │
│                    Attempts < 3? ─┬─ Yes → Generate SQL     │
│                                   ↓                         │
│                          Ask Clarification → END            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Overview

```
sql-query-agent/
├── sql_query_agent/
│   ├── graph/                    # LangGraph workflow
│   │   ├── state.py              # State definition (TypedDict)
│   │   ├── nodes.py              # Node functions (7 nodes)
│   │   ├── workflow.py           # Graph builder & compiler
│   │   └── conditions.py         # Routing logic
│   │
│   ├── tools/                    # SQL utilities
│   │   ├── sql_validator.py      # Syntax & safety validation
│   │   ├── sql_executor.py       # Safe query execution
│   │   └── schema_analyzer.py    # Database schema extraction
│   │
│   └── utils/                    # Helpers
│       ├── error_analyzer.py     # Error classification & suggestions
│       └── result_formatter.py   # Output formatting
│
├── data/
│   └── ecommerce.sqlite          # Sample database
│
├── app.py                        # Streamlit UI
├── setup_database.py             # Database generator
└── requirements.txt
```

## 🔧 Installation

### Prerequisites
- Python 3.8+
- OpenAI API key

### Setup

```bash
# Clone the repository
git clone https://github.com/bryan-lolordo/sql-query-agent.git
cd sql-query-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OpenAI API key

# Create sample database
python setup_database.py

# Run the application
streamlit run app.py
```

Navigate to `http://localhost:8501`

## 💬 Usage Examples

### Basic Queries
```
"Show me all customers"
"List all products"
"How many orders do we have?"
```

### Aggregation Queries
```
"Show me top 5 customers by revenue"
"What's the average order value?"
"Total revenue by country"
```

### Complex Queries
```
"Show me customers who ordered in October but not November"
"Which products have never been ordered?"
"Revenue growth month over month"
```

### Queries That Trigger Self-Correction
```
"Show me all employees"           # Table doesn't exist
"Customer phone numbers"          # Column doesn't exist
"Revenue for yesterday"           # Complex date logic
```

## 🧠 How Self-Correction Works

### The Learning Loop

```python
for attempt in range(max_attempts):
    # 1. Generate SQL with context from previous failures
    sql = generate_sql(
        user_query,
        schema,
        previous_errors  # "Learn from these mistakes"
    )
    
    # 2. Validate syntax
    if not valid(sql):
        previous_errors.append(validation_error)
        continue
    
    # 3. Execute query
    try:
        results = execute(sql)
        return format_results(results)
    except Exception as e:
        previous_errors.append(e)
        continue

# 4. If all attempts fail, ask for clarification
return ask_clarification(previous_errors)
```

### Error Context Injection

Each retry includes full context from previous failures:

```
Previous attempts failed with these errors:

Attempt 1:
SQL: SELECT * FROM employees
Error: no such table: employees

Attempt 2:
SQL: SELECT * FROM staff  
Error: no such table: staff

Please fix these issues in your new query.
```

This allows the LLM to learn and adapt within a single conversation.

## 🔐 Safety Features

| Feature | Implementation |
|---------|----------------|
| **Read-Only** | Only SELECT queries allowed |
| **SQL Injection Prevention** | Keyword blocking (DROP, DELETE, UPDATE, etc.) |
| **Safe Execution** | Database opened in read-only mode |
| **Syntax Validation** | Queries parsed before execution |
| **Error Handling** | Graceful failures with helpful messages |

## 📊 State Management

The agent maintains rich state across iterations:

```python
class SQLAgentState(TypedDict):
    user_query: str           # Original question
    sql_query: str            # Current SQL attempt
    execution_result: dict    # Query results
    execution_error: str      # Error message
    attempt: int              # Current attempt (1-3)
    max_attempts: int         # Retry limit
    previous_errors: list     # Error history for learning
    previous_queries: list    # SQL history
    success: bool             # Execution status
    schema: dict              # Database structure
```

## 🛠️ Tech Stack

### AI & Orchestration
- [LangGraph](https://github.com/langchain-ai/langgraph) - State machine orchestration
- [LangChain](https://github.com/langchain-ai/langchain) - LLM integration
- [OpenAI GPT-4](https://openai.com/) - SQL generation

### Infrastructure
- [Streamlit](https://streamlit.io/) - Web UI
- [SQLite](https://sqlite.org/) - Database
- [SQLParse](https://github.com/andialbrecht/sqlparse) - SQL validation
- [Pandas](https://pandas.pydata.org/) - Data formatting

## 📈 Sample Database

The included `ecommerce.sqlite` contains:

| Table | Rows | Description |
|-------|------|-------------|
| `customers` | 10 | Customer info (name, email, city, country) |
| `products` | 10 | Product catalog (name, category, price) |
| `orders` | 18 | Order history (date, quantity, total, status) |

Perfect for testing various query types!

## 🗺️ Roadmap

### Planned Features
- [ ] Query history & favorites
- [ ] Export results (CSV, Excel, PDF)
- [ ] Multi-database support (PostgreSQL, MySQL)
- [ ] Query explanation mode
- [ ] Performance metrics dashboard
- [ ] Streaming responses

### Future Enhancements
- [ ] Visual query builder
- [ ] Schema learning from conversations
- [ ] Query optimization suggestions
- [ ] Natural language result summaries

## 📚 Related Projects

This is part of my **Agentic AI Portfolio**:

| Project | Framework | Pattern |
|---------|-----------|---------|
| [Career Copilot](https://github.com/bryan-lolordo/career-copilot) | Semantic Kernel | Tool Orchestration |
| **SQL Query Agent** | LangGraph | Self-Correction Loops |
| Code Review Crew (Coming Soon) | AutoGen | Multi-Agent Collaboration |

## 📖 Documentation

For detailed technical architecture, see [ARCHITECTURE.md](ARCHITECTURE.md)

Topics covered:
- State machine design
- Node & edge configuration  
- Conditional routing logic
- Error handling patterns
- Self-correction implementation

## 📄 License

MIT License

## 👨‍💻 Author

**Bryan LoLordo**
- Specialization: Agentic AI Systems, GenAI Engineering
- Focus: Production-ready AI agents with multiple frameworks

---

Built with ❤️ using LangGraph

**Demonstrating self-correcting AI agents through iterative refinement** 🔄