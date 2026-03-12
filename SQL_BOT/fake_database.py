import sqlite3
import os
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

DB_DIR = os.path.join(os.path.dirname(__file__), "databases")
os.makedirs(DB_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# DATABASE 1 – E-Commerce
# ─────────────────────────────────────────────
def create_ecommerce_db(n_customers=500, n_orders=2000):

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

    countries = ["USA","UK","Germany","India","Canada","Spain","France"]
    products = [
        ("Laptop Pro","Electronics",1299),
        ("Wireless Mouse","Electronics",30),
        ("Running Shoes","Apparel",90),
        ("Coffee Maker","Appliances",50),
        ("Notebook Set","Stationery",13),
        ("Bluetooth Speaker","Electronics",120),
        ("Office Chair","Furniture",220),
    ]

    # insert products
    for i,p in enumerate(products,1):
        c.execute(
            "INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)",
            (i,p[0],p[1],p[2],random.randint(20,500))
        )

    # customers
    customers=[]
    for i in range(1,n_customers+1):
        customers.append(
            (
                i,
                fake.name(),
                fake.email(),
                random.choice(countries),
                fake.date_between(start_date="-3y", end_date="today")
            )
        )

    c.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?)",customers)

    # orders
    orders=[]
    for i in range(1,n_orders+1):

        customer=random.randint(1,n_customers)
        product=random.randint(1,len(products))
        quantity=random.randint(1,5)

        price=products[product-1][2]
        total=price*quantity

        orders.append(
            (
                i,
                customer,
                product,
                quantity,
                total,
                fake.date_between(start_date="-2y", end_date="today"),
                random.choice(["delivered","shipped","pending","cancelled"])
            )
        )

    c.executemany("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?)",orders)

    conn.commit()
    conn.close()

    print("✅ ecommerce.db created with large dataset")


# ─────────────────────────────────────────────
# DATABASE 2 – HR
# ─────────────────────────────────────────────
def create_hr_db(n_employees=300):

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

    departments=[
        ("Engineering","New York"),
        ("Marketing","London"),
        ("Sales","Chicago"),
        ("HR","New York"),
        ("Finance","San Francisco")
    ]

    for i,d in enumerate(departments,1):
        c.execute(
            "INSERT OR IGNORE INTO departments VALUES (?,?,?,?)",
            (i,d[0],d[1],random.randint(400000,2000000))
        )

    positions=["Engineer","Manager","Analyst","Specialist","Director"]

    employees=[]
    for i in range(1,n_employees+1):
        employees.append(
            (
                i,
                fake.name(),
                random.randint(1,5),
                random.choice(positions),
                random.randint(50000,150000),
                fake.date_between(start_date="-8y",end_date="today"),
                random.choice(["active","inactive"])
            )
        )

    c.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?)",employees)

    reviews=[]
    for i in range(1,n_employees+1):
        reviews.append(
            (
                i,
                i,
                2023,
                random.randint(5,10),
                fake.name(),
                fake.sentence()
            )
        )

    c.executemany("INSERT OR IGNORE INTO performance_reviews VALUES (?,?,?,?,?,?)",reviews)

    conn.commit()
    conn.close()

    print("✅ hr.db created with large dataset")


