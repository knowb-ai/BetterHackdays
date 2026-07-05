"""Stateful Socratic onboarding survey for BetterHackdays.

Drives the GitCommitted street survey as a stateful conversation: each
``POST /survey/answer`` advances one question and writes the answer into the
builder's profile via ``mcp_tools.update_profile``. State (current question
index) is persisted in SQLite and mirrored in memory as a small process-local
cache.

Because list fields (skills/interests/looking_for) are appended across
questions, each answer reads the current profile first and merges.
"""

from __future__ import annotations

from typing import Any, Optional

from . import matchmaking, mcp_tools
from .db import _loads, _row_to_dict, get_conn

# How many top match cards to attach when the survey completes.
MATCHES_ON_COMPLETE = 5

# Each question mirrors the street survey HTML.
QUESTIONS: list[dict[str, Any]] = [
    {
        "num": 1,
        "key": "screener",
        "text": "Do you write code, design products, or build things with tech (even as a hobby)?",
        "type": "single",
        "options": ["Yes, regularly", "Sometimes / learning", "No"],
    },
    {
        "num": 2,
        "key": "events",
        "text": "Have you ever gone to a hackathon, dev meetup, or builder event?",
        "type": "single",
        "options": [
            "Yes, in the last 6 months",
            "Yes, but not recently",
            "Never, but I would try",
            "Never, not interested",
        ],
    },
    {
        "num": 3,
        "key": "hardest",
        "text": "When you need a teammate or collaborator, what is hardest? (pick up to 2)",
        "type": "multi",
        "options": [
            "Finding someone with the right skills",
            "Finding someone who matches how I work (pace, tools, vibe)",
            "Breaking the ice / approaching strangers",
            "Trusting they will actually show up and contribute",
            "Not a problem for me",
        ],
    },
    {
        "num": 4,
        "key": "how",
        "text": "How do you usually find people to build with today?",
        "type": "multi",
        "options": [
            "Friends / existing network",
            "Discord / Slack / online communities",
            "LinkedIn or job boards",
            "Random pairing at the event",
            "I usually work alone",
        ],
    },
    {
        "num": 5,
        "key": "appeal",
        "text": "BetterHackdays matches you to builders with similar stack, goals, and vibe. How appealing, 1-5?",
        "type": "scale",
        "options": ["1", "2", "3", "4", "5"],
    },
    {
        "num": 6,
        "key": "where",
        "text": "Where would you actually use something like this?",
        "type": "multi",
        "options": [
            "Hackathons",
            "Business / startup networking events",
            "Coworking or office",
            "Casual vibecoding / AI building sessions",
            "Would not use it",
        ],
    },
    {
        "num": 7,
        "key": "trust",
        "text": "What would make you trust a match from an app?",
        "type": "open",
        "options": [],
    },
    {
        "num": 8,
        "key": "close",
        "text": "Would you try a 60-second profile if we sent you a link after the hackathon? (and what should we call you?)",
        "type": "single",
        "options": ["Yes", "Maybe later", "No thanks"],
    },
]

# Process-local cache: harness_id -> index of the NEXT question to answer.
_SESSIONS: dict[str, int] = {}


def _clamp_index(index: int) -> int:
    return max(0, min(index, len(QUESTIONS)))


def _get_session_index(harness_id: str) -> int:
    if harness_id in _SESSIONS:
        return _clamp_index(_SESSIONS[harness_id])

    with get_conn() as conn:
        row = conn.execute(
            "SELECT next_index FROM survey_sessions WHERE harness_id = ?",
            (harness_id,),
        ).fetchone()
    index = _clamp_index(row["next_index"]) if row else 0
    _SESSIONS[harness_id] = index
    return index


