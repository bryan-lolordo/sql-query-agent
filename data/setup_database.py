"""Setup script to create sample ecommerce database for SQL Query Agent."""

import sqlite3
import os


def create_ecommerce_database():
    """Create a sample ecommerce database for testing."""
    
    # Create directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect("data/ecommerce.sqlite")
    cursor = conn.cursor()
    
    print("Creating tables...")
    
    # Create customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            city TEXT,
            country TEXT,
            signup_date DATE
        )
    """)
    
    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT,
            price REAL
        )
    """)
    
    # Create orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            product_id INTEGER,
            order_date DATE,
            quantity INTEGER,
            total_amount REAL,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    print("Inserting sample data...")
    
    # Insert sample customers
    customers = [
        (1, "John Smith", "john@email.com", "New York", "USA", "2024-01-15"),
        (2, "Emma Wilson", "emma@email.com", "London", "UK", "2024-02-20"),
        (3, "Carlos Garcia", "carlos@email.com", "Madrid", "Spain", "2024-03-10"),
        (4, "Li Wei", "li@email.com", "Beijing", "China", "2024-04-05"),
        (5, "Sarah Johnson", "sarah@email.com", "Toronto", "Canada", "2024-05-12"),
        (6, "Ahmed Hassan", "ahmed@email.com", "Dubai", "UAE", "2024-06-18"),
        (7, "Maria Silva", "maria@email.com", "São Paulo", "Brazil", "2024-07-22"),
        (8, "Yuki Tanaka", "yuki@email.com", "Tokyo", "Japan", "2024-08-30"),
        (9, "Sophie Martin", "sophie@email.com", "Paris", "France", "2024-09-14"),
        (10, "David Brown", "david@email.com", "Sydney", "Australia", "2024-10-01")
    ]
    cursor.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?)", customers)
    
    # Insert sample products
    products = [
        (1, "Laptop Pro 15", "Electronics", 1299.99),
        (2, "Wireless Mouse", "Electronics", 29.99),
        (3, "Mechanical Keyboard", "Electronics", 89.99),
        (4, "Office Chair Premium", "Furniture", 299.99),
        (5, "Standing Desk", "Furniture", 499.99),
        (6, "LED Desk Lamp", "Furniture", 49.99),
        (7, "USB-C Cable", "Electronics", 12.99),
        (8, "Monitor 27 inch", "Electronics", 349.99),
        (9, "Webcam HD", "Electronics", 79.99),
        (10, "Noise Cancelling Headphones", "Electronics", 249.99)
    ]
    cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?)", products)
    
    # Insert sample orders (more realistic data)
    orders = [
        # October orders
        (1, 1, 1, "2024-10-01", 1, 1299.99, "completed"),
        (2, 1, 2, "2024-10-01", 2, 59.98, "completed"),
        (3, 2, 5, "2024-10-05", 1, 499.99, "completed"),
        (4, 3, 8, "2024-10-08", 1, 349.99, "completed"),
        (5, 4, 4, "2024-10-12", 1, 299.99, "completed"),
        (6, 5, 10, "2024-10-15", 1, 249.99, "completed"),
        (7, 2, 3, "2024-10-18", 1, 89.99, "completed"),
        (8, 6, 1, "2024-10-20", 1, 1299.99, "shipped"),
        (9, 7, 6, "2024-10-22", 2, 99.98, "completed"),
        (10, 8, 9, "2024-10-25", 1, 79.99, "completed"),
        
        # November orders
        (11, 9, 1, "2024-11-01", 1, 1299.99, "completed"),
        (12, 10, 7, "2024-11-02", 5, 64.95, "completed"),
        (13, 1, 8, "2024-11-05", 1, 349.99, "completed"),
        (14, 3, 2, "2024-11-06", 3, 89.97, "shipped"),
        (15, 4, 5, "2024-11-08", 1, 499.99, "pending"),
        (16, 5, 4, "2024-11-10", 2, 599.98, "completed"),
        (17, 2, 10, "2024-11-11", 1, 249.99, "completed"),
        (18, 6, 3, "2024-11-12", 1, 89.99, "processing")
    ]
    cursor.executemany("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?)", orders)
    
    conn.commit()
    
    # Print summary
    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    order_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_amount) FROM orders")
    total_revenue = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ Database created successfully!")
    print("="*60)
    print(f"📍 Location: data/ecommerce.sqlite")
    print(f"👥 Customers: {customer_count}")
    print(f"📦 Products: {product_count}")
    print(f"🛒 Orders: {order_count}")
    print(f"💰 Total Revenue: ${total_revenue:,.2f}")
    print("="*60)


if __name__ == "__main__":
    create_ecommerce_database()