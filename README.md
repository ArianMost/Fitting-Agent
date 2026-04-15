# 👗 Virtual Fitting Room Agent

AI-powered size recommendation agent built with **PydanticAI** + **FastAPI**,
created for the Schwarz Digits × 42 Heilbronn Agents Workshop.

---

## Project structure

```
fittingroomagent/
│
├── app/
│   ├── evaluation/
│   │   ├── evaluator.py          # orchestrates full eval pipeline
│   │   └── metrics.py            # deterministic (code-based) judges
│   │
│   ├── models/
│   │   ├── assistance_response.py  # UserMeasurements, AssistantRequest/Response
│   │   └── evaluation.py           # CodeJudgeResult, LLMJudgeResult, EvalSummary
│   │
│   ├── routers/
│   │   └── assistant.py          # POST /assistant/recommend
│   │
│   ├── services/
│   │   ├── agent.py              # PydanticAI agent + 4 tools
│   │   ├── database.py           # in-memory store loaded from store_data.json
│   │   └── langfuse_client.py    # observability (no-op if keys not set)
│   │
│   ├── __init__.py
│   └── main.py                   # FastAPI app factory
│
├── data/
│   ├── eval_data.json            # 4 annotated eval cases
│   ├── initial_data.json         # seed users
│   └── store_data.json           # clothing catalogue + size charts
│
├── scripts/
│   └── run_evaluation_pipeline.py
│
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your OpenAI key
export OPENAI_API_KEY=sk-...

# 3. (Optional) Langfuse observability
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...
```

---

## Run the API

```bash
uvicorn app.main:app --reload
```

Interactive docs at **http://localhost:8000/docs**

### Example request

```bash
curl -X POST http://localhost:8000/assistant/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "height": 180,
      "weight": 75,
      "chest": 98,
      "waist": 82,
      "fit_preference": "regular"
    },
    "item_ids": ["top_001", "bottom_001", "jacket_001"]
  }'
```

### Example response

```json
{
  "user": { "height": 180, "weight": 75, "chest": 98, "waist": 82, "fit_preference": "regular" },
  "recommendations": [
    {
      "item_id": "top_001",
      "item_name": "Classic White Oxford Shirt",
      "category": "top",
      "recommended_size": "L",
      "confidence": "high",
      "reasoning": "Your chest is 98 cm; size L has a 100 cm chest — 2 cm of ease for a comfortable regular fit.",
      "fit_notes": "Relaxed through the shoulders, true to size."
    }
  ],
  "general_advice": "Your tapered torso suits fitted tops well. At 180 cm standard lengths should work throughout."
}
```

---

## Run the evaluation pipeline

```bash
python -m scripts.run_evaluation_pipeline
```

Results are written to `data/eval_results.json`. The script exits with code `1`
if the pass rate falls below 75 %.

---

## Architecture

### Agent flow (ReAct pattern)

```
AssistantRequest
      │
      ▼
 get_catalogue()              ← what items are in the store?
      │
      ▼
 get_item_size_chart(item_id) ← what are the brand's exact measurements?
      │
      ▼
 calculate_size_fit(...)      ← which size minimises the fit delta?
      │
      ▼
 get_body_type_advice(...)    ← personalised general tips
      │
      ▼
 AssistantResponse            ← validated Pydantic output
```

### Evaluation pipeline

```
data/eval_data.json
      │
      ▼
run_agent()                   ← agent produces AssistantResponse
      │
      ├── metrics.run_code_judge()    ← size accuracy + tool coverage
      │
      └── evaluator._llm_judge()     ← LLM scores reasoning & advice quality
      │
      ▼
EvalSummary → data/eval_results.json
```

### Evaluation metrics

| Metric                 | Type       | Description                                           |
|------------------------|------------|-------------------------------------------------------|
| `size_accuracy`        | Code judge | % of items where the recommended size is correct      |
| `tool_coverage`        | Code judge | % of expected tools that were actually called         |
| `reasoning_clarity`    | LLM judge  | 1–5: Are specific measurements cited in the reasoning?|
| `advice_usefulness`    | LLM judge  | 1–5: Is the general advice personalised and actionable?|
| `confidence_appropriate` | LLM judge | Does the confidence level match the actual fit delta? |
| `overall_score`        | LLM judge  | 1–5: Holistic quality rating                          |

---

## Extending the project

**Add catalogue items** — edit `data/store_data.json`.

**Add a new tool** — define a plain Python function in `app/services/agent.py`
and decorate it with `@fitting_room_agent.tool_plain`.

**Change the LLM** — edit the `OpenAIModel(...)` call in `app/services/agent.py`.
Any OpenAI-compatible endpoint works (local models via LiteLLM, Aleph Alpha, etc.).

**Add eval cases** — add entries to `data/eval_data.json` following the existing schema.

**Enable Langfuse tracing** — set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.
Every recommendation call will be traced automatically.