def _set_session_index(harness_id: str, index: int) -> int:
    index = _clamp_index(index)
    _SESSIONS[harness_id] = index
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO survey_sessions (harness_id, next_index)
            VALUES (?, ?)
            ON CONFLICT(harness_id) DO UPDATE SET
                next_index = excluded.next_index,
                updated_at = datetime('now')
            """,
            (harness_id, index),
        )
    return index


def _question_payload(index: int) -> Optional[dict[str, Any]]:
    if index >= len(QUESTIONS):
        return None
    q = QUESTIONS[index]
    return {
        "num": q["num"],
        "key": q["key"],
        "text": q["text"],
        "type": q["type"],
        "options": q["options"],
        "progress": f"{q['num']}/{len(QUESTIONS)}",
    }


def _current_profile(harness_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE harness_id = ?", (harness_id,)
        ).fetchone()
    if row is None:
        return {
            "skills": [],
            "interests": [],
            "looking_for": [],
            "preferred_role": None,
            "project_vibe": None,
            "availability": None,
            "display_label": "New builder",
        }
    data = _row_to_dict(row)
    return {
        "skills": _loads(data.get("skills")),
        "interests": _loads(data.get("interests")),
        "looking_for": _loads(data.get("looking_for")),
        "preferred_role": data.get("preferred_role"),
        "project_vibe": data.get("project_vibe"),
        "availability": data.get("availability"),
        "display_label": data.get("display_label") or "New builder",
    }


def _merge_unique(base: list[Any], extras: list[Any]) -> list[Any]:
    """Append items from `extras` to `base` without duplicates (case-insensitive)."""
    seen = {str(v).lower() for v in base}
    merged = list(base)
    for v in extras:
        if str(v).lower() not in seen:
            merged.append(v)
            seen.add(str(v).lower())
    return merged


def _map_answer(index: int, answer: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Translate a free-text answer into profile fields to upsert."""
    a = (answer or "").strip()
    low = a.lower()
    key = QUESTIONS[index]["key"]
    out: dict[str, Any] = {}

    if key == "screener":
        # Infer both a role and the concrete skills a builder offers, using the
        # same vocabulary seeded profiles put in `looking_for`. This is what
        # makes the skill-complement scorer fire and produce differentiated
        # match cards instead of a flat deck.
        existing_skills = list(profile.get("skills", []))
        if "design" in low:
            out["preferred_role"] = "design"
            out["skills"] = _merge_unique(existing_skills, ["design", "frontend"])
        elif any(w in low for w in ("code", "build", "dev", "engineer", "program")):
            out["preferred_role"] = "full-stack"
            out["skills"] = _merge_unique(existing_skills, ["frontend", "backend"])
        elif "no" in low:
            out["preferred_role"] = "new"
        else:
            out["preferred_role"] = "product"
            out["skills"] = _merge_unique(existing_skills, ["product", "frontend"])

    elif key == "events":
        if "6 months" in low or "recently" in low or "never, but" in low:
            out["availability"] = "full sprint"
        elif "not recent" in low or "yes, but" in low:
            out["availability"] = "weekend only"
        elif "not interested" in low:
            out["availability"] = "limited"

    elif key == "hardest":
        merged = list(profile["interests"])
        for opt in QUESTIONS[index]["options"]:
            if opt.lower() in low and opt not in merged:
                merged.append(opt)
        out["interests"] = merged

    elif key == "how":
        merged = list(profile["interests"])
        tag = "finds via network"
        if "discord" in low or "slack" in low:
            tag = "finds via discord/slack"
        elif "linkedin" in low or "job" in low:
            tag = "finds via linkedin"
        elif "random" in low or "pairing" in low:
            tag = "finds via random pairing"
        elif "alone" in low:
            tag = "works alone usually"
        if tag not in merged:
            merged.append(tag)
        out["interests"] = merged

    elif key == "appeal":
        if any(f" {n}" in f" {low}" for n in ("4", "5")) or low in ("4", "5"):
            out["project_vibe"] = "ship fast"
        elif low in ("3",) or " 3 " in f" {low} ":
            out["project_vibe"] = "balanced"
        else:
            out["project_vibe"] = "exploring"

    elif key == "where":
        merged = list(profile["interests"])
        for opt in ("hackathons", "networking", "coworking", "vibecoding"):
            if opt in low and opt not in merged:
                merged.append(opt)
        out["interests"] = merged

    elif key == "trust":
        merged = list(profile["looking_for"])
        # capture named qualities loosely
        for token in ("commits", "repo", "verified", "mutual", "vibe", "skills", "reviews", "references"):
            if token in low and token not in merged:
                merged.append(token)
        if a and a not in merged and not merged:
            merged.append(a[:40])
        out["looking_for"] = merged

    elif key == "close":
        # A name is often written in the answer; use it as display_label.
        # Skip common option lead-ins ("Yes", "No", "Maybe", ...) and tiny
        # filler words so we latch onto an actual name token instead of "Yes,".
        _SKIP = {
            "yes", "yea", "yeah", "yep", "sure", "ok", "okay", "no", "nope",
            "maybe", "not", "nah", "try", "call", "me", "i", "am", "i'm",
            "im", "name", "is", "this", "the", "a", "an", "my", "it's",
        }
        label = None
        for w in a.replace(",", " ").split():
            bare = w.strip("'\".")
            if not bare:
                continue
            if bare.lower() in _SKIP:
                continue
            if bare[0].isupper():
                label = bare
                break
        out["display_label"] = label or profile["display_label"]

    return out


