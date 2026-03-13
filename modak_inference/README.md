# NL→SQL on Modal + vLLM

Self-hosted NL-to-SQL system with two Qwen3 models on Modal, replacing the
original OpenAI/Gemini calls with GPU-accelerated local inference.

---

## Architecture

```
User HTTP Request
       │
       ▼
FastAPI  /query   (Modal CPU container)
       │
       ├──► OrchestratorModel.generate()   ── Qwen3-4B   FP16  │ A10G 24 GB
       │         create_plan()  →  JSON step plan               │
       │                                                        │
       ├──► CoderModel.generate()          ── Qwen3-30B-A3B FP8 │ A100 80 GB
       │         generate_sql()  →  DATABASE/SQL lines          │
       │         (auto-retry on SQL error, max 2 attempts)      │
       │                                                        │
       └──► OrchestratorModel.generate()
                 synthesize()  →  natural-language answer
```

### Why Qwen3-30B-A3B for SQL?

It is a **Mixture-of-Experts** model: 30 B total parameters but only **3 B
active** per forward pass. This gives accuracy close to a full 30 B dense
model at the compute cost of a 3 B model. With FP8 quantisation the weights
occupy ≈ 30 GB (fits comfortably on one A100-80GB with room for a large KV cache).

### vLLM low-latency settings applied

| Knob | Coder (A100) | Orchestrator (A10G) |
|---|---|---|
| Weight dtype | FP8 | FP16 |
| KV cache dtype | fp8_e5m2 | auto (FP16) |
| PagedAttention block size | 16 | 16 |
| FlashAttention-2 | auto (Ampere) | auto (Ampere) |
| Prefix caching | ✅ schema shared | ✅ schema shared |
| CUDA Graphs | ✅ (enforce_eager=False) | ✅ |
| Chunked prefill | ✅ | ✅ |
| Qwen3 /no_think token | ✅ SQL gen | ✅ synthesis |
| max_model_len | 4096 | 4096 |
| gpu_memory_utilization | 0.95 | 0.92 |

---

## Files

```
modal_app.py      Main Modal app — model classes + FastAPI web server
db_schemas.py     DB schema registry + safe SQLite executor
prompt_utils.py   ChatML prompt builder (Qwen3 format, /no_think)
requirements.txt  Local dev dependencies
databases/        SQLite database files (created by fake_database.py)
```

---

## Quickstart

### 1. Install Modal CLI

```bash
pip install modal
modal setup          # authenticate with your Modal account
```

### 2. (Optional) Add HuggingFace token

Some Qwen3 models require a HF token for download:

```bash
modal secret create huggingface-secret HF_TOKEN=hf_...
```

### 3. Add app secrets (only needed for /transcribe endpoint)

```bash
modal secret create app-secrets OPENAI_API_KEY=sk-...
```

### 4. Local dev (live reload)

```bash
modal serve modal_app.py
```

This prints a temporary HTTPS URL. Requests are forwarded to your local
process. Model weights are downloaded to the `nl-sql-weights` Volume on
first run (≈ 5–10 min). Subsequent cold starts are fast.

### 5. Production deploy

```bash
modal deploy modal_app.py
```

Your API is now live at:
`https://<your-workspace>--nl-sql-vllm-web.modal.run`

### 6. Test

```bash
curl -X POST https://<url>/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show top 5 customers by total order value"}'
```

---

## Cost estimate (Modal on-demand pricing, 2025)

| Component | GPU | Price/hr | Typical req time | Cost/1000 req |
|---|---|---|---|---|
| Orchestrator | A10G | $1.10 | ~0.5 s | ~$0.15 |
| Coder | A100-80GB | $3.70 | ~0.3 s | ~$0.31 |
| Web endpoint | CPU | $0.016 | negligible | ~$0.01 |

Both containers scale to zero when idle. `scaledown_window=300` keeps them
warm for 5 minutes after the last request.

---

## Extending

**Add a new database:** add an entry to `DB_SCHEMAS` in `db_schemas.py`.
The schema context is injected into every prompt automatically.

**Enable speculative decoding:** add `speculative_model="[ngram]"` and
`num_speculative_tokens=5` to the `CoderModel` `AsyncEngineArgs` — this can
cut decode latency ~30% for short SQL outputs.

**Tensor parallelism for larger models:** set `tensor_parallel_size=2` in
`AsyncEngineArgs` and `gpu=modal.gpu.A100(count=2, size="80GB")`.

**Streaming responses:** replace `modal.method()` with `modal.method()` and
`async_generator` to stream tokens back to the client via SSE.
