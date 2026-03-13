"""
prompt_utils.py
─────────────────────────────────────────────────────────────────────────────
ChatML prompt formatting for Qwen3 models served by vLLM.

Qwen3 chat template:
    <|im_start|>system\n{system}<|im_end|>\n
    <|im_start|>user\n{user}<|im_end|>\n
    <|im_start|>assistant\n

Thinking control:
    - Append  /no_think  to the LAST user message to skip chain-of-thought
      (best for latency-critical tasks: SQL generation, plan parsing)
    - Omit or append  /think  to enable extended reasoning
      (better for complex multi-step synthesis)
"""

from __future__ import annotations
from typing import Optional
from db_schemas import SCHEMA_CONTEXT

# ── ChatML builder ─────────────────────────────────────────────────────────

def build_chatml(
    system: str,
    user: str,
    *,
    enable_thinking: bool = False,
) -> str:
    """
    Assemble a ChatML-formatted prompt ready for vLLM tokenisation.

    Args:
        system:           System message content.
        user:             User message content.
        enable_thinking:  If False (default), appends /no_think to suppress
                          chain-of-thought, giving ~30 % lower TTFT.
    """
    think_token = "" if enable_thinking else " /no_think"
    return (
        f"<|im_start|>system\n{system.strip()}<|im_end|>\n"
        f"<|im_start|>user\n{user.strip()}{think_token}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

# ── Orchestrator prompt: plan creation ────────────────────────────────────

ORCHESTRATOR_SYSTEM_PLAN = f"""You are the Orchestrator for a multi-database NL-to-SQL assistant.

You have access to five SQLite databases: ecommerce, hr, inventory, crm, finance.

{SCHEMA_CONTEXT}

TASK: Create the minimal step-by-step execution plan to answer the user's question.

Return ONLY valid JSON in exactly this shape (no markdown, no extra text):
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
- Always end the plan with exactly one synthesize step
- Use query steps only when data must be fetched from a database
- Use plot_dashboard only if the user explicitly requests a chart/dashboard/graph
- Set db_hint to the most likely database name when obvious, else null
- Do NOT write any SQL yourself
- Keep the plan as short as possible — prefer 1-2 query steps for simple questions
"""


def build_plan_prompt(user_query: str) -> str:
    return build_chatml(
        system=ORCHESTRATOR_SYSTEM_PLAN,
        user=f"User question: {user_query}",
        enable_thinking=True,   # allow brief reasoning for plan quality
    )

# ── Coder prompt: SQL generation ──────────────────────────────────────────

CODER_SYSTEM_SQL = f"""You are an expert SQLite SQL generator with access to 5 databases.

{SCHEMA_CONTEXT}

TASK:
1. Identify which database the question targets (ecommerce | hr | inventory | crm | finance)
2. Write a valid SQLite SQL query that fully answers the question

RESPONSE FORMAT — output ONLY these two lines, nothing else:
DATABASE: <db_name>
SQL: <single-line sql query>

Rules:
- Use exact table and column names as listed in the schema above
- Use valid SQLite syntax only (no CTEs with RECURSIVE unless needed, no ILIKE)
- Use JOINs when data spans multiple tables
- Limit results to 50 rows unless the question requests otherwise
- Do NOT use markdown, code blocks, or any extra explanation
"""


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
        parts.append(
            f"Previous SQL FAILED with error: {error_context}\n"
            "Fix the query — change table/column names or logic as needed."
        )
    return build_chatml(
        system=CODER_SYSTEM_SQL,
        user="\n\n".join(parts),
        enable_thinking=False,  # /no_think → deterministic, fast SQL
    )

# ── Orchestrator prompt: answer synthesis ─────────────────────────────────

ORCHESTRATOR_SYSTEM_SYNTH = """You are the Orchestrator. Synthesise a concise, user-facing answer.

Use only the step results provided. If a step failed, explain clearly.
Keep the answer short, accurate, and actionable (2–5 sentences max).
"""


def build_synthesis_prompt(user_query: str, step_summaries_json: str) -> str:
    return build_chatml(
        system=ORCHESTRATOR_SYSTEM_SYNTH,
        user=(
            f"User question: {user_query}\n\n"
            f"Step results:\n{step_summaries_json}"
        ),
        enable_thinking=False,
    )

# ── Plotly prompt ──────────────────────────────────────────────────────────

PLOTLY_SYSTEM = """You are a Plotly dashboard generator.
Given the datasets and the user request, output ONLY valid JSON:
{
  "data": [...],
  "layout": {...},
  "config": {...}
}
Use a single readable figure. No markdown, no extra text.
"""


def build_plotly_prompt(user_query: str, datasets_json: str) -> str:
    return build_chatml(
        system=PLOTLY_SYSTEM,
        user=f"User request: {user_query}\n\nDatasets:\n{datasets_json}",
        enable_thinking=False,
    )
