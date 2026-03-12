import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "databases")
os.makedirs(DB_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# DATABASE 1 – E-Commerce
# ─────────────────────────────────────────────
def create_ecommerce_db():
    conn = sqlite3.connect(f"{DB_DIR}/ecommerce.db")
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        country TEXT,
        joined_date TEXT
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT,
        category TEXT,
        price REAL,
        stock INTEGER
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        total REAL,
        order_date TEXT,
        status TEXT
    );
    """)

    c.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?)", [
        (1, "Alice Johnson", "alice@email.com", "USA", "2022-01-15"),
        (2, "Bob Smith",    "bob@email.com",   "UK",  "2022-03-22"),
        (3, "Carlos Ruiz",  "carlos@email.com","Spain","2023-06-01"),
        (4, "Diana Lee",    "diana@email.com", "USA", "2023-09-10"),
        (5, "Ethan Brown",  "ethan@email.com", "Canada","2024-01-05"),
    ])

    c.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", [
        (1, "Laptop Pro",     "Electronics", 1299.99, 50),
        (2, "Wireless Mouse", "Electronics",   29.99,200),
        (3, "Running Shoes",  "Apparel",       89.99,120),
        (4, "Coffee Maker",   "Appliances",    49.99, 75),
        (5, "Notebook Set",   "Stationery",    12.99,300),
    ])

    c.executemany("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?)", [
        (1, 1, 1, 1, 1299.99, "2024-01-10", "delivered"),
        (2, 2, 2, 2,   59.98, "2024-01-12", "delivered"),
        (3, 3, 3, 1,   89.99, "2024-02-01", "shipped"),
        (4, 1, 4, 1,   49.99, "2024-02-14", "pending"),
        (5, 4, 5, 3,   38.97, "2024-03-05", "delivered"),
        (6, 5, 1, 1, 1299.99, "2024-03-20", "shipped"),
        (7, 2, 3, 2,  179.98, "2024-04-01", "delivered"),
    ])

    conn.commit()
    conn.close()
    print("✅ ecommerce.db created")

# ─────────────────────────────────────────────
# DATABASE 2 – HR / Human Resources
# ─────────────────────────────────────────────
def create_hr_db():
    conn = sqlite3.connect(f"{DB_DIR}/hr.db")
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY,
        name TEXT,
        location TEXT,
        budget REAL
    );
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT,
        department_id INTEGER,
        position TEXT,
        salary REAL,
        hire_date TEXT,
        status TEXT
    );
    CREATE TABLE IF NOT EXISTS performance_reviews (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER,
        year INTEGER,
        score INTEGER,
        reviewer TEXT,
        notes TEXT
    );
    """)

    c.executemany("INSERT OR IGNORE INTO departments VALUES (?,?,?,?)", [
        (1, "Engineering",  "New York",  1500000),
        (2, "Marketing",    "London",     800000),
        (3, "Sales",        "Chicago",   1200000),
        (4, "HR",           "New York",   500000),
        (5, "Finance",      "San Francisco", 900000),
    ])

    c.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?)", [
        (1, "John Doe",      1, "Senior Engineer",  120000, "2020-03-15", "active"),
        (2, "Jane Roe",      1, "Junior Engineer",   75000, "2022-07-01", "active"),
        (3, "Mike Chan",     2, "Marketing Lead",    95000, "2019-11-20", "active"),
        (4, "Sara Ali",      3, "Sales Manager",    110000, "2021-01-10", "active"),
        (5, "Tom Harris",    4, "HR Specialist",     65000, "2023-02-28", "active"),
        (6, "Lily Zhang",    5, "Financial Analyst", 88000, "2020-08-15", "active"),
        (7, "Omar Faruk",    1, "DevOps Engineer",  105000, "2018-05-01", "active"),
        (8, "Nina Patel",    2, "Content Writer",    58000, "2023-09-01", "inactive"),
    ])

    c.executemany("INSERT OR IGNORE INTO performance_reviews VALUES (?,?,?,?,?,?)", [
        (1, 1, 2023, 9, "Lisa Green",  "Excellent performance"),
        (2, 2, 2023, 7, "Lisa Green",  "Good progress"),
        (3, 3, 2023, 8, "John Doe",    "Strong campaign results"),
        (4, 4, 2023, 9, "HR Dept",     "Exceeded sales targets"),
        (5, 7, 2023, 10,"Lisa Green",  "Outstanding infrastructure work"),
    ])

    conn.commit()
    conn.close()
    print("✅ hr.db created")

