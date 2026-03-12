"""
AI SQL Chatbot Backend
---------------------
FastAPI + LangChain + OpenAI + Gemini
5 SQLite databases: ecommerce | hr | inventory | crm | finance
Retry loop: 1 revalidation attempt on SQL error
"""

import os
import sqlite3
import traceback
import json
import io
import re
from typing import Optional, Any, Dict, List
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from openai import OpenAI

load_dotenv()

app = FastAPI(title="SQL Chatbot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database schemas (passed to LLM as context)
DB_SCHEMAS = {
    "ecommerce": {
        "path": "databases/ecommerce.db",
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
        ]
    },
    "hr": {
        "path": "databases/hr.db",
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
        ]
    },
    "inventory": {
        "path": "databases/inventory.db",
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
        ]
    },
    "crm": {
        "path": "databases/crm.db",
        "description": "Customer account management with managers and interactions",
        "tables": {
            "account_managers": ["id", "name", "email", "region", "hire_date"],
            "customer_accounts": ["id", "customer_id", "account_manager_id", "tier", "status", "since_date"],
            "interactions": ["id", "customer_id", "channel", "interaction_date", "outcome", "notes"],
        },
        "sample_questions": [
            "List account managers in EMEA",
            "Show active customer accounts by tier",
            "Which customers had escalated interactions?",
            "Find the account manager for customer 42",
        ]
    },
    "finance": {
        "path": "databases/finance.db",
        "description": "Billing system with invoices, payments, and refunds",
        "tables": {
            "invoices": ["id", "customer_id", "amount", "status", "issue_date", "due_date"],
            "payments": ["id", "invoice_id", "customer_id", "amount", "method", "payment_date"],
            "refunds": ["id", "payment_id", "amount", "reason", "refund_date"],
        },
        "sample_questions": [
            "Show overdue invoices",
            "Total payments by method",
            "List refunds by reason",
            "Top customers by total invoice amount",
        ]
    }
}

# Helper: build schema context string
def build_schema_context() -> str:
    lines = []
    for db_name, info in DB_SCHEMAS.items():
        lines.append(f"\n### DATABASE: {db_name.upper()}")
        lines.append(f"Description: {info['description']}")
        lines.append("Tables and columns:")
        for table, cols in info["tables"].items():
            lines.append(f"  - {table}: {', '.join(cols)}")
    return "\n".join(lines)

SCHEMA_CONTEXT = build_schema_context()

# Helper: execute SQL safely
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def execute_sql(db_name: str, sql: str) -> dict:
    if db_name not in DB_SCHEMAS:
        return {"error": f"Unknown database: {db_name}"}

    db_path = os.path.join(BASE_DIR, DB_SCHEMAS[db_name]["path"])
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(row) for row in cur.fetchall()]
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}

# LLM Setup

