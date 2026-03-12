# ⚡ SQL Mind — AI Chatbot (NL → SQL)

Natural Language to SQL chatbot with 5 databases, LangChain, Gemini Orchestrator + OpenAI Coder, and a revalidation loop Voice Section is their But Not Added.

---

## 🏗️ New Architecture (Plan & Execute)

```
User Question
    |
    v
Orchestrator (Gemini) -> Step-by-step Plan
    |
    v
For each step:
  - Coder (GPT-4o-mini) generates SQL
  - Execute on selected SQLite DB
  - Revalidate on error (Checker)
    |
    v
Optional: Plotly Dashboard Agent (if PLOTLY_AGENT=on)
    |
    v
Synthesize final answer + return steps (+ chart if enabled)
```

---

## 🗄️ The 5 Databases

| Database | Tables | Description |
|----------|--------|-------------|
| **ecommerce.db** | customers, products, orders | Online store data |
| **hr.db** | employees, departments, performance_reviews | HR management |
| **inventory.db** | warehouses, items, stock, shipments | Warehouse logistics |
| **crm.db** | account_managers, customer_accounts, interactions | Account management |
| **finance.db** | invoices, payments, refunds | Billing and payments |

---

## 🚀 Setup & Run

### 1. Backend

```bash
cd SQL_BOT

# Install dependencies
pip install -r requirements.txt

# Set your API keys
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "GOOGLE_API_KEY=your-gemini-key" >> .env

# Optional settings
# GEMINI_MODEL=gemini-1.5-pro
# CODER_MODEL=gpt-4o-mini
# PLOTLY_AGENT=off
# PLOTLY_MODEL=gpt-4o-mini

# Seed databases + start server
python main.py
# OR
python seed_databases.py   # seed first
uvicorn main:app --reload  # then run server
```

Backend runs at: **http://localhost:8000**

### 2. Frontend

```bash
# Option A: React (Vite)
cd frontend-vite
npm install
npm run dev

# Option B: Use the standalone App.jsx directly in claude.ai Artifacts
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/query` | Send NL question → get SQL + results |
| `GET` | `/schema` | Get all database schemas |
| `GET` | `/health` | Health check |
| `POST` | `/transcribe` | Voice → text (Whisper) |

### Example Request
```json
POST /query
{
  "question": "Show all employees with salary above 100000"
}
```

### Example Response
```json
{
  "success": true,
  "database": "hr",
  "sql": "SELECT * FROM employees WHERE salary > 100000 LIMIT 50",
  "columns": ["id", "name", "department_id", "position", "salary", "hire_date", "status"],
  "rows": [...],
  "row_count": 3,
  "attempts": 1,
  "message": "✅ Query executed successfully on hr database."
}
```

---

## 🔑 How It Works

### LLM Prompt Strategy

The system passes **all 5 database schemas** to the LLM in every request.
The Orchestrator (Gemini) breaks the query into steps, and the Coder (OpenAI) generates SQL per step.

### Revalidation Loop

1. **Attempt 1**: Generate SQL → Execute
2. **If error**: Pass the error message back to LLM with the original question
3. **Attempt 2**: LLM sees what went wrong → generates fixed SQL → Execute
4. **If still fails**: Return user-friendly error message

Only **1 retry** is made to keep responses fast.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI + Python
- **AI**: LangChain + Gemini (Orchestrator) + OpenAI GPT-4o-mini (Coder)
- **Databases**: SQLite (5x)
- **Frontend**: React + Tailwind-inspired CSS

---

## 💡 Sample Questions to Try

**E-Commerce:**
- "Show all customers from USA"
- "What is the total revenue from all orders?"
- "List products with price above 50"

**HR:**
- "Who is the highest paid employee?"
- "List all active employees in Engineering"
- "Show performance reviews with score above 8"

**Inventory:**
- "What items are stored in Dallas?"
- "Show all inbound shipments in 2024"
- "Which warehouse has the highest capacity?"
**Multi Hop Questions:**
Here are some multi‑hop questions you can try:

- “Find the top 5 customers by total order value in ecommerce, then show their account managers from the CRM database.”
- “List customers with overdue invoices in finance, then check their last interaction outcome in CRM.”
- “Get the top 3 products by revenue in ecommerce, then show current stock for those items in inventory.”
“- Find employees in HR with the highest performance scores, then list their department budgets.”
“Show customers who purchased in the last 90 days (ecommerce), then list any refunds they received (finance).”
“Find the 5 warehouses with the highest stock quantity (inventory), then list the top 3 item categories in those warehouses.”
“Identify active CRM accounts with platinum tier, then show their total invoice amount from finance.”
“Get customers from ecommerce in the USA, then show their account manager regions in CRM.”
“Find overdue invoices (finance), then check if those customers had escalated interactions (CRM).”
“List employees hired in the last 2 years (HR), then show performance review scores for those employees.”
