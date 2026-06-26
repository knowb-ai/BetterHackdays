"""Pydantic models for requests and responses.

These models are shared by the FastAPI routes and the MCP-friendly function
layer. All list fields default to empty lists so a freshly connected builder
with no profile data still serializes cleanly.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Profile -----------------------------------------------------------------


class ProfileBase(BaseModel):
    """Profile fields a harness may set when connecting or updating."""

    model_config = ConfigDict(populate_by_name=True)

    harness_id: str = Field(..., description="Unique harness identifier")
    display_label: str = Field("New builder")
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    preferred_role: Optional[str] = None
    project_vibe: Optional[str] = None
    looking_for: list[str] = Field(default_factory=list)
    availability: Optional[str] = None


class ConnectRequest(BaseModel):
    harness_id: str = Field(..., description="Unique harness identifier")


class UpdateProfileRequest(BaseModel):
    harness_id: str = Field(..., description="Unique harness identifier")
    display_label: Optional[str] = "New builder"
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    preferred_role: Optional[str] = None
    project_vibe: Optional[str] = None
    looking_for: list[str] = Field(default_factory=list)
    availability: Optional[str] = None


class Profile(ProfileBase):
    is_seeded: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SurveyQuestion(BaseModel):
    num: int
    key: str
    text: str
    type: str
    options: list[str] = Field(default_factory=list)
    progress: str


class ConnectResponse(BaseModel):
    status: str
    profile: Profile
    next: str
    question: Optional[SurveyQuestion] = None


class UpdateProfileResponse(BaseModel):
    status: str
    profile: Profile
    next: str


# --- Matchmaking cards --------------------------------------------------------


class MatchCard(BaseModel):
    harness_id: str
    display_label: str
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    preferred_role: Optional[str] = None
    project_vibe: Optional[str] = None
    looking_for: list[str] = Field(default_factory=list)
    match_score: int
    match_reason: str


class CardsResponse(BaseModel):
    cards: list[MatchCard]


# --- Swipes / matches ---------------------------------------------------------


class SwipeRequest(BaseModel):
    from_harness_id: str
    to_harness_id: str


class SwipeResponse(BaseModel):
    status: str
    next: str
    mutual_match: Optional[bool] = None
    match_id: Optional[str] = None
    harness_ids: Optional[list[str]] = None


class MatchRecord(BaseModel):
    match_id: str
    harness_ids: list[str]
    status: str
    next: str


class MatchesResponse(BaseModel):
    matches: list[MatchRecord]


# --- Health -------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    service: str
    runtime: str


# --- Survey onboarding --------------------------------------------------------


class SurveyAnswerRequest(BaseModel):
    harness_id: str = Field(..., description="Unique harness identifier")
    answer: str = Field(..., description="Free-text answer to the current question")


class SurveyAnswerResponse(BaseModel):
    status: str
    harness_id: Optional[str] = None
    answered: Optional[int] = None
    saved: dict[str, Any] = Field(default_factory=dict)
    next_question: Optional[SurveyQuestion] = None
    done: bool = False
    # Populated with the top match cards once the survey is `done`.
    matches: list[MatchCard] = Field(default_factory=list)


class SurveyStateResponse(BaseModel):
    harness_id: str
    progress: str
    question: Optional[SurveyQuestion] = None
    done: bool
