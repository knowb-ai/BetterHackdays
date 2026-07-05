"""Pydantic models for requests and responses.

These models are shared by the FastAPI routes and the MCP-friendly function
layer. All list fields default to empty lists so a freshly connected builder
with no profile data still serializes cleanly.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

HarnessId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=80,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    ),
]


# --- Profile -----------------------------------------------------------------


class ProfileBase(BaseModel):
    """Profile fields a harness may set when connecting or updating."""

    model_config = ConfigDict(populate_by_name=True)

    harness_id: HarnessId = Field(..., description="Unique harness identifier")
    display_label: str = Field("New builder")
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    preferred_role: Optional[str] = None
    project_vibe: Optional[str] = None
    looking_for: list[str] = Field(default_factory=list)
    availability: Optional[str] = None


class ConnectRequest(BaseModel):
    harness_id: HarnessId = Field(..., description="Unique harness identifier")


class UpdateProfileRequest(BaseModel):
    harness_id: HarnessId = Field(..., description="Unique harness identifier")
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
    harness_id: HarnessId
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
    from_harness_id: HarnessId
    to_harness_id: HarnessId


class SwipeResponse(BaseModel):
    status: str
    next: str
    mutual_match: Optional[bool] = None
    match_id: Optional[str] = None
    harness_ids: Optional[list[str]] = None


class MatchRecord(BaseModel):
    match_id: str
    harness_ids: list[HarnessId]
    status: str
    next: str


class MatchesResponse(BaseModel):
    matches: list[MatchRecord]


# --- Health -------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    service: str
    runtime: str


# --- Event ingest -------------------------------------------------------------


class EventSource(BaseModel):
    source_type: Literal["pasted_text"]
    source_label: str
    source_url: Optional[str] = None
    captured_at: str


class EventFieldSourceNote(BaseModel):
    field: str
    source_label: str
    confidence: Literal["high", "medium", "low"]
    note: str


class EventTeamSize(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class EventDeadline(BaseModel):
    name: str
    due_at: Optional[str] = None
    description: Optional[str] = None


class EventJudgingCriterion(BaseModel):
    name: str
    description: Optional[str] = None


class EventSponsor(BaseModel):
    name: str
    requirements: list[str] = Field(default_factory=list)


class EventSubmission(BaseModel):
    url: Optional[str] = None
    requirements: list[str] = Field(default_factory=list)


class EventContext(BaseModel):
    event_name: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    tracks: list[str] = Field(default_factory=list)
    team_size: Optional[EventTeamSize] = None
    deadlines: list[EventDeadline] = Field(default_factory=list)
    judging_criteria: list[EventJudgingCriterion] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    sponsors: list[EventSponsor] = Field(default_factory=list)
    submission: EventSubmission = Field(default_factory=EventSubmission)
    allowed_tools: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    sources: list[EventSource] = Field(default_factory=list)
    source_notes: list[EventFieldSourceNote] = Field(default_factory=list)


class EventIngestTextRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20)]
    source_label: str = "Pasted event text"
    source_url: Optional[str] = None


class EventIngestResponse(BaseModel):
    status: str
    event: EventContext
    missing_fields: list[str] = Field(default_factory=list)
    next: str


# --- Survey onboarding --------------------------------------------------------


class SurveyAnswerRequest(BaseModel):
    harness_id: HarnessId = Field(..., description="Unique harness identifier")
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
    harness_id: HarnessId
    progress: str
    question: Optional[SurveyQuestion] = None
    done: bool
