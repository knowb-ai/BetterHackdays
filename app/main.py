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

from . import mcp_tools
from .db import init_db
from .models import (
    CardsResponse,
    ConnectRequest,
    ConnectResponse,
    HealthResponse,
    MatchRecord,
    MatchesResponse,
    Profile,
    SwipeRequest,
    SwipeResponse,
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
    result = mcp_tools.connect_harness(req.harness_id)
    return ConnectResponse(
        status=result["status"],
        profile=Profile(**result["profile"]),
        next=result["next"],
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


# --- matchmaking cards -------------------------------------------------------


@app.get("/matchmaking/cards", response_model=CardsResponse)
def matchmaking_cards(
    harness_id: str = Query(..., description="Harness requesting cards"),
) -> CardsResponse:
    result = mcp_tools.get_match_cards(harness_id)
    return CardsResponse(cards=result["cards"])


# --- like / pass -------------------------------------------------------------


@app.post("/matchmaking/like", response_model=SwipeResponse)
def like(req: SwipeRequest) -> SwipeResponse:
    if req.from_harness_id == req.to_harness_id:
        raise HTTPException(status_code=400, detail="A harness cannot like itself.")
    result = mcp_tools.like_profile(req.from_harness_id, req.to_harness_id)
    return SwipeResponse(**result)


@app.post("/matchmaking/pass", response_model=SwipeResponse)
def pass_profile(req: SwipeRequest) -> SwipeResponse:
    result = mcp_tools.pass_profile(req.from_harness_id, req.to_harness_id)
    return SwipeResponse(**result)


# --- matches -----------------------------------------------------------------


@app.get("/matches", response_model=MatchesResponse)
def matches(
    harness_id: str = Query(..., description="Harness requesting its matches"),
) -> MatchesResponse:
    result = mcp_tools.get_matches(harness_id)
    return MatchesResponse(matches=[MatchRecord(**m) for m in result["matches"]])
