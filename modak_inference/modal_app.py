"""
modal_app.py  —  fully self-contained, no external module imports
─────────────────────────────────────────────────────────────────
NL-to-SQL on Modal + vLLM
  • OrchestratorModel  Qwen3-4B       FP16  A10G   — planning + synthesis
  • CoderModel         Qwen3-30B-A3B  FP8   A100   — SQL generation

Fixes vs previous version
  1. db_schemas + prompt_utils inlined  → no ModuleNotFoundError
  2. allow_concurrent_inputs removed    → @modal.concurrent (Modal 1.0 API)
  3. required=False removed             → works with all Modal SDK versions
"""

from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import traceback
from typing import Any, Dict, List, Optional

CACHE_DIR = "/model-cache/databases"
import modal
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — DB SCHEMAS + SQL EXECUTOR
# ══════════════════════════════════════════════════════════════════════════════

DB_SCHEMAS: Dict[str, Dict[str, Any]] = {
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
        ],
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
        ],
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
        ],
    },
    "crm": {
        "path": "databases/crm.db",
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
        "path": "databases/finance.db",
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


def _build_schema_context() -> str:
    lines: List[str] = []
    for db_name, info in DB_SCHEMAS.items():
        lines.append(f"\n### DATABASE: {db_name.upper()}")
        lines.append(f"Description: {info['description']}")
        lines.append("Tables and columns:")
        for table, cols in info["tables"].items():
            lines.append(f"  - {table}: {', '.join(cols)}")
    return "\n".join(lines)


SCHEMA_CONTEXT: str = _build_schema_context()
BASE_DIR = CACHE_DIR


def execute_sql(db_name: str, sql: str) -> Dict[str, Any]:
    if db_name not in DB_SCHEMAS:
        return {"error": f"Unknown database: {db_name!r}. Valid: {list(DB_SCHEMAS.keys())}"}
    db_path = os.path.join(BASE_DIR, DB_SCHEMAS[db_name]["path"])
    if not os.path.exists(db_path):
        return {"error": f"Database file not found: {db_path}"}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(row) for row in cur.fetchall()]
        columns = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as exc:
        return {"error": str(exc)}


def sample_rows(rows: List[dict], max_rows: int = 5) -> List[dict]:
    return rows[:max_rows]


def extract_key_values(columns: List[str], rows: List[dict]) -> Dict[str, List[Any]]:
    key_fields = ["id", "customer_id", "employee_id",
                  "account_manager_id", "invoice_id", "payment_id"]
    out: Dict[str, List[Any]] = {}
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
                out[key] = seen
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — PROMPT UTILS (Qwen3 ChatML + /no_think)
# ══════════════════════════════════════════════════════════════════════════════

