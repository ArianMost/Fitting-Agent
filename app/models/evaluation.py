from pydantic import BaseModel


class CodeJudgeResult(BaseModel):
    eval_id: str
    size_accuracy: float          # 0–1: fraction of items with correct size
    correct_sizes: dict[str, bool]
    tool_coverage: float          # 0–1: fraction of expected tools called
    passed: bool                  # True if both metrics >= 0.75


class LLMJudgeResult(BaseModel):
    eval_id: str
    reasoning_clarity: int        # 1–5
    advice_usefulness: int        # 1–5
    confidence_appropriate: bool
    overall_score: float          # 1–5
    judge_feedback: str


class CaseResult(BaseModel):
    eval_id: str
    description: str
    code: CodeJudgeResult
    llm: LLMJudgeResult


class EvalSummary(BaseModel):
    total_cases: int
    avg_size_accuracy: float
    avg_llm_score: float
    pass_rate: float
    per_case: list[CaseResult]