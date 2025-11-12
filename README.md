# SQL Query Agent with LangGraph

A self-correcting SQL query agent that converts natural language to SQL, executes queries, and automatically fixes errors through iterative refinement loops.

## Features

- 🔄 Self-correcting SQL generation
- 🔁 Iterative refinement with error learning
- 🎯 Quality-based retry logic
- 🛡️ Safe, read-only query execution
- 🎨 Interactive Streamlit UI

## Installation

```bash
pip install -r requirements.txt
```

## Setup

1. Create a `.env` file:
```
OPENAI_API_KEY=your_api_key_here
```

2. Run the application:
```bash
streamlit run app.py
```

## Usage

Enter natural language queries like:
- "Show me top 5 customers by revenue"
- "What are the sales totals by month?"
- "Find products with price greater than $100"

The agent will:
1. Generate SQL from your query
2. Validate syntax
3. Execute safely
4. Auto-correct errors (up to 3 attempts)
5. Display results

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.