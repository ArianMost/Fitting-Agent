"""
routers/assistant.py — FastAPI router exposing the fitting-room agent via REST.
"""

from fastapi import APIRouter, HTTPException

from app.models.assistance_response import AssistantRequest, AssistantResponse
from app.services import agent as agent_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/recommend", response_model=AssistantResponse)
async def recommend_sizes(request: AssistantRequest) -> AssistantResponse:
    """
    Given a customer's body measurements, return size recommendations
    for every requested clothing item.

    - **user**: body measurements + fit preference
    - **item_ids**: list of catalogue item IDs to evaluate
                    (leave empty to try the full catalogue)
    """
    try:
        response = await agent_service.run_agent(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return response