def _chatml(system: str, user: str, *, think: bool = False) -> str:
    suffix = "" if think else " /no_think"
    return (
        f"<|im_start|>system\n{system.strip()}<|im_end|>\n"
        f"<|im_start|>user\n{user.strip()}{suffix}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


_PLAN_SYSTEM = f"""You are the Orchestrator for a multi-database NL-to-SQL assistant.
You have access to five SQLite databases: ecommerce, hr, inventory, crm, finance.

{SCHEMA_CONTEXT}

TASK: Create the minimal step-by-step execution plan to answer the user question.
Return ONLY valid JSON — no markdown, no extra text:
{{
  "plan": [
    {{
      "id": "step_1",
      "action": "query",
      "instruction": "natural language instruction for the SQL agent",
      "db_hint": "database_name_or_null",
      "depends_on": []
    }},
    {{
      "id": "step_2",
      "action": "synthesize",
      "instruction": "Provide the final answer.",
      "db_hint": null,
      "depends_on": ["step_1"]
    }}
  ]
}}

Rules:
- action must be one of: query | synthesize | plot_dashboard
- Always end with exactly one synthesize step
- Set db_hint to the most likely database when obvious, else null
- Do NOT write any SQL — the SQL agent handles that
- Keep the plan as short as possible
"""

_SQL_SYSTEM = f"""You are an expert SQLite SQL generator with access to 5 databases.

{SCHEMA_CONTEXT}

TASK:
1. Identify which database the question targets (ecommerce | hr | inventory | crm | finance)
2. Write a valid SQLite SQL query that fully answers the question

RESPONSE FORMAT — output ONLY these two lines, nothing else:
DATABASE: <db_name>
SQL: <sql query>

Rules:
- Use exact table/column names from the schema above
- Valid SQLite syntax only
- Use JOINs when data spans multiple tables
- Limit to 50 rows unless asked otherwise
- No markdown, no code blocks, no extra text
"""

_SYNTH_SYSTEM = """You are the Orchestrator. Write a concise user-facing answer (2-5 sentences max).
Use only the step results provided. If a step failed, explain clearly.
"""

_PLOTLY_SYSTEM = """You are a Plotly dashboard generator.
Output ONLY valid JSON: {"data": [...], "layout": {...}, "config": {...}}
No markdown, no extra text.
"""


def build_plan_prompt(user_query: str) -> str:
    return _chatml(_PLAN_SYSTEM, f"User question: {user_query}", think=True)


def build_sql_prompt(
    instruction: str,
    *,
    db_hint: Optional[str] = None,
    context: Optional[str] = None,
    error_context: Optional[str] = None,
) -> str:
    parts = [f"Question: {instruction}"]
    if db_hint:
        parts.append(f"Target database hint: {db_hint}")
    if context:
        parts.append(f"Context from previous steps:\n{context}")
    if error_context:
        parts.append(f"Previous SQL FAILED: {error_context}\nFix the query.")
    return _chatml(_SQL_SYSTEM, "\n\n".join(parts), think=False)


def build_synthesis_prompt(user_query: str, summaries_json: str) -> str:
    return _chatml(
        _SYNTH_SYSTEM,
        f"User question: {user_query}\n\nStep results:\n{summaries_json}",
        think=False,
    )


def build_plotly_prompt(user_query: str, datasets_json: str) -> str:
    return _chatml(
        _PLOTLY_SYSTEM,
        f"User request: {user_query}\n\nDatasets:\n{datasets_json}",
        think=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — MODAL APP + GPU MODEL CLASSES
# ══════════════════════════════════════════════════════════════════════════════

app = modal.App("nl-sql-vllm")

model_volume = modal.Volume.from_name("nl-sql-weights", create_if_missing=True)
CACHE_DIR = "/model-cache"

ORCHESTRATOR_MODEL_ID = "Qwen/Qwen3.5-4B"
CODER_MODEL_ID        = "Qwen/Qwen3-30B-A3B"

vllm_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("uv")
    .run_commands(
        # Let vLLM resolve its own torch + CUDA deps
        "uv pip install vllm hf-transfer huggingface-hub accelerate --system",
        # FlashInfer for cu124 (Modal H100s), matching vLLM's torch version
        "uv pip install flashinfer-python --system "
        "--extra-index-url https://flashinfer.ai/whl/cu124/torch2.6",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
        "TOKENIZERS_PARALLELISM": "false",
        "VLLM_CACHE_ROOT": "/model-cache/vllm-cache",
        "TORCHINDUCTOR_CACHE_DIR": "/model-cache/inductor",
    })
)

# ── OrchestratorModel — Qwen3-4B FP16 on A10G ────────────────────────────

