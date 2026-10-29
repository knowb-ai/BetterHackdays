"""FastAPI application for the BetterHackdays matchmaking backend.

Routes here are thin: they validate input with Pydantic and delegate to the
MCP-friendly functions in `app.mcp_tools`, which in turn call the matchmaking
engine and SQLite layer. This keeps REST and MCP behavior identical.

Run locally:

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Open the interactive docs at http://localhost:8000/docs
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query

from . import mcp_tools, survey
from .db import init_db
from .models import (
    CardsResponse,
    CompareRfpsRequest,
    ConnectRequest,
    ConnectResponse,
    ContributorRequestListInput,
    ContributorRequestPreviewInput,
    ContributorRequestSubmitInput,
    DesignResourceReadRequest,
    EventIngestResponse,
    EventIngestTextRequest,
    HarnessId,
    HealthResponse,
    IdeaSuggestionsRequest,
    IdeaSuggestionsResponse,
    MatchCard,
    MatchRecord,
    MatchesResponse,
    Profile,
    PrepChecklistRequest,
    PrepChecklistResponse,
    ProcessTimelineRequest,
    ProcessTimelineResponse,
    ProposeIdeaCatalogueRequest,
    QualifyIdeaRequest,
    SlugResolveRequest,
    SlugResolveResponse,
    SwipeRequest,
    SwipeResponse,
    SurveyAnswerRequest,
    SurveyAnswerResponse,
    SurveyStateResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
)
from .seed import seed_profiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the DB and seed anonymous profiles on startup."""
    init_db()
    if os.getenv("SEED_PROFILES", "true").lower() in {"1", "true", "yes"}:
        seeded = seed_profiles(force=False)
        if seeded:
            app.state.logger.info(f"Seeded {seeded} anonymous builder profiles")
    yield


