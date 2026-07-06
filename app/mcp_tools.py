"""MCP-friendly function abstraction layer.

These plain Python functions are the single integration point for any MCP
server we build later. They always return plain dicts/lists (no Pydantic
models, no FastAPI objects) so they can be wrapped by any tool protocol.

The FastAPI routes in `app/main.py` call these same functions, so the REST
and MCP surfaces never drift.

A future work package can register these as actual MCP tools by adding an
`mcp.server.fastmcp.FastMCP` wrapper that points at these functions.
"""

from __future__ import annotations

from typing import Any, Optional

from . import event_ingest, matchmaking, planner, slug_resolution
from .db import _dumps, _loads, _row_to_dict, get_conn


class ProfileNotFoundError(ValueError):
    """Raised when an action requires an existing profile."""


def _profile_row_to_dict(row: Any) -> dict[str, Any]:
    data = _row_to_dict(row)
    data["skills"] = _loads(data.get("skills"))
    data["interests"] = _loads(data.get("interests"))
    data["looking_for"] = _loads(data.get("looking_for"))
    data["is_seeded"] = bool(data.get("is_seeded"))
    return data


def _require_profiles(*harness_ids: str) -> None:
    missing: list[str] = []
    with get_conn() as conn:
        for harness_id in harness_ids:
            row = conn.execute(
                "SELECT 1 FROM profiles WHERE harness_id = ?",
                (harness_id,),
            ).fetchone()
            if row is None:
                missing.append(harness_id)
    if missing:
        raise ProfileNotFoundError(
            "Unknown profile: " + ", ".join(sorted(set(missing)))
        )


def _get_or_create_profile(
    conn: Any,
    harness_id: str,
    create: bool = True,
) -> Optional[dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM profiles WHERE harness_id = ?",
        (harness_id,),
    ).fetchone()
    if row is not None:
        return _profile_row_to_dict(row)
    if not create:
        return None
    conn.execute(
        """
        INSERT INTO profiles (harness_id, display_label)
        VALUES (?, 'New builder')
        """,
        (harness_id,),
    )
    row = conn.execute(
        "SELECT * FROM profiles WHERE harness_id = ?",
        (harness_id,),
    ).fetchone()
    return _profile_row_to_dict(row)


def connect_harness(harness_id: str) -> dict[str, Any]:
    """Create or return the anonymous profile for a connecting harness.

    Returns a `next` action so the calling agent knows what to do first.
    """
    with get_conn() as conn:
        profile = _get_or_create_profile(conn, harness_id, create=True)
    assert profile is not None  # created above
    return {
        "status": "connected",
        "profile": profile,
        "next": "update_profile",
    }


def update_profile(
    harness_id: str,
    display_label: Optional[str] = None,
    skills: Optional[list[str]] = None,
    interests: Optional[list[str]] = None,
    preferred_role: Optional[str] = None,
    project_vibe: Optional[str] = None,
    looking_for: Optional[list[str]] = None,
    availability: Optional[str] = None,
) -> dict[str, Any]:
    """Upsert (create-then-update) the profile for a harness_id."""
    with get_conn() as conn:
        existing = _get_or_create_profile(conn, harness_id, create=True)
        assert existing is not None

        # Merge over existing values: any omitted field keeps its current value.
        merged = {
            "display_label": display_label or existing["display_label"],
            "skills": _dumps(skills if skills is not None else existing["skills"]),
            "interests": _dumps(
                interests if interests is not None else existing["interests"]
            ),
            "preferred_role": (
                preferred_role
                if preferred_role is not None
                else existing["preferred_role"]
            ),
            "project_vibe": (
                project_vibe
                if project_vibe is not None
                else existing["project_vibe"]
            ),
            "looking_for": _dumps(
                looking_for if looking_for is not None else existing["looking_for"]
            ),
            "availability": (
                availability if availability is not None else existing["availability"]
            ),
        }

        conn.execute(
            """
            UPDATE profiles SET
                display_label = ?,
                skills = ?,
                interests = ?,
                preferred_role = ?,
                project_vibe = ?,
                looking_for = ?,
                availability = ?,
                updated_at = datetime('now')
            WHERE harness_id = ?
            """,
            (
                merged["display_label"],
                merged["skills"],
                merged["interests"],
                merged["preferred_role"],
                merged["project_vibe"],
                merged["looking_for"],
                merged["availability"],
                harness_id,
            ),
        )
        profile = _profile_row_to_dict(
            conn.execute(
                "SELECT * FROM profiles WHERE harness_id = ?",
                (harness_id,),
            ).fetchone()
        )

    return {
        "status": "updated",
        "profile": profile,
        "next": "get_match_cards",
    }