@app.cls(
    image=vllm_image,
    gpu="L40S",
    volumes={CACHE_DIR: model_volume},
    timeout=600,
    scaledown_window=300,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.concurrent(max_inputs=32)
class OrchestratorModel:

    @modal.enter()
    async def load(self) -> None:
        from vllm import AsyncLLMEngine, AsyncEngineArgs
        from inspect import signature
        engine_kwargs = dict(
            model=ORCHESTRATOR_MODEL_ID,
            download_dir=CACHE_DIR,
            dtype="float16",
            kv_cache_dtype="auto",
            gpu_memory_utilization=0.92,
            max_model_len=4096,
            block_size=16,
            max_num_batched_tokens=8192,
            max_num_seqs=32,
            enable_chunked_prefill=True,
            enable_prefix_caching=True,
            enforce_eager=False,
            trust_remote_code=True,
        )
        if "disable_log_requests" in signature(AsyncEngineArgs.__init__).parameters:
            engine_kwargs["disable_log_requests"] = True
        self.engine = AsyncLLMEngine.from_engine_args(AsyncEngineArgs(**engine_kwargs))

    @modal.method()
    async def generate(self, prompt: str, max_tokens: int = 512,
                       temperature: float = 0.6, top_p: float = 0.9) -> str:
        from vllm import SamplingParams
        import uuid
        params = SamplingParams(
            max_tokens=max_tokens, temperature=temperature, top_p=top_p,
            stop=["<|im_end|>", "<|endoftext|>"], skip_special_tokens=True,
        )
        output = None
        async for out in self.engine.generate(prompt, params, str(uuid.uuid4())):
            output = out
        return output.outputs[0].text.strip() if output and output.outputs else ""


# ── CoderModel — Qwen3-30B-A3B FP8 on A100-80GB ──────────────────────────

@app.cls(
    image=vllm_image,
    gpu="H100",
    volumes={CACHE_DIR: model_volume},
    timeout=3600,
    scaledown_window=300,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.concurrent(max_inputs=16)
class CoderModel:

    @modal.enter()
    async def load(self) -> None:
        from vllm import AsyncLLMEngine, AsyncEngineArgs
        from inspect import signature
        engine_kwargs = dict(
            model=CODER_MODEL_ID,
            download_dir=CACHE_DIR,
            dtype="bfloat16",
            quantization="fp8",
            kv_cache_dtype="auto",
            gpu_memory_utilization=0.95,
            max_model_len=4096,
            block_size=16,
            max_num_batched_tokens=4096,
            max_num_seqs=16,
            enable_chunked_prefill=True,
            enable_prefix_caching=True,
            enforce_eager=False,
            trust_remote_code=True,
        )
        if "disable_log_requests" in signature(AsyncEngineArgs.__init__).parameters:
            engine_kwargs["disable_log_requests"] = True
        self.engine = AsyncLLMEngine.from_engine_args(AsyncEngineArgs(**engine_kwargs))

    @modal.method()
    async def generate(self, prompt: str, max_tokens: int = 256,
                       temperature: float = 0.0, top_p: float = 1.0) -> str:
        from vllm import SamplingParams
        import uuid
        params = SamplingParams(
            max_tokens=max_tokens, temperature=temperature, top_p=top_p,
            stop=["<|im_end|>", "<|endoftext|>"], skip_special_tokens=True,
        )
        output = None
        async for out in self.engine.generate(prompt, params, str(uuid.uuid4())):
            output = out
        return output.outputs[0].text.strip() if output and output.outputs else ""


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — FASTAPI + ORCHESTRATION LOGIC
# ══════════════════════════════════════════════════════════════════════════════

web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("fastapi", "uvicorn", "pydantic>=2.0", "openai","python-multipart")
)

fastapi_app = FastAPI(title="NL-SQL API (Modal + vLLM)")
fastapi_app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except Exception:
        pass
    m = re.search(r"\{.*\}", clean, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


def _parse_db_sql(raw: str) -> tuple[Optional[str], Optional[str]]:
    db_name = sql = None
    for line in raw.split("\n"):
        up = line.strip().upper()
        if up.startswith("DATABASE:"):
            db_name = line.split(":", 1)[1].strip().lower()
        elif up.startswith("SQL:"):
            sql = line.split(":", 1)[1].strip()
    if "SQL:" in raw.upper():
        sql = raw[raw.upper().find("SQL:") + 4:].strip()
    return db_name, sql


def _build_context(depends_on: List[str], step_store: Dict[str, dict]) -> str:
    chunks = []
    for dep in depends_on:
        info = step_store.get(dep)
        if not info:
            continue
        chunks.append(json.dumps({
            "step_id":     dep,
            "database":    info.get("database"),
            "row_count":   info.get("row_count"),
            "columns":     info.get("columns"),
            "sample_rows": sample_rows(info.get("rows") or [], 5),
            "key_values":  info.get("key_values") or {},
        }, default=str))
    return "\n".join(chunks)


async def _create_plan(question: str) -> List[Dict[str, Any]]:
    raw = await OrchestratorModel().generate.remote.aio(
        build_plan_prompt(question), max_tokens=512, temperature=0.6
    )
    data = _extract_json(raw)
    plan: List[Dict[str, Any]] = []

    if data and isinstance(data.get("plan"), list):
        for i, step in enumerate(data["plan"], 1):
            if not isinstance(step, dict):
                continue
            dep = step.get("depends_on") or []
            if isinstance(dep, str):
                dep = [dep]
            plan.append({
                "id":          step.get("id") or f"step_{i}",
                "action":      (step.get("action") or "query").strip().lower(),
                "instruction": step.get("instruction") or question,
                "db_hint":     step.get("db_hint") or step.get("db"),
                "depends_on":  dep if isinstance(dep, list) else [],
            })

    if not plan:
        plan = [
            {"id": "step_1", "action": "query",      "instruction": question,                "db_hint": None, "depends_on": []},
            {"id": "step_2", "action": "synthesize",  "instruction": "Provide final answer.", "db_hint": None, "depends_on": ["step_1"]},
        ]
    if not any(s["action"] == "synthesize" for s in plan):
        plan.append({"id": f"step_{len(plan)+1}", "action": "synthesize",
                     "instruction": "Provide final answer.", "db_hint": None,
                     "depends_on": [plan[-1]["id"]]})
    if any(k in question.lower() for k in ["plot","chart","dashboard","graph","visualize"]):
        if not any(s["action"] == "plot_dashboard" for s in plan):
            plan.insert(max(0, len(plan)-1), {
                "id": "step_plot", "action": "plot_dashboard",
                "instruction": "Create a Plotly dashboard.", "db_hint": None,
                "depends_on": [s["id"] for s in plan if s["action"] == "query"],
            })
    return plan


async def _run_query(instruction: str, context_text: Optional[str],
                     db_hint: Optional[str]) -> Dict[str, Any]:
    coder = CoderModel()

    async def _attempt(error_ctx: Optional[str] = None):
        raw = await coder.generate.remote.aio(
            build_sql_prompt(instruction, db_hint=db_hint,
                             context=context_text, error_context=error_ctx),
            max_tokens=256, temperature=0.1,
        )
        db, sql = _parse_db_sql(raw)
        if not db or not sql:
            return db, sql, {"error": "Model did not return DATABASE/SQL lines."}
        return db, sql, execute_sql(db, sql)

    db, sql, res = await _attempt()
    if "error" not in res:
        return {"success": True, "database": db, "sql": sql, "columns": res["columns"],
                "rows": res["rows"], "row_count": res["count"], "attempts": 1, "error": None}

    db2, sql2, res2 = await _attempt(error_ctx=res["error"])
    if "error" not in res2:
        return {"success": True, "database": db2, "sql": sql2, "columns": res2["columns"],
                "rows": res2["rows"], "row_count": res2["count"], "attempts": 2, "error": None}

    return {"success": False, "database": db2, "sql": sql2, "attempts": 2, "error": res2["error"]}


async def _synthesize(question: str, step_store: Dict[str, dict]) -> str:
    summaries = [
        {"step_id": sid, "database": info.get("database"), "sql": info.get("sql"),
         "row_count": info.get("row_count"), "columns": info.get("columns"),
         "sample_rows": sample_rows(info.get("rows") or [], 5)}
        for sid, info in step_store.items()
    ]
    return await OrchestratorModel().generate.remote.aio(
        build_synthesis_prompt(question, json.dumps(summaries, default=str)),
        max_tokens=256, temperature=0.3,
    )


async def _generate_plotly(question: str, step_store: Dict[str, dict]) -> dict:
    datasets = [
        {"step_id": sid, "database": info.get("database"),
         "columns": info.get("columns"), "rows": sample_rows(info.get("rows") or [], 50)}
        for sid, info in step_store.items() if info.get("columns") and info.get("rows")
    ]
    raw = await OrchestratorModel().generate.remote.aio(
        build_plotly_prompt(question, json.dumps(datasets, default=str)),
        max_tokens=1024, temperature=0.2,
    )
    fig = _extract_json(raw)
    if not fig:
        raise ValueError("Model did not return valid Plotly JSON.")
    return fig


# ── Pydantic models ───────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    success: bool
    database: Optional[str] = None
    sql: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[dict]] = None
    row_count: Optional[int] = None
    error: Optional[str] = None
    attempts: int = 0
    message: str
    steps: Optional[List[dict]] = None
    plotly: Optional[dict] = None
    plotly_message: Optional[str] = None


# ── API endpoints ─────────────────────────────────────────────────────────

@fastapi_app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest) -> QueryResponse:
    question = req.question.strip()
    if not question:
        return QueryResponse(success=False, error="Empty question",
                             attempts=0, message="Please provide a question.")
    try:
        plan = await _create_plan(question)
        step_store: Dict[str, dict] = {}
        step_results: List[dict] = []
        total_attempts = 0
        final_message = plotly_spec = plotly_message = None

        for step in plan:
            action      = step["action"]
            step_id     = step["id"]
            instruction = step.get("instruction") or question
            depends_on  = step.get("depends_on") or []
            db_hint     = step.get("db_hint")

            if action == "query":
                result = await _run_query(instruction, _build_context(depends_on, step_store), db_hint)
                total_attempts += result.get("attempts", 0)
                step_rec = {
                    "id": step_id, "action": action, "instruction": instruction,
                    "database": result.get("database"), "sql": result.get("sql"),
                    "columns": result.get("columns"), "rows": result.get("rows"),
                    "row_count": result.get("row_count"),
                    "attempts": result.get("attempts", 0), "error": result.get("error"),
                }
                step_results.append(step_rec)
                if not result.get("success"):
                    return QueryResponse(
                        success=False, database=result.get("database"),
                        sql=result.get("sql"), error=result.get("error"),
                        attempts=total_attempts, steps=step_results,
                        message="❌ Could not process your query. Please rephrase and try again.",
                    )
                step_store[step_id] = {
                    "database": result.get("database"), "sql": result.get("sql"),
                    "columns": result.get("columns"), "rows": result.get("rows"),
                    "row_count": result.get("row_count"),
                    "key_values": extract_key_values(result.get("columns") or [], result.get("rows") or []),
                }
            elif action == "plot_dashboard":
                try:
                    plotly_spec = await _generate_plotly(question, step_store)
                except Exception as exc:
                    plotly_message = f"Dashboard generation failed: {exc}"
            elif action == "synthesize":
                final_message = await _synthesize(question, step_store)

        primary = step_results[0] if len(step_results) == 1 else None
        return QueryResponse(
            success=True,
            database=primary["database"] if primary else None,
            sql=primary["sql"] if primary else None,
            columns=primary["columns"] if primary else None,
            rows=primary["rows"] if primary else None,
            row_count=primary["row_count"] if primary else None,
            attempts=total_attempts,
            message=final_message or "✅ Done.",
            steps=step_results if len(step_results) > 1 else None,
            plotly=plotly_spec,
            plotly_message=plotly_message,
        )
    except Exception:
        traceback.print_exc()
        return QueryResponse(success=False, error="Internal server error",
                             attempts=0, message="❌ Internal error. Please try again.")


@fastapi_app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid audio file.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set.")
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    buf = io.BytesIO(audio_bytes)
    buf.name = file.filename or "audio.webm"
    result = client.audio.transcriptions.create(model="whisper-large-v3", file=buf)
    return {"text": getattr(result, "text", str(result))}


@fastapi_app.get("/schema")
def schema_endpoint():
    return {
        db: {
            "description": info["description"],
            "tables": {t: cols for t, cols in info["tables"].items()},
            "sample_questions": info["sample_questions"],
        }
        for db, info in DB_SCHEMAS.items()
    }


@fastapi_app.get("/health")
def health():
    return {"status": "ok", "models": {
        "orchestrator": ORCHESTRATOR_MODEL_ID,
        "coder": CODER_MODEL_ID,
    }}


# ── Modal web endpoint ────────────────────────────────────────────────────

@app.function(
    image=web_image,
    timeout=3600,
    secrets=[modal.Secret.from_name("app-secrets")],
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def web() -> FastAPI:
    return fastapi_app
