from typing import Literal
from pydantic import BaseModel, Field


class UserMeasurements(BaseModel):
    height: float = Field(..., description="Height in cm")
    weight: float = Field(..., description="Weight in kg")
    chest: float = Field(..., description="Chest circumference in cm")
    waist: float = Field(..., description="Waist circumference in cm")
    fit_preference: Literal["slim", "regular", "relaxed"] = Field(
        "regular", description="Preferred fit style"
    )


class AssistantRequest(BaseModel):
    user: UserMeasurements
    item_ids: list[str] = Field(
        default=[],
        description="Specific item IDs to try on. Empty = try all catalogue items.",
    )


class SizeRecommendation(BaseModel):
    item_id: str
    item_name: str
    category: str
    recommended_size: str
    confidence: Literal["high", "medium", "low"]
    reasoning: str
    fit_notes: str


class AssistantResponse(BaseModel):
    user: UserMeasurements
    recommendations: list[SizeRecommendation]
    general_advice: str