def get_match_cards(harness_id: str) -> dict[str, Any]:
    """Return the scored, sorted, anonymized card deck for a harness."""
    return {"cards": matchmaking.get_match_cards(harness_id)}


def like_profile(from_harness_id: str, to_harness_id: str) -> dict[str, Any]:
    """Like a candidate and create a mutual match when reciprocated."""
    _require_profiles(from_harness_id, to_harness_id)
    return matchmaking.like_profile(from_harness_id, to_harness_id)


def pass_profile(from_harness_id: str, to_harness_id: str) -> dict[str, Any]:
    """Pass on a candidate. Passes never create matches."""
    _require_profiles(from_harness_id, to_harness_id)
    return matchmaking.pass_profile(from_harness_id, to_harness_id)


def get_matches(harness_id: str) -> dict[str, Any]:
    """Return all open matches involving a harness."""
    return {"matches": matchmaking.get_matches(harness_id)}


def ingest_event_text(
    text: str,
    source_label: str = "Pasted event text",
    source_url: str | None = None,
) -> dict[str, Any]:
    """Return normalized event context extracted from pasted event text."""
    return event_ingest.ingest_pasted_event_text(
        text,
        source_label=source_label,
        source_url=source_url,
    )


def rank_idea_suggestions(
    event: Any,
    profile: Any = None,
    team: Optional[list[Any]] = None,
    topics: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Return concise ranked hackathon ideas from event and team signals."""
    return planner.rank_idea_suggestions(
        event,
        profile=profile,
        team=team,
        topics=topics,
    )


def generate_process_timeline(
    event: Any,
    profile: Any = None,
    team: Optional[list[Any]] = None,
    hack_day: Any = None,
    team_room: Any = None,
    workspace_repo: Any = None,
) -> dict[str, Any]:
    """Return a concise deadline-aware Hack Day execution timeline."""
    return planner.generate_process_timeline(
        event,
        profile=profile,
        team=team,
        hack_day=hack_day,
        team_room=team_room,
        workspace_repo=workspace_repo,
    )


def generate_prep_checklist(
    event: Any,
    profile: Any = None,
    team: Optional[list[Any]] = None,
    hack_day: Any = None,
    team_room: Any = None,
    workspace_repo: Any = None,
) -> dict[str, Any]:
    """Return a concise actionable Hack Day prep checklist."""
    return planner.generate_prep_checklist(
        event,
        profile=profile,
        team=team,
        hack_day=hack_day,
        team_room=team_room,
        workspace_repo=workspace_repo,
    )


def resolve_slug(
    raw_input: str,
    hack_days: list[dict[str, Any]],
    standalone_slugs: Optional[list[dict[str, Any]]] = None,
    caller_participant_id: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve a Hack Day code, standalone slug, or namespaced room keyword."""
    return slug_resolution.resolve_slug(
        raw_input,
        hack_days=hack_days,
        standalone_slugs=standalone_slugs,
        caller_participant_id=caller_participant_id,
    )


# Registry for a future MCP server to enumerate and register these as tools.
MCP_TOOLS = {
    "connect_harness": connect_harness,
    "update_profile": update_profile,
    "get_match_cards": get_match_cards,
    "like_profile": like_profile,
    "pass_profile": pass_profile,
    "get_matches": get_matches,
    "ingest_event_text": ingest_event_text,
    "rank_idea_suggestions": rank_idea_suggestions,
    "generate_process_timeline": generate_process_timeline,
    "generate_prep_checklist": generate_prep_checklist,
    "resolve_slug": resolve_slug,
}
