"""Deterministic hackathon prep planning helpers.

The M3 planner starts with idea ranking. It intentionally avoids LLM calls so
the first planner surface is fast, explainable, and easy to test.
"""

from __future__ import annotations

import re
from typing import Any


IDEA_TYPES = ("safe_default", "ambitious", "niche", "fast_fallback")

TIMELINE_STAGES = (
    "before_event",
    "first_30_minutes",
    "first_2_hours",
    "validation",
    "demo_prep",
    "final_submission",
)

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
    if value is None:
        return ""
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


def _deadline_lines(event: dict[str, Any]) -> list[dict[str, Any]]:
    deadlines: list[dict[str, Any]] = []
    for item in _as_list(event.get("deadlines")):
        if not isinstance(item, dict):
            continue
        name = _clean(item.get("name") or "Deadline")
        due_at = _clean(item.get("due_at"))
        description = _clean(item.get("description"))
        deadlines.append({
            "name": name,
            "due_at": due_at or None,
            "description": description or None,
        })
    submission = event.get("submission")
    if isinstance(submission, dict) and submission.get("requirements") and not deadlines:
        deadlines.append({
            "name": "Final submission",
            "due_at": None,
            "description": "Submission requirements are known, but deadline is missing.",
        })
    return deadlines


def _final_deadline(deadlines: list[dict[str, Any]]) -> dict[str, Any] | None:
    for deadline in deadlines:
        searchable = " ".join([
            _clean(deadline.get("name")),
            _clean(deadline.get("description")),
        ]).lower()
        if any(token in searchable for token in ("final", "submission", "submit")):
            return deadline
    return deadlines[-1] if deadlines else None


def _hack_day_state(
    hack_day: dict[str, Any],
    team_room: dict[str, Any],
    workspace_repo: dict[str, Any],
) -> str:
    if workspace_repo:
        return "workspace_connected"
    if team_room:
        return "team_room"
    state = _clean(hack_day.get("participant_state") or hack_day.get("state")).lower()
    if state in {"active", "matchable", "matched"}:
        return state
    return "event_only"


def _workspace_tasks(workspace_repo: dict[str, Any]) -> list[str]:
    if not workspace_repo:
        return ["Keep repo setup as a permissioned next step after the team agrees."]
    repo_name = _clean(workspace_repo.get("repo")) or _clean(workspace_repo.get("name"))
    repo_owner = _clean(workspace_repo.get("owner"))
    label = f"{repo_owner}/{repo_name}" if repo_owner and repo_name else "the connected repo"
    return [
        f"Use {label} as the shared source of truth.",
        "Keep docs/process-plan.md and docs/checklist.md current as decisions change.",
    ]