# ─────────────────────────────────────────────
# DATABASE 3 – Inventory / Warehouse
# ─────────────────────────────────────────────
def create_inventory_db():
    conn = sqlite3.connect(f"{DB_DIR}/inventory.db")
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY,
        name TEXT,
        city TEXT,
        capacity INTEGER
    );
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        name TEXT,
        sku TEXT,
        unit_cost REAL,
        category TEXT
    );
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY,
        item_id INTEGER,
        warehouse_id INTEGER,
        quantity INTEGER,
        last_updated TEXT
    );
    CREATE TABLE IF NOT EXISTS shipments (
        id INTEGER PRIMARY KEY,
        item_id INTEGER,
        warehouse_id INTEGER,
        quantity INTEGER,
        direction TEXT,
        shipment_date TEXT
    );
    """)

    c.executemany("INSERT OR IGNORE INTO warehouses VALUES (?,?,?,?)", [
        (1, "Alpha Storage",   "Dallas",   10000),
        (2, "Beta Hub",        "Seattle",   8000),
        (3, "Gamma Facility",  "Miami",    12000),
    ])

    c.executemany("INSERT OR IGNORE INTO items VALUES (?,?,?,?,?)", [
        (1, "Steel Bolts",    "SKU-001",  0.15, "Hardware"),
        (2, "PVC Pipes",      "SKU-002",  4.50, "Plumbing"),
        (3, "LED Bulbs",      "SKU-003",  2.20, "Electrical"),
        (4, "Wooden Pallets", "SKU-004", 12.00, "Logistics"),
        (5, "Safety Gloves",  "SKU-005",  3.75, "Safety"),
    ])

    c.executemany("INSERT OR IGNORE INTO stock VALUES (?,?,?,?,?)", [
        (1, 1, 1, 5000, "2024-03-01"),
        (2, 2, 1, 1200, "2024-03-01"),
        (3, 3, 2, 3400, "2024-03-05"),
        (4, 4, 3,  800, "2024-02-20"),
        (5, 5, 2, 2200, "2024-03-10"),
        (6, 1, 3, 1500, "2024-03-01"),
        (7, 3, 1,  700, "2024-02-28"),
    ])

    c.executemany("INSERT OR IGNORE INTO shipments VALUES (?,?,?,?,?,?)", [
        (1, 1, 1, 1000, "inbound",  "2024-01-10"),
        (2, 3, 2,  500, "outbound", "2024-02-14"),
        (3, 2, 1,  300, "inbound",  "2024-02-28"),
        (4, 4, 3,  200, "outbound", "2024-03-05"),
        (5, 5, 2,  800, "inbound",  "2024-03-11"),
    ])

    conn.commit()
    conn.close()
    print("✅ inventory.db created")

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE 4 – CRM / Account Management
# ─────────────────────────────────────────────────────────────────────────────
def create_crm_db():
    conn = sqlite3.connect(f"{DB_DIR}/crm.db")
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS account_managers (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        region TEXT,
        hire_date TEXT
    );
    CREATE TABLE IF NOT EXISTS customer_accounts (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        account_manager_id INTEGER,
        tier TEXT,
        status TEXT,
        since_date TEXT
    );
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        channel TEXT,
        interaction_date TEXT,
        outcome TEXT,
        notes TEXT
    );
    """)

    c.executemany("INSERT OR IGNORE INTO account_managers VALUES (?,?,?,?,?)", [
        (1, "Ava Walker", "ava@company.com", "EMEA", "2020-05-12"),
        (2, "Noah Patel", "noah@company.com", "North America", "2019-09-01"),
    ])

    c.executemany("INSERT OR IGNORE INTO customer_accounts VALUES (?,?,?,?,?,?)", [
        (1, 1, 1, "gold", "active", "2021-02-10"),
        (2, 2, 2, "silver", "active", "2022-07-14"),
        (3, 3, 1, "bronze", "inactive", "2023-03-05"),
    ])

    c.executemany("INSERT OR IGNORE INTO interactions VALUES (?,?,?,?,?,?)", [
        (1, 1, "email", "2024-01-15", "resolved", "Renewal discussion"),
        (2, 2, "call", "2024-02-02", "follow-up", "Pricing questions"),
        (3, 3, "chat", "2024-03-12", "escalated", "Service issue"),
    ])

    conn.commit()
    conn.close()
    print("✅ crm.db created")

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE 5 – Finance / Billing
# ─────────────────────────────────────────────────────────────────────────────
def create_finance_db():
    conn = sqlite3.connect(f"{DB_DIR}/finance.db")
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount REAL,
        status TEXT,
        issue_date TEXT,
        due_date TEXT
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        invoice_id INTEGER,
        customer_id INTEGER,
        amount REAL,
        method TEXT,
        payment_date TEXT
    );
    CREATE TABLE IF NOT EXISTS refunds (
        id INTEGER PRIMARY KEY,
        payment_id INTEGER,
        amount REAL,
        reason TEXT,
        refund_date TEXT
    );
    """)

    c.executemany("INSERT OR IGNORE INTO invoices VALUES (?,?,?,?,?,?)", [
        (1, 1, 1200.00, "paid", "2024-01-05", "2024-02-05"),
        (2, 2, 450.00, "overdue", "2024-02-10", "2024-03-10"),
        (3, 3, 800.00, "pending", "2024-03-01", "2024-03-31"),
    ])

    c.executemany("INSERT OR IGNORE INTO payments VALUES (?,?,?,?,?,?)", [
        (1, 1, 1, 1200.00, "card", "2024-01-15"),
    ])

    c.executemany("INSERT OR IGNORE INTO refunds VALUES (?,?,?,?,?)", [
        (1, 1, 200.00, "service_issue", "2024-01-20"),
    ])

    conn.commit()
    conn.close()
    print("✅ finance.db created")

if __name__ == "__main__":
    create_ecommerce_db()
    create_hr_db()
    create_inventory_db()
    create_crm_db()
    create_finance_db()
    print("\n🎉 All 5 databases seeded successfully!")
