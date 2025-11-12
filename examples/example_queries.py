"""Example queries for testing the SQL Query Agent."""

# Example queries that should work with the sample database
EXAMPLE_QUERIES = [
    # Basic queries
    "Show me all customers",
    "List all products",
    "What are the different order statuses?",
    
    # Aggregation queries
    "Show me the top 5 customers by total revenue",
    "What is the total revenue for each product?",
    "How many orders do we have per status?",
    
    # Date-based queries
    "Show me orders from the last 30 days",
    "What was our revenue in Q4 2024?",
    "List orders placed in December 2024",
    
    # Join queries
    "Show me customer names with their order totals",
    "List products with the number of times they've been ordered",
    "Show me customer details along with their most recent order",
    
    # Complex queries
    "Which customers have spent more than $500 total?",
    "Show me the average order value by month",
    "List customers who haven't placed an order in the last 60 days",
    
    # Queries that should trigger errors (for testing self-correction)
    "Show me top customers by revenue in quarter 4",  # May need date function correction
    "Get all orders with their customer phone numbers",  # May need join correction
    "Show me sales by region",  # May need table/column name correction
]

# Queries with expected challenges (to test self-correction)
CHALLENGING_QUERIES = {
    "date_functions": [
        "Show orders from last week",  # SQLite date functions
        "What's our month-over-month revenue growth?",
        "List orders by day of week",
    ],
    
    "aggregations": [
        "Show me the average, min, and max order values",
        "Calculate the running total of revenue",
        "Show cumulative customer count over time",
    ],
    
    "subqueries": [
        "Find customers whose average order value is above the overall average",
        "Show products that have never been ordered",
        "List the top product for each customer",
    ],
    
    "string_operations": [
        "Find customers whose name starts with 'A'",
        "Show orders with 'premium' in the product name",
        "List customers with email addresses from gmail",
    ]
}

def get_example_query(category: str = "basic") -> str:
    """
    Get a random example query from a specific category.
    
    Args:
        category: Category of query ('basic', 'date_functions', 'aggregations', etc.)
        
    Returns:
        An example query string
    """
    import random
    
    if category == "basic":
        return random.choice(EXAMPLE_QUERIES[:15])
    elif category in CHALLENGING_QUERIES:
        return random.choice(CHALLENGING_QUERIES[category])
    else:
        return random.choice(EXAMPLE_QUERIES)

def print_all_examples():
    """Print all example queries organized by category."""
    print("=" * 80)
    print("BASIC EXAMPLE QUERIES")
    print("=" * 80)
    for i, query in enumerate(EXAMPLE_QUERIES, 1):
        print(f"{i}. {query}")
    
    print("\n" + "=" * 80)
    print("CHALLENGING QUERIES")
    print("=" * 80)
    for category, queries in CHALLENGING_QUERIES.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for query in queries:
            print(f"  • {query}")

if __name__ == "__main__":
    print_all_examples()