app = FastAPI(
    title=os.getenv("APP_NAME", "betterhackdays-matchmaking"),
    description=(
        "BetterHackdays harness matchmaking backend. Runs inside one long-lived "
        "Daytona Sandbox; all harnesses connect to the same shared service."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# FastAPI lazily attaches a logger; keep a convenience handle for startup logs.
import logging  # noqa: E402

app.state.logger = logging.getLogger("betterhackdays")
logging.basicConfig(level=logging.INFO)


# --- health ------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="betterhackdays-matchmaking",
        runtime="daytona-sandbox-ready",
    )


# --- connect -----------------------------------------------------------------


@app.post("/connect", response_model=ConnectResponse)
def connect(req: ConnectRequest) -> ConnectResponse:
    # /connect kicks off the stateful Socratic onboarding survey: it creates
    # the anonymous profile and returns the first question in one shot.
    result = survey.start_survey(req.harness_id)
    return ConnectResponse(
        status=result["status"],
        profile=Profile(**result["profile"]),
        next=result["next"],
        question=result.get("question"),
    )


# --- profile update ----------------------------------------------------------


@app.post("/profile/update", response_model=UpdateProfileResponse)
def update_profile(req: UpdateProfileRequest) -> UpdateProfileResponse:
    result = mcp_tools.update_profile(
        harness_id=req.harness_id,
        display_label=req.display_label,
        skills=req.skills,
        interests=req.interests,
        preferred_role=req.preferred_role,
        project_vibe=req.project_vibe,
        looking_for=req.looking_for,
        availability=req.availability,
    )
    return UpdateProfileResponse(
        status=result["status"],
        profile=Profile(**result["profile"]),
        next=result["next"],
    )


# --- event ingest ------------------------------------------------------------


@app.post("/event/ingest/text", response_model=EventIngestResponse)
def ingest_event_text(req: EventIngestTextRequest) -> EventIngestResponse:
    result = mcp_tools.ingest_event_text(
        text=req.text,
        source_label=req.source_label,
        source_url=req.source_url,
    )
    return EventIngestResponse(**result)


# --- planner ----------------------------------------------------------------


@app.post("/planner/ideas", response_model=IdeaSuggestionsResponse)
def planner_ideas(req: IdeaSuggestionsRequest) -> IdeaSuggestionsResponse:
    result = mcp_tools.rank_idea_suggestions(
        event=req.event.model_dump(),
        profile=req.profile.model_dump() if req.profile else None,
        team=[member.model_dump() for member in req.team],
        topics=req.topics,
    )
    return IdeaSuggestionsResponse(**result)


@app.post("/planner/timeline", response_model=ProcessTimelineResponse)
def planner_timeline(req: ProcessTimelineRequest) -> ProcessTimelineResponse:
    result = mcp_tools.generate_process_timeline(
        event=req.event.model_dump(),
        profile=req.profile.model_dump() if req.profile else None,
        team=[member.model_dump() for member in req.team],
        hack_day=req.hack_day.model_dump() if req.hack_day else None,
        team_room=req.team_room.model_dump() if req.team_room else None,
        workspace_repo=req.workspace_repo.model_dump() if req.workspace_repo else None,
    )
    return ProcessTimelineResponse(**result)


@app.post("/planner/checklist", response_model=PrepChecklistResponse)
def planner_checklist(req: PrepChecklistRequest) -> PrepChecklistResponse:
    result = mcp_tools.generate_prep_checklist(
        event=req.event.model_dump(),
        profile=req.profile.model_dump() if req.profile else None,
        team=[member.model_dump() for member in req.team],
        hack_day=req.hack_day.model_dump() if req.hack_day else None,
        team_room=req.team_room.model_dump() if req.team_room else None,
        workspace_repo=req.workspace_repo.model_dump() if req.workspace_repo else None,
    )
    return PrepChecklistResponse(**result)


# --- slug resolution ---------------------------------------------------------


@app.post("/slug/resolve", response_model=SlugResolveResponse)
def slug_resolve(req: SlugResolveRequest) -> SlugResolveResponse:
    result = mcp_tools.resolve_slug(
        raw_input=req.raw_input,
        hack_days=[hack_day.model_dump() for hack_day in req.hack_days],
        standalone_slugs=[slug.model_dump() for slug in req.standalone_slugs],
        caller_participant_id=req.caller_participant_id,
    )
    return SlugResolveResponse(**result)


# --- matchmaking cards -------------------------------------------------------


@app.get("/matchmaking/cards", response_model=CardsResponse)
def matchmaking_cards(
    harness_id: HarnessId = Query(..., description="Harness requesting cards"),
) -> CardsResponse:
    result = mcp_tools.get_match_cards(harness_id)
    return CardsResponse(cards=result["cards"])


# --- like / pass -------------------------------------------------------------


@app.post("/matchmaking/like", response_model=SwipeResponse)
def like(req: SwipeRequest) -> SwipeResponse:
    if req.from_harness_id == req.to_harness_id:
        raise HTTPException(status_code=400, detail="A harness cannot like itself.")
    try:
        result = mcp_tools.like_profile(req.from_harness_id, req.to_harness_id)
    except mcp_tools.ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SwipeResponse(**result)


@app.post("/matchmaking/pass", response_model=SwipeResponse)
def pass_profile(req: SwipeRequest) -> SwipeResponse:
    try:
        result = mcp_tools.pass_profile(req.from_harness_id, req.to_harness_id)
    except mcp_tools.ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SwipeResponse(**result)


# --- matches -----------------------------------------------------------------


@app.get("/matches", response_model=MatchesResponse)
def matches(
    harness_id: HarnessId = Query(..., description="Harness requesting its matches"),
) -> MatchesResponse:
    result = mcp_tools.get_matches(harness_id)
    return MatchesResponse(matches=[MatchRecord(**m) for m in result["matches"]])


# --- survey onboarding --------------------------------------------------------


@app.post("/survey/start", response_model=ConnectResponse)
def survey_start(req: ConnectRequest) -> ConnectResponse:
    """(Re)start the onboarding survey for a harness, returning question 1."""
    result = survey.start_survey(req.harness_id)
    return ConnectResponse(
        status=result["status"],
        profile=Profile(**result["profile"]),
        next=result["next"],
        question=result.get("question"),
    )


@app.post("/survey/answer", response_model=SurveyAnswerResponse)
def survey_answer(req: SurveyAnswerRequest) -> SurveyAnswerResponse:
    result = survey.answer_survey(req.harness_id, req.answer)
    return SurveyAnswerResponse(
        status=result["status"],
        harness_id=result.get("harness_id"),
        answered=result.get("answered"),
        saved=result.get("saved", {}),
        next_question=result.get("next_question"),
        done=result.get("done", False),
        matches=[MatchCard(**m) for m in result.get("matches", [])],
    )


@app.get("/survey/state", response_model=SurveyStateResponse)
def survey_state(
    harness_id: HarnessId = Query(
        ...,
        description="Harness checking its survey progress",
    ),
) -> SurveyStateResponse:
    result = survey.survey_state(harness_id)
    return SurveyStateResponse(
        harness_id=result["harness_id"],
        progress=result["progress"],
        question=result.get("question"),
        done=result["done"],
    )


# --- KnowB RFP, design resources, idea catalogue, and contributor connector --


@app.get("/rfps")
def rfps_list(
    visibility: str | None = Query(
        default=None,
        description="Optional visibility filter (e.g. public_website or connector_only)",
    ),
) -> dict:
    return mcp_tools.list_project_rfps(visibility=visibility)


@app.get("/rfps/search")
def rfps_search(
    q: str = Query(..., description="Search query across approved RFPs"),
    include_design_resources: bool = Query(default=False),
) -> dict:
    return mcp_tools.search_project_rfps(
        query=q,
        include_design_resources=include_design_resources,
    )


@app.post("/rfps/compare")
def rfps_compare(req: CompareRfpsRequest) -> dict:
    return mcp_tools.compare_project_rfps(rfp_ids=req.rfp_ids)


@app.get("/rfps/{rfp_id}")
def rfps_read(rfp_id: str) -> dict:
    return mcp_tools.read_project_rfp(rfp_id=rfp_id)


@app.get("/design-resources")
def design_resources_list() -> dict:
    return mcp_tools.list_design_resources()


@app.get("/design-resources/search")
def design_resources_search(
    q: str = Query(..., description="Search query across allowlisted design resources"),
) -> dict:
    return mcp_tools.search_design_resources(query=q)


@app.post("/design-resources/read")
def design_resources_read(req: DesignResourceReadRequest) -> dict:
    return mcp_tools.read_design_resource(path=req.path, repo=req.repo)


@app.get("/ideas/catalogue")
def ideas_catalogue(
    q: str | None = Query(default=None),
    section: str | None = Query(default=None),
    limit: int | None = Query(default=None),
) -> dict:
    return mcp_tools.fetch_idea_catalogue(query=q, section=section, limit=limit)


@app.post("/ideas/qualify")
def ideas_qualify(req: QualifyIdeaRequest) -> dict:
    return mcp_tools.qualify_idea(
        title=req.title,
        summary=req.summary,
        alignment_evidence=req.alignment_evidence,
        human_reviewed_rationale=req.human_reviewed_rationale,
        reviewed_by=req.reviewed_by,
    )


@app.post("/ideas/propose")
def ideas_propose(req: ProposeIdeaCatalogueRequest) -> dict:
    return mcp_tools.propose_idea_catalogue_addition(
        title=req.title,
        summary=req.summary,
        alignment_evidence=req.alignment_evidence,
        human_reviewed_rationale=req.human_reviewed_rationale,
        reviewed_by=req.reviewed_by,
        section=req.section,
        submit=req.submit,
        auth_context=req.auth_context,
    )


@app.post("/contributor/requests/preview")
def contributor_request_preview(req: ContributorRequestPreviewInput) -> dict:
    return mcp_tools.preview_contributor_request(
        request_type=req.request_type,
        rfp_id=req.rfp_id,
        requested_scope=req.requested_scope,
        message=req.message,
    )


@app.post("/contributor/requests/submit")
def contributor_request_submit(req: ContributorRequestSubmitInput) -> dict:
    return mcp_tools.submit_contributor_request(
        request_type=req.request_type,
        rfp_id=req.rfp_id,
        requested_scope=req.requested_scope,
        message=req.message,
        target_repo=req.target_repo,
        caller_supplied_login=req.caller_supplied_login,
        asserted_role=req.asserted_role,
        auth_context=req.auth_context,
    )


@app.post("/contributor/requests/list")
def contributor_request_list(req: ContributorRequestListInput) -> dict:
    return mcp_tools.list_contributor_requests(auth_context=req.auth_context)

