"""Deterministic hackathon prep planning helpers.

The M3 planner starts with idea ranking. It intentionally avoids LLM calls so
the first planner surface is fast, explainable, and easy to test.
"""

from __future__ import annotations

import re
from typing import Any


IDEA_TYPES = ("safe_default", "ambitious", "niche", "fast_fallback")

SKILL_ALIASES = {
    "frontend": ("ui", "ux", "demo", "interface", "web"),
    "react": ("ui", "ux", "demo", "interface", "web"),
    "design": ("ux", "story", "demo", "interface"),
    "backend": ("api", "data", "workflow", "reliability"),
    "fastapi": ("api", "backend", "python", "workflow"),
    "python": ("api", "data", "automation", "prototype"),
    "ai": ("agent", "assistant", "model", "automation"),
    "agents": ("agent", "assistant", "workflow", "automation"),
    "llm": ("agent", "assistant", "model", "automation"),
    "data": ("analytics", "insight", "dashboard", "scoring"),
}


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return list(value)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _lower_set(values: list[Any]) -> set[str]:
    out: set[str] = set()
    for value in values:
        text = _clean(value).lower()
        if text:
            out.add(text)
    return out


def _event_terms(event: dict[str, Any]) -> dict[str, list[str]]:
    tracks = [_clean(track) for track in _as_list(event.get("tracks")) if _clean(track)]
    criteria = [
        _clean(item.get("name") or item.get("description"))
        for item in _as_list(event.get("judging_criteria"))
        if isinstance(item, dict) and _clean(item.get("name") or item.get("description"))
    ]
    tools = [
        _clean(tool)
        for tool in _as_list(event.get("allowed_tools"))
        + _as_list(event.get("recommended_tools"))
        if _clean(tool)
    ]
    return {"tracks": tracks, "criteria": criteria, "tools": tools}


def _profile_terms(
    profile: dict[str, Any],
    team: list[dict[str, Any]],
) -> dict[str, list[str]]:
    skills: list[str] = []
    interests: list[str] = []
    roles: list[str] = []

    for person in [profile, *team]:
        if not person:
            continue
        skills.extend(_clean(skill) for skill in _as_list(person.get("skills")))
        interests.extend(_clean(interest) for interest in _as_list(person.get("interests")))
        if person.get("preferred_role"):
            roles.append(_clean(person["preferred_role"]))

    return {
        "skills": sorted(_lower_set(skills)),
        "interests": sorted(_lower_set(interests)),
        "roles": sorted(_lower_set(roles)),
    }


def _primary(values: list[str], fallback: str) -> str:
    return values[0] if values else fallback


def _expanded_skill_terms(skills: list[str]) -> set[str]:
    terms = set(skills)
    for skill in skills:
        for alias, mapped in SKILL_ALIASES.items():
            if alias in skill:
                terms.update(mapped)
    return terms


def _score_candidate(
    candidate: dict[str, Any],
    *,
    event_terms: dict[str, list[str]],
    profile_terms: dict[str, list[str]],
    topics: list[str],
) -> dict[str, Any]:
    score = candidate["base_score"]
    signals: list[str] = []
    searchable = " ".join(
        [
            candidate["summary"],
            candidate["why_it_fits"],
            candidate["main_tradeoff"],
            *candidate["tags"],
        ]
    ).lower()

    tracks = event_terms["tracks"]
    if tracks:
        primary_track = tracks[0]
        score += 14
        signals.append(f"Track fit: {primary_track}")

    criteria = event_terms["criteria"]
    if criteria:
        criterion = criteria[0]
        score += 10
        signals.append(f"Judging fit: {criterion}")

    if topics:
        topic = topics[0]
        score += 8
        signals.append(f"Topic fit: {topic}")

    skill_terms = _expanded_skill_terms(profile_terms["skills"])
    matched_skills = [
        skill for skill in profile_terms["skills"]
        if skill in searchable or any(term in searchable for term in SKILL_ALIASES.get(skill, ()))
    ]
    if not matched_skills and skill_terms.intersection(set(candidate["tags"])):
        matched_skills = [next(iter(skill_terms.intersection(set(candidate["tags"]))))]
    if matched_skills:
        score += min(14, 6 + len(matched_skills) * 3)
        signals.append("Skill fit: " + ", ".join(matched_skills[:3]))

    if candidate["idea_type"] == "fast_fallback":
        score += 8
        signals.append("Demo speed: smallest useful build")
    elif candidate["idea_type"] == "safe_default":
        score += 6
        signals.append("Feasibility: balanced scope")
    elif candidate["idea_type"] == "ambitious":
        score += 7
        signals.append("Novelty: higher ceiling with higher risk")
    elif candidate["idea_type"] == "niche":
        score += 5
        signals.append("Differentiation: focused wedge")

    ranked = {
        key: candidate[key]
        for key in ("idea_type", "summary", "why_it_fits", "main_tradeoff")
    }
    ranked["score"] = min(score, 100)
    ranked["signals"] = signals or ["Fallback: limited event or team context"]
    return ranked


