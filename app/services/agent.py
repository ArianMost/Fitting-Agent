"""
agent.py — Virtual Fitting Room AI agent built with PydanticAI.

The agent follows a ReAct loop:
  1. get_catalogue           → discover available items
  2. get_item_size_chart     → inspect brand-specific sizing
  3. calculate_size_fit      → find best size for the user's measurements
  4. get_body_type_advice    → personalised general tips
  → returns AssistantResponse (validated Pydantic model)
"""

import os
from typing import Any

from pydantic_ai import Agent

from app.models.assistance_response import (
    AssistantRequest,
    AssistantResponse,
    UserMeasurements,
)
from app.services import database as db

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are an expert virtual fitting-room assistant. Your goal is to recommend
the best clothing size for each item, fully grounded in the customer's body
measurements and the brand's own size chart.

Workflow (follow this order):
1. Call `get_catalogue` to see the available items.
2. For every item the customer wants to try, call `get_item_size_chart` to
   retrieve the exact brand measurements per size.
3. Call `calculate_size_fit` for each item — it returns the best size match
   taking fit preference (slim / regular / relaxed) into account.
4. Call `get_body_type_advice` once for personalised general tips.
5. Return an AssistantResponse with one SizeRecommendation per item.

Rules:
- Base every recommendation on tool output, never on guessed numbers.
- Include *specific* measurements in the reasoning field
  (e.g. "Your chest is 98 cm; size L has a 100 cm chest — 2 cm of ease").
- If confidence is "low", mention in fit_notes that the customer should
  also try the next size up.
- Keep fit_notes short and actionable.

The response needs to be like this:
{
  "user": {
    "height": 180,
    "weight": 70,
    "chest": 140,
    "waist": 80,
    "fit_preference": "regular"
  },
  "recommendations": [
    {
      "item_id": "top_001",
      "item_name": "Classic White Oxford Shirt",
      "category": "top",
      "recommended_size": "M",
      "confidence": "low",
      "reasoning": "Your chest is 140 cm...",
      "fit_notes": "Confidence is low. You should also try the next size up."
    },
    {
      "item_id": "top_002",
      "item_name": "Slim-Fit Polo",
      "category": "top",
      "recommended_size": "L",
      "confidence": "low",
      "reasoning": Your waist is 90 cm...,
      "fit_notes": "Confidence is low. You should also try the next size up."
    },
  ],
  "general_advice": "Unable to provide specific body type advice as the required tool is not available."
}
"""

# ── Model + agent ─────────────────────────────────────────────────────────────




# ── Tools ─────────────────────────────────────────────────────────────────────

def get_catalogue() -> list[dict[str, Any]]:
    """Return a summary of every item available in the store catalogue."""
    return db.list_catalogue()


def get_item_size_chart(item_id: str) -> dict[str, Any]:
    """
    Return the full size chart for a specific clothing item.

    Args:
        item_id: The unique identifier of the item (e.g. 'top_001').
    """
    item = db.get_item(item_id)
    if item is None:
        return {"error": f"Item '{item_id}' not found in catalogue."}
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "brand": item["brand"],
        "size_chart": item["size_chart"],
    }


def calculate_size_fit(
    item_id: str,
    chest_cm: float,
    waist_cm: float,
    fit_preference: str = "regular",
) -> dict[str, Any]:
    """
    Calculate the best-fitting size for an item given body measurements.

    Args:
        item_id:         The item to evaluate.
        chest_cm:        Customer chest circumference in cm.
        waist_cm:        Customer waist circumference in cm.
        fit_preference:  'slim' (−2 cm ease) | 'regular' (0) | 'relaxed' (+4 cm).
    """
    item = db.get_item(item_id)
    if item is None:
        return {"error": f"Item '{item_id}' not found."}

    ease_map = {"slim": -2, "regular": 0, "relaxed": 4}
    ease = ease_map.get(fit_preference, 0)
    target_chest = chest_cm + ease
    target_waist = waist_cm + ease

    best_size: str | None = None
    best_delta = float("inf")

    for size, dims in item["size_chart"].items():
        delta = 0.0
        if "chest" in dims:
            delta += abs(dims["chest"] - target_chest)
        if "waist" in dims:
            delta += abs(dims["waist"] - target_waist)
        if delta < best_delta:
            best_delta = delta
            best_size = size

    if best_delta <= 3:
        confidence = "high"
    elif best_delta <= 7:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "item_id": item_id,
        "item_name": item["name"],
        "recommended_size": best_size,
        "confidence": confidence,
        "fit_delta_cm": round(best_delta, 1),
        "ease_applied_cm": ease,
    }


def get_body_type_advice(
    height: float,
    weight: float,
    chest: float,
    waist: float,
) -> dict[str, Any]:
    """
    Provide personalised body-type fitting advice.

    Args:
        height: Height in cm.
        weight: Weight in kg.
        chest:  Chest circumference in cm.
        waist:  Waist circumference in cm.
    """
    bmi = weight / ((height / 100) ** 2)
    cw_ratio = chest / waist

    if bmi < 18.5:
        build = "slim"
    elif bmi < 25:
        build = "athletic / average"
    elif bmi < 30:
        build = "fuller"
    else:
        build = "plus"

    tips: list[str] = []
    if cw_ratio > 1.2:
        tips.append(
            "Your tapered torso suits slim-fit or fitted tops well."
        )
    elif cw_ratio < 1.05:
        tips.append(
            "Your chest and waist are similar in size — regular or relaxed fits "
            "will avoid pulling across the chest."
        )

    if height < 170:
        tips.append(
            "Look for cropped or regular-length styles; longer cuts can shorten "
            "the silhouette."
        )
    elif height > 185:
        tips.append(
            "Consider 'tall' or 'long' size options for better shirt and trouser length."
        )

    return {
        "bmi": round(bmi, 1),
        "build": build,
        "chest_waist_ratio": round(cw_ratio, 2),
        "tips": tips,
    }


fitting_agent = Agent(
    "vertexai:gemini-2.5-flash",
    output_type=AssistantResponse,
    instrument=True,
    tools=[get_catalogue, get_item_size_chart, calculate_size_fit],
    system_prompt=SYSTEM_PROMPT
)

# ── Public runner ─────────────────────────────────────────────────────────────

async def run_agent(request: AssistantRequest) -> AssistantResponse:
    """Run the fitting-room agent for a given request and return the response."""
    u = request.user
    items_hint = (
        f"Item IDs to try: {request.item_ids}."
        if request.item_ids
        else "Try all items in the catalogue."
    )
    prompt = (
        f"Please recommend sizes for this customer.\n"
        f"Measurements: height={u.height} cm, weight={u.weight} kg, "
        f"chest={u.chest} cm, waist={u.waist} cm, "
        f"fit_preference='{u.fit_preference}'.\n"
        f"{items_hint}"
    )
    result = await fitting_agent.run(prompt)
    return result.output