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

EventIngestText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=20, max_length=12_000),
]

EventIngestSourceLabel = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]

EventIngestSourceUrl = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=500),
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
    text: EventIngestText
    source_label: EventIngestSourceLabel = "Pasted event text"
    source_url: Optional[EventIngestSourceUrl] = None


class EventIngestResponse(BaseModel):
    status: str
    event: EventContext
    missing_fields: list[str] = Field(default_factory=list)
    next: str


# --- Planner -----------------------------------------------------------------


class IdeaSuggestion(BaseModel):
    idea_type: Literal["safe_default", "ambitious", "niche", "fast_fallback"]
    summary: str
    why_it_fits: str
    main_tradeoff: str
    score: int
    signals: list[str] = Field(default_factory=list)


class IdeaSuggestionsRequest(BaseModel):
    event: EventContext
    profile: Optional[Profile] = None
    team: list[Profile] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class IdeaSuggestionsResponse(BaseModel):
    status: str
    ideas: list[IdeaSuggestion] = Field(default_factory=list)
    ranking_signals: list[str] = Field(default_factory=list)
    next: str


class HackDayContext(BaseModel):
    hack_day_id: Optional[str] = None
    name: Optional[str] = None
    state: Optional[Literal["active", "matchable", "matched", "team_room"]] = None
    participant_state: Optional[Literal["active", "matchable", "matched"]] = None


class TeamRoomContext(BaseModel):
    room_id: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[str] = None
    selected_idea: Optional[str] = None


class WorkspaceRepoContext(BaseModel):
    owner: Optional[str] = None
    repo: Optional[str] = None
    default_branch: str = "main"
    permission_status: Optional[str] = None
    connected: bool = False


class ProcessTimelineStage(BaseModel):
    stage: Literal[
        "before_event",
        "first_30_minutes",
        "first_2_hours",
        "validation",
        "demo_prep",
        "final_submission",
    ]
    label: str
    when: str
    tasks: list[str] = Field(default_factory=list)
    decision_checkpoint: str
    risk_flags: list[str] = Field(default_factory=list)
    optional_help: list[str] = Field(default_factory=list)
    deadline: Optional[EventDeadline] = None


class ProcessTimelineRequest(BaseModel):
    event: EventContext
    profile: Optional[Profile] = None
    team: list[Profile] = Field(default_factory=list)
    hack_day: Optional[HackDayContext] = None
    team_room: Optional[TeamRoomContext] = None
    workspace_repo: Optional[WorkspaceRepoContext] = None


class ProcessTimelineResponse(BaseModel):
    status: str
    stages: list[ProcessTimelineStage] = Field(default_factory=list)
    timeline_signals: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    next: str


class PrepChecklistItem(BaseModel):
    task: str
    why: str
    done_hint: str
    linked_doc: Optional[str] = None


class PrepChecklistSection(BaseModel):
    section: Literal[
        "prep_tasks",
        "first_hour_focus",
        "missing_inputs",
        "optional_help",
        "workspace_next_steps",
    ]
    title: str
    items: list[PrepChecklistItem] = Field(default_factory=list)


class PrepChecklistRequest(BaseModel):
    event: EventContext
    profile: Optional[Profile] = None
    team: list[Profile] = Field(default_factory=list)
    hack_day: Optional[HackDayContext] = None
    team_room: Optional[TeamRoomContext] = None
    workspace_repo: Optional[WorkspaceRepoContext] = None


class PrepChecklistResponse(BaseModel):
    status: str
    sections: list[PrepChecklistSection] = Field(default_factory=list)
    checklist_signals: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    next: str


# --- Slug resolution ---------------------------------------------------------


class WorkspaceRepoResolutionRecord(BaseModel):
    owner: str
    repo: str
    default_branch: str = "main"
    permission_status: Optional[str] = None
    allowed_write_targets: list[str] = Field(default_factory=list)
    last_synced_planning_snapshot: Optional[str] = None


class TeamRoomResolutionRecord(BaseModel):
    room_id: str
    keyword: str
    join_mode: Literal["open", "approval", "invite_only"] = "open"
    participant_ids: list[str] = Field(default_factory=list)
    state: Literal["room_created", "workspace_connected"] = "room_created"
    workspace_repo: Optional[WorkspaceRepoResolutionRecord] = None


class ParticipantStateRecord(BaseModel):
    participant_id: str
    state: Literal[
        "active",
        "matchable",
        "matched",
        "room_created",
        "workspace_connected",
    ]


class HackDayResolutionRecord(BaseModel):
    hack_day_id: str
    code: str
    name: str
    status: Literal["upcoming", "active", "ended"] = "active"
    expires_at: Optional[str] = None
    participant_states: list[ParticipantStateRecord] = Field(default_factory=list)
    team_rooms: list[TeamRoomResolutionRecord] = Field(default_factory=list)


class StandaloneSlugRecord(BaseModel):
    slug: str
    target_type: Literal["hack_day", "team_room"]
    target_id: str
    expires_at: Optional[str] = None


class SlugResolveRequest(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=160)
    hack_days: list[HackDayResolutionRecord] = Field(default_factory=list)
    standalone_slugs: list[StandaloneSlugRecord] = Field(default_factory=list)
    caller_participant_id: Optional[str] = None


class SlugResolveResponse(BaseModel):
    status: Literal["resolved", "ambiguous", "not_found", "invalid"]
    input: str
    normalized_tokens: list[str] = Field(default_factory=list)
    target_type: Optional[Literal["hack_day", "team_room"]] = None
    target_id: Optional[str] = None
    hack_day_id: Optional[str] = None
    participant_state: Optional[str] = None
    room_state: Optional[str] = None
    safe_summary: str
    next: str
    workspace_repo: Optional[WorkspaceRepoResolutionRecord] = None
    required_authorization: list[str] = Field(default_factory=list)
    matches: list[str] = Field(default_factory=list)


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