def start_survey(harness_id: str) -> dict[str, Any]:
    """Begin the survey for a harness; ensure a profile exists, return Q1.

    This is what ``/connect`` calls so connecting kicks off the Socratic loop.
    """
    connect_result = mcp_tools.connect_harness(harness_id)
    _set_session_index(harness_id, 0)
    return {
        "status": "survey_started",
        "harness_id": harness_id,
        "profile": connect_result["profile"],
        "next": "survey",
        "question": _question_payload(0),
    }


def _top_matches(harness_id: str, limit: int = MATCHES_ON_COMPLETE) -> list[dict[str, Any]]:
    """Return up to `limit` best match cards for a harness, best first."""
    try:
        cards = matchmaking.get_match_cards(harness_id)
    except Exception:
        return []
    return cards[:limit]


def answer_survey(harness_id: str, answer: str) -> dict[str, Any]:
    """Record an answer, advance one question, return the next question."""
    index = _get_session_index(harness_id)
    if index >= len(QUESTIONS):
        return {
            "status": "completed",
            "harness_id": harness_id,
            "next_question": None,
            "done": True,
            "matches": _top_matches(harness_id),
        }

    profile = _current_profile(harness_id)
    updates = _map_answer(index, answer, profile)
    if updates:
        mcp_tools.update_profile(harness_id=harness_id, **updates)

    answered = QUESTIONS[index]
    _set_session_index(harness_id, index + 1)
    next_q = _question_payload(index + 1)

    # Screener decline -> end early. No matches: the profile is too bare to
    # score meaningfully, so we surface an empty list explicitly.
    if answered["key"] == "screener" and "no" in (answer or "").lower():
        _set_session_index(harness_id, len(QUESTIONS))
        return {
            "status": "ended",
            "answered": answered["num"],
            "saved": updates,
            "next_question": None,
            "done": True,
            "matches": [],
        }

    completed = next_q is None
    return {
        "status": "answered",
        "harness_id": harness_id,
        "answered": answered["num"],
        "saved": updates,
        "next_question": next_q,
        "done": completed,
        # Attach the best matches the moment the survey completes so the demo
        # flows straight from the last answer into the match deck.
        "matches": _top_matches(harness_id) if completed else [],
    }


def survey_state(harness_id: str) -> dict[str, Any]:
    """Return current survey progress for a harness without advancing."""
    index = _get_session_index(harness_id)
    return {
        "harness_id": harness_id,
        "progress": f"{index}/{len(QUESTIONS)}",
        "question": _question_payload(index),
        "done": index >= len(QUESTIONS),
    }
