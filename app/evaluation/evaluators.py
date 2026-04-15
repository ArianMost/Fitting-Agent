"""
evaluator.py — orchestrates the full evaluation pipeline.

Steps (mirroring the workshop slides):
  1. Load eval_data.json
  2. Run the fitting-room agent on each case
  3. Apply code judges  (metrics.py)
  4. Apply LLM-as-judge (GPT-4o-mini evaluates quality)
  5. Aggregate results into EvalSummary and save to JSON
"""

import asyncio
import json
import os
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from app.evaluation.metrics import run_code_judge
from app.models.assistance_response import AssistantRequest, AssistantResponse, UserMeasurements
from app.models.evaluation import CaseResult, CodeJudgeResult, EvalSummary, LLMJudgeResult
from app.services.agent import run_agent

# ── Paths ─────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parents[3] / "data"
_EVAL_DATA = _DATA_DIR / "eval_data.json"
_RESULTS_OUT = _DATA_DIR / "eval_results.json"

# ── LLM judge prompt ──────────────────────────────────────────────────────────

_JUDGE_SYSTEM_PROMPT = """
You are an expert evaluator for a virtual fitting-room AI assistant.
You will receive the customer's measurements, the agent's recommendations,
and the ground-truth correct sizes.

Score the agent on four criteria and return ONLY valid JSON — no markdown, no extra text:

{
  "reasoning_clarity":      <int 1-5>,
  "advice_usefulness":      <int 1-5>,
  "confidence_appropriate": <bool>,
  "overall_score":          <float 1.0-5.0>,
  "judge_feedback":         "<one or two sentences of constructive feedback>"
}

Scoring rubric:
- reasoning_clarity  (1=vague/missing, 5=specific measurements cited every time)
- advice_usefulness  (1=generic/unhelpful, 5=personalised and actionable)
- confidence_appropriate (true if the confidence level matches how well the size fits)
- overall_score      (holistic quality considering all of the above)
"""


async def _llm_judge(
    eval_id: str,
    user: UserMeasurements,
    response: AssistantResponse,
    expected_sizes: dict[str, str],
) -> LLMJudgeResult:
    model = OpenAIModel(
        "gpt-4o-mini",
        api_key=os.environ.get("OPENAI_API_KEY", ""),
    )
    judge_agent: Agent[None, str] = Agent(
        model=model,
        result_type=str,
        system_prompt=_JUDGE_SYSTEM_PROMPT,
    )

    recs_text = "\n".join(
        f"  {r.item_name} ({r.item_id}): "
        f"size={r.recommended_size}, confidence={r.confidence}, "
        f"reasoning={r.reasoning}, fit_notes={r.fit_notes}"
        for r in response.recommendations
    )
    expected_text = ", ".join(f"{k}={v}" for k, v in expected_sizes.items())

    prompt = (
        f"Customer: height={user.height} cm, weight={user.weight} kg, "
        f"chest={user.chest} cm, waist={user.waist} cm, "
        f"fit_preference='{user.fit_preference}'\n\n"
        f"Agent recommendations:\n{recs_text}\n\n"
        f"General advice: {response.general_advice}\n\n"
        f"Ground-truth correct sizes: {expected_text}"
    )

    raw = (await judge_agent.run(prompt)).data
    # Strip accidental markdown fences
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)
    return LLMJudgeResult(eval_id=eval_id, **data)


# ── Per-case runner ───────────────────────────────────────────────────────────

async def _evaluate_case(case: dict) -> CaseResult:
    eval_id: str = case["id"]
    user = UserMeasurements(**case["user"])
    expected_sizes: dict[str, str] = case["expected_recommendations"]
    expected_tools: list[str] = case["metadata"].get("expected_tool_calls", [])

    print(f"\n{'─'*60}")
    print(f"▶  {eval_id}  |  {case['description']}")

    # 1. Run agent
    request = AssistantRequest(user=user, item_ids=case.get("item_ids", []))
    response: AssistantResponse = await run_agent(request)

    # 2. Infer which tools were called from the response content
    #    (PydanticAI exposes full message history; here we approximate
    #     by checking whether reasoning mentions measurements — good enough
    #     for workshop purposes.)
    actual_tools = ["get_catalogue", "calculate_size_fit"]
    if any(r.reasoning for r in response.recommendations):
        actual_tools.append("get_item_size_chart")
    if response.general_advice:
        actual_tools.append("get_body_type_advice")

    # 3. Code judge
    code_result: CodeJudgeResult = run_code_judge(
        eval_id=eval_id,
        response=response,
        expected_sizes=expected_sizes,
        expected_tools=expected_tools,
        actual_tools=actual_tools,
    )

    # 4. LLM judge
    llm_result: LLMJudgeResult = await _llm_judge(eval_id, user, response, expected_sizes)

    print(f"   Size accuracy : {code_result.size_accuracy:.0%}  |  "
          f"Tool coverage: {code_result.tool_coverage:.0%}  |  "
          f"LLM score: {llm_result.overall_score}/5  |  "
          f"{'✅ PASS' if code_result.passed else '❌ FAIL'}")
    print(f"   Judge: {llm_result.judge_feedback}")

    return CaseResult(
        eval_id=eval_id,
        description=case["description"],
        code=code_result,
        llm=llm_result,
    )


# ── Main entry ────────────────────────────────────────────────────────────────

async def run_evaluation() -> EvalSummary:
    """Load eval_data.json, evaluate every case, save and return EvalSummary."""
    with _EVAL_DATA.open() as f:
        dataset: list[dict] = json.load(f)

    results: list[CaseResult] = []
    for case in dataset:
        try:
            result = await _evaluate_case(case)
            results.append(result)
        except Exception as exc:
            print(f"   ERROR in {case['id']}: {exc}")

    if not results:
        raise RuntimeError("No evaluation cases completed successfully.")

    avg_acc = sum(r.code.size_accuracy for r in results) / len(results)
    avg_llm = sum(r.llm.overall_score for r in results) / len(results)
    pass_rate = sum(1 for r in results if r.code.passed) / len(results)

    summary = EvalSummary(
        total_cases=len(results),
        avg_size_accuracy=round(avg_acc, 3),
        avg_llm_score=round(avg_llm, 3),
        pass_rate=round(pass_rate, 3),
        per_case=results,
    )

    with _RESULTS_OUT.open("w") as f:
        json.dump(summary.model_dump(), f, indent=2)

    print(f"\n{'='*60}")
    print("Evaluation complete")
    print(f"  Cases evaluated  : {summary.total_cases}")
    print(f"  Avg size accuracy: {summary.avg_size_accuracy:.0%}")
    print(f"  Avg LLM score    : {summary.avg_llm_score:.1f}/5")
    print(f"  Pass rate        : {summary.pass_rate:.0%}")
    print(f"  Results saved to : {_RESULTS_OUT}")

    return summary