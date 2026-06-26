"""Pydantic models for requests and responses.

These models are shared by the FastAPI routes and the MCP-friendly function
layer. All list fields default to empty lists so a freshly connected builder
with no profile data still serializes cleanly.
"""

from __future__ import annotations

from typing import Optional

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


class ConnectResponse(BaseModel):
    status: str
    profile: Profile
    next: str


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
