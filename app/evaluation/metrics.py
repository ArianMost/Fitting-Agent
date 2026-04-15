"""
metrics.py — deterministic (code-based) evaluation metrics.

These are fast, cheap, and objective — the "code judge" from the workshop slides.
"""

from app.models.assistance_response import AssistantResponse
from app.models.evaluation import CodeJudgeResult

# Thresholds for passing
SIZE_ACCURACY_THRESHOLD = 0.75
TOOL_COVERAGE_THRESHOLD = 0.75


# ── Individual metrics ────────────────────────────────────────────────────────

def size_accuracy(
    response: AssistantResponse,
    expected: dict[str, str],
) -> dict[str, bool]:
    """
    Compare each recommended size against the expected size.

    Returns a per-item bool map: True = correct, False = wrong / missing.
    """
    rec_map = {r.item_id: r.recommended_size for r in response.recommendations}
    return {
        item_id: rec_map.get(item_id) == exp_size
        for item_id, exp_size in expected.items()
    }


def tool_coverage(
    actual_tool_calls: list[str],
    expected_tool_calls: list[str],
) -> float:
    """
    Fraction of expected tools that appear in the actual call list.

    Returns 1.0 if expected_tool_calls is empty.
    """
    if not expected_tool_calls:
        return 1.0
    called = set(actual_tool_calls)
    expected = set(expected_tool_calls)
    return len(called & expected) / len(expected)


def confidence_distribution(response: AssistantResponse) -> dict[str, int]:
    """Count how many recommendations fall into each confidence tier."""
    counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for rec in response.recommendations:
        counts[rec.confidence] = counts.get(rec.confidence, 0) + 1
    return counts


# ── Composite code judge ──────────────────────────────────────────────────────

def run_code_judge(
    eval_id: str,
    response: AssistantResponse,
    expected_sizes: dict[str, str],
    expected_tools: list[str],
    actual_tools: list[str],
) -> CodeJudgeResult:
    """
    Run all deterministic checks and return a CodeJudgeResult.

    Args:
        eval_id:        Identifier of the eval case.
        response:       The AssistantResponse produced by the agent.
        expected_sizes: Mapping of item_id → expected correct size.
        expected_tools: List of tool names that should have been called.
        actual_tools:   List of tool names that were actually called.
    """
    correct = size_accuracy(response, expected_sizes)
    acc = sum(correct.values()) / len(correct) if correct else 0.0
    cov = tool_coverage(actual_tools, expected_tools)
    passed = acc >= SIZE_ACCURACY_THRESHOLD and cov >= TOOL_COVERAGE_THRESHOLD

    return CodeJudgeResult(
        eval_id=eval_id,
        size_accuracy=round(acc, 3),
        correct_sizes=correct,
        tool_coverage=round(cov, 3),
        passed=passed,
    )