def _stage_templates(
    *,
    event: dict[str, Any],
    deadlines: list[dict[str, Any]],
    hack_day_state: str,
    workspace_repo: dict[str, Any],
) -> list[dict[str, Any]]:
    event_name = _clean(event.get("event_name")) or "the Hack Day"
    starts_at = _clean(event.get("starts_at"))
    ends_at = _clean(event.get("ends_at"))
    final_deadline = _final_deadline(deadlines)
    final_due = final_deadline.get("due_at") if final_deadline else None

    before_tasks = [
        f"Review {event_name} rules, tracks, judging criteria, and submission needs.",
        "Confirm whether you are active, matchable, or already in a team room.",
    ]
    if hack_day_state == "active":
        before_tasks.append("Finish the profile loop so you can enter matchmaking.")
    elif hack_day_state == "matchable":
        before_tasks.append("Review match cards and decide what team gaps matter most.")
    elif hack_day_state in {"team_room", "workspace_connected"}:
        before_tasks.append("Align the team on one idea, one owner per workstream, and one demo path.")

    first_30_tasks = [
        "Pick the smallest credible project direction and define the demo promise.",
        "Assign roles for build, demo, pitch, and submission ownership.",
    ]
    if hack_day_state == "matchable":
        first_30_tasks.insert(0, "Run a focused matchmaking pass before locking solo scope.")
    if hack_day_state in {"team_room", "workspace_connected"}:
        first_30_tasks.append("Write the idea and division of work into team-room notes.")

    first_2_tasks = [
        "Build a walking skeleton that proves the core workflow end to end.",
        "Cut anything that does not improve judging fit or demo clarity.",
    ]
    first_2_tasks.extend(_workspace_tasks(workspace_repo))

    validation_tasks = [
        "Test the core flow with one realistic example.",
        "Check the project against judging criteria and sponsor constraints.",
        "Decide what to cut before demo prep starts.",
    ]

    demo_tasks = [
        "Freeze the demo path and prepare fallback screenshots or sample data.",
        "Write the 60 second story: problem, insight, build, impact.",
        "Confirm repo, video, and summary requirements.",
    ]
    if final_due:
        demo_tasks.append(f"Work backward from final submission: {final_due}.")

    final_tasks = [
        "Submit only polished, working artifacts.",
        "Verify links, repo access, demo video, and project summary.",
        "Keep a final fallback package ready in case deployment fails.",
    ]

    return [
        {
            "stage": "before_event",
            "label": "Before the event",
            "when": starts_at or "Before the Hack Day starts",
            "tasks": before_tasks,
            "decision_checkpoint": "Are you ready to become matchable or start team execution?",
            "risk_flags": ["Missing event context can waste the first hour."],
            "optional_help": ["Ask for missing rules, judging criteria, or team gaps."],
        },
        {
            "stage": "first_30_minutes",
            "label": "First 30 minutes",
            "when": f"At kickoff: {starts_at}" if starts_at else "At kickoff",
            "tasks": first_30_tasks,
            "decision_checkpoint": "Can you explain the idea and demo in one sentence?",
            "risk_flags": ["Too many ideas or unclear ownership will slow the team immediately."],
            "optional_help": ["Ask for a scope cut or role split."],
        },
        {
            "stage": "first_2_hours",
            "label": "First 2 hours",
            "when": "After kickoff, before deep build time",
            "tasks": first_2_tasks,
            "decision_checkpoint": "Does the core workflow run end to end?",
            "risk_flags": ["Integrations and auth can consume the sprint if not boxed in early."],
            "optional_help": ["Ask for a fallback implementation plan."],
        },
        {
            "stage": "validation",
            "label": "Validation checkpoint",
            "when": "Before demo prep",
            "tasks": validation_tasks,
            "decision_checkpoint": "What must be cut so the demo is reliable?",
            "risk_flags": ["A technically impressive build can still lose if the story is unclear."],
            "optional_help": ["Ask for judging alignment or a risk review."],
        },
        {
            "stage": "demo_prep",
            "label": "Demo preparation",
            "when": "Before final submission window",
            "tasks": demo_tasks,
            "decision_checkpoint": "Can someone else run the demo from the notes?",
            "risk_flags": ["Unrehearsed demos and missing submission assets fail late."],
            "optional_help": ["Ask for a pitch outline or demo script."],
        },
        {
            "stage": "final_submission",
            "label": "Final submission",
            "when": final_due or ends_at or "At the published submission deadline",
            "deadline": final_deadline,
            "tasks": final_tasks,
            "decision_checkpoint": "Are all required artifacts submitted and accessible?",
            "risk_flags": ["Late uploads, private repos, and broken links are avoidable losses."],
            "optional_help": ["Ask for a final submission checklist."],
        },
    ]


def generate_process_timeline(
    event: Any,
    *,
    profile: Any = None,
    team: list[Any] | None = None,
    hack_day: Any = None,
    team_room: Any = None,
    workspace_repo: Any = None,
) -> dict[str, Any]:
    """Generate a concise, deadline-aware Hack Day process timeline."""
    event_dict = _as_dict(event)
    _ = _as_dict(profile)
    _ = [_as_dict(member) for member in _as_list(team)]
    hack_day_dict = _as_dict(hack_day)
    team_room_dict = _as_dict(team_room)
    workspace_repo_dict = _as_dict(workspace_repo)

    deadlines = _deadline_lines(event_dict)
    state = _hack_day_state(hack_day_dict, team_room_dict, workspace_repo_dict)
    stages = _stage_templates(
        event=event_dict,
        deadlines=deadlines,
        hack_day_state=state,
        workspace_repo=workspace_repo_dict,
    )

    missing_inputs: list[str] = []
    if not event_dict.get("starts_at"):
        missing_inputs.append("starts_at")
    if not event_dict.get("ends_at"):
        missing_inputs.append("ends_at")
    if not deadlines:
        missing_inputs.append("deadlines")
    if not event_dict.get("judging_criteria"):
        missing_inputs.append("judging_criteria")

    timeline_signals = ["default_hack_day_stages"]
    if deadlines:
        timeline_signals.append("event_deadlines")
    if state != "event_only":
        timeline_signals.append(f"hack_day_state:{state}")
    if workspace_repo_dict:
        timeline_signals.append("workspace_repo_connected")
    if missing_inputs:
        timeline_signals.append("missing_inputs")

    return {
        "status": "generated",
        "stages": stages,
        "timeline_signals": timeline_signals,
        "missing_inputs": missing_inputs,
        "next": "review_timeline",
    }