# ─────────────────────────────────────────────
# DATABASE 3 – Inventory
# ─────────────────────────────────────────────
def create_inventory_db(n_items=200):

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
    """)

    warehouses=[
        ("Alpha Storage","Dallas"),
        ("Beta Hub","Seattle"),
        ("Gamma Facility","Miami")
    ]

    for i,w in enumerate(warehouses,1):
        c.execute(
            "INSERT OR IGNORE INTO warehouses VALUES (?,?,?,?)",
            (i,w[0],w[1],random.randint(5000,15000))
        )

    categories=["Hardware","Electrical","Safety","Logistics","Plumbing"]

    items=[]
    for i in range(1,n_items+1):
        items.append(
            (
                i,
                fake.word().capitalize()+" Item",
                f"SKU-{i:04}",
                round(random.uniform(1,50),2),
                random.choice(categories)
            )
        )

    c.executemany("INSERT OR IGNORE INTO items VALUES (?,?,?,?,?)",items)

    stock=[]
    for i in range(1,n_items+1):
        stock.append(
            (
                i,
                i,
                random.randint(1,3),
                random.randint(50,5000),
                fake.date_between(start_date="-1y",end_date="today")
            )
        )

    c.executemany("INSERT OR IGNORE INTO stock VALUES (?,?,?,?,?)",stock)

    conn.commit()
    conn.close()

    print("✅ inventory.db created with large dataset")


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE 4 – CRM (Account Management)
# ─────────────────────────────────────────────────────────────────────────────
def create_crm_db(n_customers=500, n_managers=25):

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

    regions = ["North America", "EMEA", "APAC", "LATAM"]
    tiers = ["gold", "silver", "bronze", "platinum"]
    channels = ["email", "call", "chat", "in-person"]
    outcomes = ["resolved", "follow-up", "escalated", "closed"]

    managers = []
    for i in range(1, n_managers + 1):
        managers.append(
            (
                i,
                fake.name(),
                fake.email(),
                random.choice(regions),
                fake.date_between(start_date="-8y", end_date="today")
            )
        )
    c.executemany("INSERT OR IGNORE INTO account_managers VALUES (?,?,?,?,?)", managers)

    accounts = []
    for i in range(1, n_customers + 1):
        accounts.append(
            (
                i,
                i,
                random.randint(1, n_managers),
                random.choice(tiers),
                random.choice(["active", "inactive"]),
                fake.date_between(start_date="-4y", end_date="today")
            )
        )
    c.executemany("INSERT OR IGNORE INTO customer_accounts VALUES (?,?,?,?,?,?)", accounts)

    interactions = []
    for i in range(1, n_customers * 2 + 1):
        interactions.append(
            (
                i,
                random.randint(1, n_customers),
                random.choice(channels),
                fake.date_between(start_date="-18mo", end_date="today"),
                random.choice(outcomes),
                fake.sentence()
            )
        )
    c.executemany("INSERT OR IGNORE INTO interactions VALUES (?,?,?,?,?,?)", interactions)

    conn.commit()
    conn.close()

    print("✅ crm.db created with large dataset")


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE 5 – Finance/Billing
# ─────────────────────────────────────────────────────────────────────────────
def create_finance_db(n_customers=500, n_invoices=1200):

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

    methods = ["card", "bank_transfer", "paypal", "cash"]
    statuses = ["paid", "pending", "overdue", "void"]

    invoices = []
    for i in range(1, n_invoices + 1):
        issue = fake.date_between(start_date="-2y", end_date="today")
        due = issue + timedelta(days=random.randint(14, 45))
        amount = round(random.uniform(50, 5000), 2)
        status = random.choice(statuses)
        invoices.append((i, random.randint(1, n_customers), amount, status, issue, due))
    c.executemany("INSERT OR IGNORE INTO invoices VALUES (?,?,?,?,?,?)", invoices)

    payments = []
    refunds = []
    payment_id = 1
    refund_id = 1
    for inv in invoices:
        inv_id = inv[0]
        cust_id = inv[1]
        amount = inv[2]
        status = inv[3]
        if status == "paid":
            pay_amount = amount
            pay_date = fake.date_between(start_date=inv[4], end_date="today")
            payments.append(
                (payment_id, inv_id, cust_id, pay_amount, random.choice(methods), pay_date)
            )
            if random.random() < 0.08:
                refunds.append(
                    (refund_id, payment_id, round(pay_amount * random.uniform(0.2, 0.8), 2),
                     random.choice(["duplicate_charge", "service_issue", "fraud"]), 
                     fake.date_between(start_date=pay_date, end_date="today"))
                )
                refund_id += 1
            payment_id += 1

    c.executemany("INSERT OR IGNORE INTO payments VALUES (?,?,?,?,?,?)", payments)
    c.executemany("INSERT OR IGNORE INTO refunds VALUES (?,?,?, ?,?)", refunds)

    conn.commit()
    conn.close()

    print("✅ finance.db created with large dataset")

if __name__ == "__main__":
    create_ecommerce_db()
    create_hr_db()
    create_inventory_db()
    create_crm_db()
    create_finance_db()

    print("\n🎉 Large datasets generated successfully!")
