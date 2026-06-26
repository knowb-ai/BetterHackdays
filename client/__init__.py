"""Terminal-side MCP client for BetterHackdays.

This package runs on the harness/terminal side (e.g. in Warp, Claude Code,
Cursor). It derives an anonymous, stable ``harness_id`` from the local Git
email and forwards calls to the shared BetterHackdays backend running inside a
Daytona Sandbox.

No login, no API keys, no real identity is ever sent. The Git email is hashed
so two teammates on different machines collide only if they share the exact
same Git ``user.email``.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from typing import Optional

try:
    import urllib.request
    import json as _json

    _HAS_STDlib = True
except Exception:  # pragma: no cover - stdlib always present
    _HAS_STDlib = False

__all__ = [
    "BACKEND_URL_ENV",
    "IDENTITY_ENV",
    "derive_harness_id",
    "get_harness_id",
    "connect",
    "update_profile",
    "get_match_cards",
    "like_profile",
    "pass_profile",
    "get_matches",
]

BACKEND_URL_ENV = "BETTERHACKDAYS_BACKEND_URL"
IDENTITY_ENV = "BETTERHACKDAYS_HARNESS_ID"


def _git_email() -> Optional[str]:
    """Return the configured local/global Git user.email, or None."""
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "user.email"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def derive_harness_id(email: Optional[str] = None, salt: str = "betterhackdays") -> str:
    """Derive an anonymous, stable harness_id from a Git email.

    The email is SHA-256 hashed with a salt so the backend never sees the
    raw address. Same email on the same machine yields the same harness_id
    across sessions.
    """
    email = email or _git_email() or "anonymous@local"
    digest = hashlib.sha256(f"{salt}:{email}".encode("utf-8")).hexdigest()
    # Short, stable, readable prefix so cards/matches stay legible.
    return f"harness_{digest[:12]}"


def get_harness_id() -> str:
    """Return the harness_id to use.

    Priority:
      1. ``$BETTERHACKDAYS_HARNESS_ID`` (explicit override)
      2. Derived from local Git ``user.email``
    """
    explicit = os.getenv(IDENTITY_ENV)
    if explicit:
        return explicit
    return derive_harness_id()


def _backend_url() -> str:
    url = os.getenv(BACKEND_URL_ENV)
    if not url:
        raise RuntimeError(
            f"Set ${BACKEND_URL_ENV} to the BetterHackdays backend URL "
            "(the Daytona preview URL)."
        )
    return url.rstrip("/")


def _request(verb: str, path: str, body: Optional[dict] = None) -> dict:
    """Minimal stdlib HTTP client. Keeps the terminal client dependency-free."""
    if not _HAS_STDlib:  # pragma: no cover
        raise RuntimeError("stdlib urllib not available")
    url = f"{_backend_url()}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = _json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=verb)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        return _json.loads(raw) if raw else {}


# --- MCP-friendly tool functions ---------------------------------------------
# These are the same names the backend's mcp_tools.py exposes, but here they
# run terminal-side, deriving identity automatically and calling the backend.


def connect(harness_id: Optional[str] = None) -> dict:
    """Connect this harness to the shared backend.

    If ``harness_id`` is omitted it is derived from the local Git email, so a
    terminal can call this with no arguments. Sends only the anonymous hashed
    id — never the raw email.
    """
    hid = harness_id or get_harness_id()
    return _request("POST", "/connect", {"harness_id": hid})


def update_profile(
    *,
    harness_id: Optional[str] = None,
    display_label: Optional[str] = None,
    skills: Optional[list[str]] = None,
    interests: Optional[list[str]] = None,
    preferred_role: Optional[str] = None,
    project_vibe: Optional[str] = None,
    looking_for: Optional[list[str]] = None,
    availability: Optional[str] = None,
) -> dict:
    """Update (or create) the anonymous profile for this harness."""
    hid = harness_id or get_harness_id()
    body: dict = {"harness_id": hid}
    for k, v in (
        ("display_label", display_label),
        ("skills", skills),
        ("interests", interests),
        ("preferred_role", preferred_role),
        ("project_vibe", project_vibe),
        ("looking_for", looking_for),
        ("availability", availability),
    ):
        if v is not None:
            body[k] = v
    return _request("POST", "/profile/update", body)


def get_match_cards(harness_id: Optional[str] = None) -> dict:
    """Fetch scored, anonymized match cards for this harness."""
    hid = harness_id or get_harness_id()
    return _request("GET", f"/matchmaking/cards?harness_id={hid}")


def like_profile(to_harness_id: str, harness_id: Optional[str] = None) -> dict:
    """Like a candidate. Mutual likes create a match."""
    hid = harness_id or get_harness_id()
    return _request(
        "POST",
        "/matchmaking/like",
        {"from_harness_id": hid, "to_harness_id": to_harness_id},
    )


def pass_profile(to_harness_id: str, harness_id: Optional[str] = None) -> dict:
    """Pass on a candidate."""
    hid = harness_id or get_harness_id()
    return _request(
        "POST",
        "/matchmaking/pass",
        {"from_harness_id": hid, "to_harness_id": to_harness_id},
    )


def get_matches(harness_id: Optional[str] = None) -> dict:
    """Return all open matches involving this harness."""
    hid = harness_id or get_harness_id()
    return _request("GET", f"/matches?harness_id={hid}")
