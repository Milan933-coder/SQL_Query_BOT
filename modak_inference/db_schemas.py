"""
db_schemas.py
─────────────────────────────────────────────────────────────────────────────
Database schema registry for 5 SQLite databases + safe SQL executor.
Imported by both modal_app.py and (optionally) local dev scripts.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional

# ── Schema registry ────────────────────────────────────────────────────────

DB_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "ecommerce": {
        "path": "SQL_BOT/databases/ecommerce.db",
        "description": "E-Commerce store with customers, products, and orders",
        "tables": {
            "customers": ["id", "name", "email", "country", "joined_date"],
            "products":  ["id", "name", "category", "price", "stock"],
            "orders":    ["id", "customer_id", "product_id", "quantity", "total", "order_date", "status"],
        },
        "sample_questions": [
            "Show all customers from USA",
            "What are the top 3 selling products?",
            "List all delivered orders",
            "What is the total revenue from all orders?",
        ],
    },
    "hr": {
        "path": "SQL_BOT/databases/hr.db",
        "description": "HR system with employees, departments, and performance reviews",
        "tables": {
            "departments":         ["id", "name", "location", "budget"],
            "employees":           ["id", "name", "department_id", "position", "salary", "hire_date", "status"],
            "performance_reviews": ["id", "employee_id", "year", "score", "reviewer", "notes"],
        },
        "sample_questions": [
            "List all active employees",
            "Which department has the highest budget?",
            "Show employees with salary above 100000",
            "Who got the highest performance score in 2023?",
        ],
    },
    "inventory": {
        "path": "SQL_BOT/databases/inventory.db",
        "description": "Warehouse inventory with items, stock levels, and shipments",
        "tables": {
            "warehouses": ["id", "name", "city", "capacity"],
            "items":      ["id", "name", "sku", "unit_cost", "category"],
            "stock":      ["id", "item_id", "warehouse_id", "quantity", "last_updated"],
            "shipments":  ["id", "item_id", "warehouse_id", "quantity", "direction", "shipment_date"],
        },
        "sample_questions": [
            "What items are stocked in Dallas?",
            "Show all inbound shipments",
            "Which item has the highest quantity in stock?",
            "List warehouses with their cities",
        ],
    },
    "crm": {
        "path": "SQL_BOT/databases/crm.db",
        "description": "Customer account management with managers and interactions",
        "tables": {
            "account_managers":  ["id", "name", "email", "region", "hire_date"],
            "customer_accounts": ["id", "customer_id", "account_manager_id", "tier", "status", "since_date"],
            "interactions":      ["id", "customer_id", "channel", "interaction_date", "outcome", "notes"],
        },
        "sample_questions": [
            "List account managers in EMEA",
            "Show active customer accounts by tier",
            "Which customers had escalated interactions?",
            "Find the account manager for customer 42",
        ],
    },
    "finance": {
        "path": "SQL_BOT/databases/finance.db",
        "description": "Billing system with invoices, payments, and refunds",
        "tables": {
            "invoices": ["id", "customer_id", "amount", "status", "issue_date", "due_date"],
            "payments": ["id", "invoice_id", "customer_id", "amount", "method", "payment_date"],
            "refunds":  ["id", "payment_id", "amount", "reason", "refund_date"],
        },
        "sample_questions": [
            "Show overdue invoices",
            "Total payments by method",
            "List refunds by reason",
            "Top customers by total invoice amount",
        ],
    },
}

# Pre-built schema context injected into every prompt (cached at import time)
def build_schema_context() -> str:
    lines: List[str] = []
    for db_name, info in DB_SCHEMAS.items():
        lines.append(f"\n### DATABASE: {db_name.upper()}")
        lines.append(f"Description: {info['description']}")
        lines.append("Tables and columns:")
        for table, cols in info["tables"].items():
            lines.append(f"  - {table}: {', '.join(cols)}")
    return "\n".join(lines)


SCHEMA_CONTEXT: str = build_schema_context()

# ── Safe SQL execution ─────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def execute_sql(db_name: str, sql: str) -> Dict[str, Any]:
    """
    Execute a read-only SQL query against a local SQLite database.

    Returns either:
        {"columns": [...], "rows": [...], "count": int}
    or:
        {"error": "<message>"}
    """
    if db_name not in DB_SCHEMAS:
        return {"error": f"Unknown database: {db_name!r}. "
                         f"Valid choices: {list(DB_SCHEMAS.keys())}"}

    db_path = os.path.join(BASE_DIR, DB_SCHEMAS[db_name]["path"])
    if not os.path.exists(db_path):
        return {"error": f"Database file not found at {db_path}"}

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(row) for row in cur.fetchall()]
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as exc:
        return {"error": str(exc)}

# ── Small helper utilities ─────────────────────────────────────────────────

def sample_rows(rows: List[dict], max_rows: int = 5) -> List[dict]:
    return rows[:max_rows]


def extract_key_values(columns: List[str], rows: List[dict]) -> Dict[str, List[Any]]:
    """Pull ID-like columns to pass as context for dependent query steps."""
    key_fields = [
        "id", "customer_id", "employee_id",
        "account_manager_id", "invoice_id", "payment_id",
    ]
    values: Dict[str, List[Any]] = {}
    for key in key_fields:
        if key in columns:
            seen: List[Any] = []
            for row in rows:
                val = row.get(key)
                if val is not None and val not in seen:
                    seen.append(val)
                if len(seen) >= 20:
                    break
            if seen:
                values[key] = seen
    return values