def _candidate_ideas(
    event_terms: dict[str, list[str]],
    profile_terms: dict[str, list[str]],
    topics: list[str],
) -> list[dict[str, Any]]:
    track = _primary(event_terms["tracks"], "the event theme")
    criterion = _primary(event_terms["criteria"], "demo clarity")
    topic = _primary(topics, _primary(profile_terms["interests"], track))
    skill = _primary(profile_terms["skills"], "the team's strongest stack")

    return [
        {
            "idea_type": "safe_default",
            "summary": f"{track} command center for teams to make faster decisions",
            "why_it_fits": (
                f"Maps directly to {track} and can show {criterion} in one clear demo."
            ),
            "main_tradeoff": "Less surprising, but easiest to scope and explain.",
            "base_score": 54,
            "tags": ["dashboard", "workflow", "demo", "ui", "api", "prototype"],
        },
        {
            "idea_type": "ambitious",
            "summary": f"Agentic copilot that turns {track} signals into next actions",
            "why_it_fits": (
                f"Creates a memorable demo if {skill} can support the core workflow quickly."
            ),
            "main_tradeoff": "Higher upside, but integration risk can eat the sprint.",
            "base_score": 49,
            "tags": ["agent", "assistant", "automation", "workflow", "model", "api"],
        },
        {
            "idea_type": "niche",
            "summary": f"{topic} specialist tool for one overlooked hackathon user",
            "why_it_fits": (
                "A narrow wedge can feel more original than a broad platform pitch."
            ),
            "main_tradeoff": "Needs a crisp user story or it may feel too small.",
            "base_score": 47,
            "tags": ["story", "ux", "insight", "focused", "dashboard"],
        },
        {
            "idea_type": "fast_fallback",
            "summary": f"Submission-ready {track} microtool with a polished demo path",
            "why_it_fits": (
                "Keeps scope tiny while still proving the core event-relevant behavior."
            ),
            "main_tradeoff": "Safer finish, but lower novelty unless the demo is sharp.",
            "base_score": 52,
            "tags": ["demo", "prototype", "ui", "api", "submission", "fast"],
        },
    ]


def rank_idea_suggestions(
    event: Any,
    *,
    profile: Any = None,
    team: list[Any] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Rank concise hackathon idea directions by event and team fit."""
    event_dict = _as_dict(event)
    profile_dict = _as_dict(profile)
    team_dicts = [_as_dict(member) for member in _as_list(team)]
    clean_topics = [_clean(topic) for topic in _as_list(topics) if _clean(topic)]

    event_signal_terms = _event_terms(event_dict)
    profile_signal_terms = _profile_terms(profile_dict, team_dicts)
    candidates = _candidate_ideas(
        event_signal_terms,
        profile_signal_terms,
        clean_topics,
    )
    ideas = [
        _score_candidate(
            candidate,
            event_terms=event_signal_terms,
            profile_terms=profile_signal_terms,
            topics=clean_topics,
        )
        for candidate in candidates
    ]
    ideas.sort(key=lambda idea: idea["score"], reverse=True)

    ranking_signals = []
    if event_signal_terms["tracks"]:
        ranking_signals.append("event_tracks")
    if event_signal_terms["criteria"]:
        ranking_signals.append("judging_criteria")
    if profile_signal_terms["skills"]:
        ranking_signals.append("profile_or_team_skills")
    if clean_topics:
        ranking_signals.append("chosen_topics")
    if not ranking_signals:
        ranking_signals.append("fallback_defaults")

    return {
        "status": "ranked",
        "ideas": ideas,
        "ranking_signals": ranking_signals,
        "next": "review_ideas",
    }