def get_coder_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    model = os.getenv("CODER_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0, openai_api_key=api_key)


def get_orchestrator_llm():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY (or GEMINI_API_KEY) not set in environment")
    model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    return ChatGoogleGenerativeAI(model=model, temperature=1, google_api_key=api_key)


def get_plotly_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    model = os.getenv("PLOTLY_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0, openai_api_key=api_key)


def is_plotly_enabled() -> bool:
    flag = os.getenv("PLOTLY_AGENT", "off").strip().lower()
    return flag in {"1", "true", "yes", "on"}

# Step 1: Identify DB + Generate SQL

def generate_sql(user_query: str, error_context: Optional[str] = None, context: Optional[str] = None, db_hint: Optional[str] = None) -> dict:
    llm = get_coder_llm()

    system_prompt = f"""You are an expert SQL assistant. You have access to 5 SQLite databases.

{SCHEMA_CONTEXT}

YOUR TASK:
1. Identify which database the user's question is about (ecommerce, hr, inventory, crm, or finance)
2. Generate a valid SQLite SQL query to answer the question

RESPONSE FORMAT — respond ONLY in this exact format (no extra text):
DATABASE: <db_name>
SQL: <your sql query>

RULES:
- Use only valid SQLite syntax
- Use exact table/column names as listed above
- Do NOT use markdown or code blocks
- Use JOINs when needed to relate tables
- Limit results to 50 rows max unless asked otherwise
"""

    user_content = f"User question: {user_query}"
    if db_hint:
        user_content += f"\n\nTarget database hint: {db_hint}"
    if context:
        user_content += f"\n\nContext from previous steps:\n{context}"
    if error_context:
        user_content += f"\n\nPrevious SQL failed with error: {error_context}\nPlease fix the SQL query."

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()

    # Parse response
    db_name, sql = None, None
    for line in raw.split("\n"):
        if line.upper().startswith("DATABASE:"):
            db_name = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("SQL:"):
            sql = line.split(":", 1)[1].strip()

    # Handle multi-line SQL
    if "SQL:" in raw:
        sql_part = raw[raw.upper().find("SQL:") + 4:].strip()
        sql = sql_part

    return {"db_name": db_name, "sql": sql, "raw_response": raw}


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


def create_plan(user_query: str) -> List[Dict[str, Any]]:
    llm = get_orchestrator_llm()
    system_prompt = f"""You are the Orchestrator for a multi-database SQL assistant.

You have access to these SQLite databases:
ecommerce, hr, inventory, crm, finance.

{SCHEMA_CONTEXT}

TASK:
Create the smallest step-by-step plan to answer the user's question.

Return JSON only with the exact shape:
{{
  "plan": [
    {{
      "id": "step_1",
      "action": "query|synthesize|plot_dashboard",
      "instruction": "natural language instruction",
      "depends_on": ["step_0"]
    }}
  ]
}}

Rules:
- Always end with a synthesize step.
- Use query steps when data must be fetched.
- Use plot_dashboard only if the user requests a dashboard/chart or if a visualization clearly helps.
- Do NOT write SQL.
- Do NOT include extra text or markdown.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User question: {user_query}")
    ]
    response = llm.invoke(messages)
    raw = response.content.strip()
    data = _extract_json(raw)

    plan = []
    if data and isinstance(data.get("plan"), list):
        for i, step in enumerate(data["plan"], 1):
            if not isinstance(step, dict):
                continue
            step_id = step.get("id") or f"step_{i}"
            action = (step.get("action") or "query").strip().lower()
            instruction = step.get("instruction") or step.get("task") or user_query
            depends_on = step.get("depends_on") or []
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            if not isinstance(depends_on, list):
                depends_on = []
            plan.append({
                "id": step_id,
                "action": action,
                "instruction": instruction,
                "depends_on": depends_on,
                "db_hint": step.get("db") or step.get("database")
            })

    if not plan:
        plan = [
            {"id": "step_1", "action": "query", "instruction": user_query, "depends_on": [], "db_hint": None},
            {"id": "step_2", "action": "synthesize", "instruction": "Provide the final answer.", "depends_on": ["step_1"], "db_hint": None}
        ]

    if not any(s["action"] == "synthesize" for s in plan):
        last_id = plan[-1]["id"]
        plan.append({
            "id": f"step_{len(plan) + 1}",
            "action": "synthesize",
            "instruction": "Provide the final answer.",
            "depends_on": [last_id],
            "db_hint": None
        })

    wants_plot = any(k in user_query.lower() for k in ["plot", "chart", "dashboard", "graph", "visualize"])
    has_plot = any(s["action"] == "plot_dashboard" for s in plan)
    if wants_plot and not has_plot:
        insert_at = max(0, len(plan) - 1)
        depends = [s["id"] for s in plan if s["action"] == "query"]
        plan.insert(insert_at, {
            "id": "step_plot",
            "action": "plot_dashboard",
            "instruction": "Create a plotly dashboard for the results.",
            "depends_on": depends,
            "db_hint": None
        })

    return plan


def _sample_rows(rows: List[dict], max_rows: int = 5) -> List[dict]:
    if not rows:
        return []
    return rows[:max_rows]


def _extract_key_values(columns: List[str], rows: List[dict]) -> Dict[str, List[Any]]:
    key_fields = ["id", "customer_id", "employee_id", "account_manager_id", "invoice_id", "payment_id"]
    values: Dict[str, List[Any]] = {}
    for key in key_fields:
        if key in columns:
            seen = []
            for row in rows:
                val = row.get(key)
                if val is not None and val not in seen:
                    seen.append(val)
                if len(seen) >= 20:
                    break
            if seen:
                values[key] = seen
    return values


def build_context_from_steps(depends_on: List[str], step_store: Dict[str, dict]) -> str:
    chunks = []
    for dep in depends_on:
        info = step_store.get(dep)
        if not info:
            continue
        columns = info.get("columns") or []
        rows = info.get("rows") or []
        sample = _sample_rows(rows, max_rows=5)
        key_values = info.get("key_values") or {}
        chunk = {
            "step_id": dep,
            "database": info.get("database"),
            "row_count": info.get("row_count"),
            "columns": columns,
            "sample_rows": sample,
            "key_values": key_values
        }
        chunks.append(json.dumps(chunk, default=str))
    return "\n".join(chunks)


def run_query_with_revalidation(step_instruction: str, context_text: Optional[str] = None, db_hint: Optional[str] = None) -> dict:
    gen = generate_sql(step_instruction, context=context_text, db_hint=db_hint)
    db_name = gen.get("db_name")
    sql = gen.get("sql")
    if not db_name or not sql:
        return {
            "success": False,
            "database": db_name,
            "sql": sql,
            "attempts": 1,
            "error": "LLM failed to return database or SQL."
        }

    result = execute_sql(db_name, sql)
    if "error" not in result:
        return {
            "success": True,
            "database": db_name,
            "sql": sql,
            "attempts": 1,
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["count"],
            "error": None
        }

    error_msg = result["error"]
    gen2 = generate_sql(step_instruction, error_context=error_msg, context=context_text, db_hint=db_hint)
    db_name2 = gen2.get("db_name") or db_name
    sql2 = gen2.get("sql")
    result2 = execute_sql(db_name2, sql2)

    if "error" not in result2:
        return {
            "success": True,
            "database": db_name2,
            "sql": sql2,
            "attempts": 2,
            "columns": result2["columns"],
            "rows": result2["rows"],
            "row_count": result2["count"],
            "error": None
        }

    return {
        "success": False,
        "database": db_name2,
        "sql": sql2,
        "attempts": 2,
        "error": result2["error"]
    }


def synthesize_answer(user_query: str, step_store: Dict[str, dict]) -> str:
    llm = get_orchestrator_llm()
    summaries = []
    for step_id, info in step_store.items():
        columns = info.get("columns") or []
        rows = info.get("rows") or []
        sample = _sample_rows(rows, max_rows=5)
        summaries.append({
            "step_id": step_id,
            "database": info.get("database"),
            "sql": info.get("sql"),
            "row_count": info.get("row_count"),
            "columns": columns,
            "sample_rows": sample
        })

    system_prompt = """You are the Orchestrator. Provide a concise final answer for the user.
Use the step results below. If any step failed, explain clearly.
Keep the answer short and actionable.
"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User question: {user_query}\n\nStep results:\n{json.dumps(summaries, default=str)}")
    ]
    response = llm.invoke(messages)
    return response.content.strip()


