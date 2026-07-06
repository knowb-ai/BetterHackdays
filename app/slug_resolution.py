"""Slug and room keyword resolution for Hack Day entry points."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional


def _normalize_tokens(value: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    return [token for token in normalized.split(" ") if token]


def _is_expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        normalized = expires_at.replace("Z", "+00:00")
        expires = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires < datetime.now(timezone.utc)


def _hack_day_code(hack_day: dict[str, Any]) -> str:
    return str(hack_day.get("code", "")).strip().lower()


def _room_keyword(room: dict[str, Any]) -> str:
    return str(room.get("keyword", "")).strip().lower()


def _room_state(room: dict[str, Any]) -> str:
    if room.get("workspace_repo"):
        return "workspace_connected"
    return str(room.get("state") or "room_created")


def _participant_state(
    hack_day: dict[str, Any],
    caller_participant_id: Optional[str],
) -> Optional[str]:
    if not caller_participant_id:
        return None
    for participant in hack_day.get("participant_states", []):
        if participant.get("participant_id") == caller_participant_id:
            return participant.get("state")
    return None


def _is_room_authorized(
    room: dict[str, Any],
    caller_participant_id: Optional[str],
) -> bool:
    if not caller_participant_id:
        return False
    return caller_participant_id in set(room.get("participant_ids", []))


def _safe_workspace_repo(
    room: dict[str, Any],
    caller_participant_id: Optional[str],
) -> Optional[dict[str, Any]]:
    repo = room.get("workspace_repo")
    if not repo or not _is_room_authorized(room, caller_participant_id):
        return None
    return {
        "owner": repo.get("owner"),
        "repo": repo.get("repo"),
        "default_branch": repo.get("default_branch", "main"),
        "permission_status": repo.get("permission_status"),
        "allowed_write_targets": repo.get("allowed_write_targets", []),
        "last_synced_planning_snapshot": repo.get("last_synced_planning_snapshot"),
    }


def _resolve_hack_day(
    hack_day: dict[str, Any],
    tokens: list[str],
    caller_participant_id: Optional[str],
) -> dict[str, Any]:
    state = _participant_state(hack_day, caller_participant_id)
    next_action = "join_hack_day" if state is None else "continue_hack_day"
    if state == "active":
        next_action = "complete_profile"
    elif state == "matchable":
        next_action = "view_matchmaking"
    elif state in {"matched", "room_created", "workspace_connected"}:
        next_action = "open_team_room"
    return {
        "status": "resolved",
        "input": " ".join(tokens),
        "normalized_tokens": tokens,
        "target_type": "hack_day",
        "target_id": hack_day.get("hack_day_id"),
        "hack_day_id": hack_day.get("hack_day_id"),
        "participant_state": state,
        "room_state": None,
        "safe_summary": f"Hack Day: {hack_day.get('name') or hack_day.get('code')}",
        "next": next_action,
        "workspace_repo": None,
        "required_authorization": [],
    }


def _resolve_room(
    hack_day: dict[str, Any],
    room: dict[str, Any],
    tokens: list[str],
    caller_participant_id: Optional[str],
) -> dict[str, Any]:
    authorized = _is_room_authorized(room, caller_participant_id)
    join_mode = room.get("join_mode", "open")
    required_authorization: list[str] = []
    if join_mode == "approval":
        required_authorization.append("room_approval")
    elif join_mode == "invite_only" and not authorized:
        required_authorization.append("team_room_invite")
    state = _room_state(room)
    workspace_repo = _safe_workspace_repo(room, caller_participant_id)
    next_action = "open_team_room" if authorized else "request_room_access"
    if join_mode == "open" and not authorized:
        next_action = "join_team_room"
    if state == "workspace_connected" and authorized:
        next_action = "open_workspace_repo"
    return {
        "status": "resolved",
        "input": " ".join(tokens),
        "normalized_tokens": tokens,
        "target_type": "team_room",
        "target_id": room.get("room_id"),
        "hack_day_id": hack_day.get("hack_day_id"),
        "participant_state": _participant_state(hack_day, caller_participant_id),
        "room_state": state,
        "safe_summary": f"Team room: {room.get('keyword')}",
        "next": next_action,
        "workspace_repo": workspace_repo,
        "required_authorization": required_authorization,
    }


def _ambiguous(tokens: list[str], matches: list[str]) -> dict[str, Any]:
    return {
        "status": "ambiguous",
        "input": " ".join(tokens),
        "normalized_tokens": tokens,
        "target_type": None,
        "target_id": None,
        "hack_day_id": None,
        "participant_state": None,
        "room_state": None,
        "safe_summary": "Multiple slug targets matched.",
        "next": "ask_for_more_context",
        "workspace_repo": None,
        "required_authorization": [],
        "matches": matches,
    }


def _not_found(tokens: list[str]) -> dict[str, Any]:
    return {
        "status": "not_found",
        "input": " ".join(tokens),
        "normalized_tokens": tokens,
        "target_type": None,
        "target_id": None,
        "hack_day_id": None,
        "participant_state": None,
        "room_state": None,
        "safe_summary": "No active Hack Day, standalone slug, room, or team keyword matched.",
        "next": "check_code_or_create_hack_day",
        "workspace_repo": None,
        "required_authorization": [],
    }


def resolve_slug(
    raw_input: str,
    hack_days: list[dict[str, Any]],
    standalone_slugs: Optional[list[dict[str, Any]]] = None,
    caller_participant_id: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve Hack Day codes, standalone slugs, and namespaced room keywords."""
    tokens = _normalize_tokens(raw_input)
    standalone_slugs = standalone_slugs or []
    active_hack_days = [
        hack_day
        for hack_day in hack_days
        if hack_day.get("status", "active") != "ended"
        and not _is_expired(hack_day.get("expires_at"))
    ]

    if len(tokens) == 1:
        token = tokens[0]
        hack_day_matches = [
            hack_day for hack_day in active_hack_days if _hack_day_code(hack_day) == token
        ]
        if len(hack_day_matches) == 1:
            return _resolve_hack_day(hack_day_matches[0], tokens, caller_participant_id)
        if len(hack_day_matches) > 1:
            return _ambiguous(tokens, [str(match.get("hack_day_id")) for match in hack_day_matches])

        slug_matches = [
            slug
            for slug in standalone_slugs
            if str(slug.get("slug", "")).strip().lower() == token
            and not _is_expired(slug.get("expires_at"))
        ]
        if len(slug_matches) > 1:
            return _ambiguous(tokens, [str(match.get("target_id")) for match in slug_matches])
        if len(slug_matches) == 1:
            slug = slug_matches[0]
            target_type = slug.get("target_type")
            target_id = slug.get("target_id")
            if target_type == "hack_day":
                matches = [
                    hack_day
                    for hack_day in active_hack_days
                    if hack_day.get("hack_day_id") == target_id
                ]
                if matches:
                    return _resolve_hack_day(matches[0], tokens, caller_participant_id)
            if target_type == "team_room":
                for hack_day in active_hack_days:
                    for room in hack_day.get("team_rooms", []):
                        if room.get("room_id") == target_id:
                            return _resolve_room(
                                hack_day,
                                room,
                                tokens,
                                caller_participant_id,
                            )
        return _not_found(tokens)

    if len(tokens) == 2:
        hack_day_token, keyword = tokens
        hack_day_matches = [
            hack_day
            for hack_day in active_hack_days
            if _hack_day_code(hack_day) == hack_day_token
        ]
        if len(hack_day_matches) != 1:
            if len(hack_day_matches) > 1:
                return _ambiguous(
                    tokens,
                    [str(match.get("hack_day_id")) for match in hack_day_matches],
                )
            return _not_found(tokens)
        hack_day = hack_day_matches[0]
        room_matches = [
            room
            for room in hack_day.get("team_rooms", [])
            if _room_keyword(room) == keyword
        ]
        if len(room_matches) == 1:
            return _resolve_room(hack_day, room_matches[0], tokens, caller_participant_id)
        if len(room_matches) > 1:
            return _ambiguous(tokens, [str(match.get("room_id")) for match in room_matches])
        return _not_found(tokens)

    return {
        "status": "invalid",
        "input": " ".join(tokens),
        "normalized_tokens": tokens,
        "target_type": None,
        "target_id": None,
        "hack_day_id": None,
        "participant_state": None,
        "room_state": None,
        "safe_summary": "Use a Hack Day code, standalone slug, or Hack Day code plus room keyword.",
        "next": "enter_supported_slug_format",
        "workspace_repo": None,
        "required_authorization": [],
    }
