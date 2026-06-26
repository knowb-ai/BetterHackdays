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

from . import matchmaking
from .db import _dumps, _loads, _row_to_dict, get_conn


def _profile_row_to_dict(row: Any) -> dict[str, Any]:
    data = _row_to_dict(row)
    data["skills"] = _loads(data.get("skills"))
    data["interests"] = _loads(data.get("interests"))
    data["looking_for"] = _loads(data.get("looking_for"))
    data["is_seeded"] = bool(data.get("is_seeded"))
    return data


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
    return matchmaking.like_profile(from_harness_id, to_harness_id)


def pass_profile(from_harness_id: str, to_harness_id: str) -> dict[str, Any]:
    """Pass on a candidate. Passes never create matches."""
    return matchmaking.pass_profile(from_harness_id, to_harness_id)


def get_matches(harness_id: str) -> dict[str, Any]:
    """Return all open matches involving a harness."""
    return {"matches": matchmaking.get_matches(harness_id)}


# Registry for a future MCP server to enumerate and register these as tools.
MCP_TOOLS = {
    "connect_harness": connect_harness,
    "update_profile": update_profile,
    "get_match_cards": get_match_cards,
    "like_profile": like_profile,
    "pass_profile": pass_profile,
    "get_matches": get_matches,
}