def generate_plotly_figure(user_query: str, step_store: Dict[str, dict]) -> dict:
    llm = get_plotly_llm()
    datasets = []
    for step_id, info in step_store.items():
        if info.get("columns") and info.get("rows"):
            datasets.append({
                "step_id": step_id,
                "database": info.get("database"),
                "columns": info.get("columns"),
                "rows": _sample_rows(info.get("rows"), max_rows=50)
            })

    system_prompt = """You are a Plotly dashboard agent.
Given the datasets and the user request, output ONLY valid JSON with:
{
  "data": [...],
  "layout": {...},
  "config": {...}
}
Use a single figure with sensible defaults. Keep it readable.
Do NOT include markdown or any extra text.
"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {user_query}\n\nDatasets:\n{json.dumps(datasets, default=str)}")
    ]
    response = llm.invoke(messages)
    raw = response.content.strip()
    fig = _extract_json(raw)
    if not fig:
        raise ValueError("Plotly agent did not return valid JSON.")
    return fig

# Pydantic Models

class QueryRequest(BaseModel):
    question: str

class StepResult(BaseModel):
    id: str
    action: str
    instruction: Optional[str] = None
    database: Optional[str] = None
    sql: Optional[str] = None
    columns: Optional[list] = None
    rows: Optional[list] = None
    row_count: Optional[int] = None
    attempts: int = 0
    error: Optional[str] = None

class QueryResponse(BaseModel):
    success: bool
    database: Optional[str]
    sql: Optional[str]
    columns: Optional[list]
    rows: Optional[list]
    row_count: Optional[int]
    error: Optional[str]
    attempts: int
    message: str
    steps: Optional[list] = None
    plotly: Optional[dict] = None
    plotly_message: Optional[str] = None

# Main Endpoint

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    question = req.question.strip()
    if not question:
        return QueryResponse(
            success=False, database=None, sql=None,
            columns=None, rows=None, row_count=None,
            error="Empty question", attempts=0,
            message="Please provide a question."
        )

    try:
        plan = create_plan(question)
        step_store: Dict[str, dict] = {}
        step_results: List[dict] = []
        total_attempts = 0
        final_message: Optional[str] = None
        plotly_spec: Optional[dict] = None
        plotly_message: Optional[str] = None

        for step in plan:
            action = step.get("action")
            step_id = step.get("id")
            instruction = step.get("instruction") or question
            depends_on = step.get("depends_on") or []

            if action == "query":
                context_text = build_context_from_steps(depends_on, step_store)
                result = run_query_with_revalidation(instruction, context_text, step.get("db_hint"))
                total_attempts += result.get("attempts", 0)

                step_result = {
                    "id": step_id,
                    "action": action,
                    "instruction": instruction,
                    "database": result.get("database"),
                    "sql": result.get("sql"),
                    "columns": result.get("columns"),
                    "rows": result.get("rows"),
                    "row_count": result.get("row_count"),
                    "attempts": result.get("attempts", 0),
                    "error": result.get("error")
                }
                step_results.append(step_result)

                if not result.get("success"):
                    return QueryResponse(
                        success=False,
                        database=result.get("database"),
                        sql=result.get("sql"),
                        columns=None,
                        rows=None,
                        row_count=None,
                        error=result.get("error"),
                        attempts=total_attempts,
                        message="❌ Sorry, we are getting some issues processing your query. Please rephrase or try a simpler question.",
                        steps=step_results
                    )

                key_values = _extract_key_values(result.get("columns") or [], result.get("rows") or [])
                step_store[step_id] = {
                    "database": result.get("database"),
                    "sql": result.get("sql"),
                    "columns": result.get("columns"),
                    "rows": result.get("rows"),
                    "row_count": result.get("row_count"),
                    "key_values": key_values
                }

            elif action == "plot_dashboard":
                if not is_plotly_enabled():
                    plotly_message = "Dashboard creation agent is set off."
                else:
                    try:
                        plotly_spec = generate_plotly_figure(question, step_store)
                    except Exception as e:
                        plotly_message = f"Dashboard generation failed: {e}"

            elif action == "synthesize":
                final_message = synthesize_answer(question, step_store)

        if not final_message:
            final_message = "✅ Done."

        primary = step_results[0] if len(step_results) == 1 else None

        return QueryResponse(
            success=True,
            database=primary.get("database") if primary else None,
            sql=primary.get("sql") if primary else None,
            columns=primary.get("columns") if primary else None,
            rows=primary.get("rows") if primary else None,
            row_count=primary.get("row_count") if primary else None,
            error=None,
            attempts=total_attempts,
            message=final_message,
            steps=step_results if step_results else None,
            plotly=plotly_spec,
            plotly_message=plotly_message
        )

    except Exception as e:
        traceback.print_exc()
        return QueryResponse(
            success=False, database=None, sql=None,
            columns=None, rows=None, row_count=None,
            error=str(e), attempts=0,
            message="❌ Internal server error. Please check your API keys and try again."
        )

# Schema Info Endpoint

@app.get("/schema")
def get_schema():
    return {
        db: {
            "description": info["description"],
            "tables": {t: cols for t, cols in info["tables"].items()},
            "sample_questions": info["sample_questions"],
        }
        for db, info in DB_SCHEMAS.items()
    }

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid audio file type.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in environment.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    client = OpenAI(api_key=api_key)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = file.filename or "audio.webm"
    result = client.audio.transcriptions.create(
        model="whisper-large-v3",
        file=audio_file
    )
    text = getattr(result, "text", None)
    if text is None:
        text = str(result)
    return {"text": text}

@app.get("/health")
def health():
    return {"status": "ok"}

# Run
if __name__ == "__main__":
    import uvicorn
    from fake_database import (
        create_ecommerce_db,
        create_hr_db,
        create_inventory_db,
        create_crm_db,
        create_finance_db
    )
    create_ecommerce_db()
    create_hr_db()
    create_inventory_db()
    create_crm_db()
    create_finance_db()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
