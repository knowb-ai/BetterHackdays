"""Seed data and seeding logic for anonymous builder profiles.

Profiles are intentionally anonymous: fake harness_ids, no real names, no
emails. They cover the builder archetypes required for a demo sprint:

* frontend / demo builder
* backend / API builder
* AI agent builder
* infra / sandbox builder
* product / storytelling builder
* design / pitch builder
* data / RAG builder
* full-stack builder
"""

from __future__ import annotations

from typing import Any

from .db import _dumps, _row_to_dict, get_conn

SEED_PROFILES: list[dict[str, Any]] = [
    {
        "harness_id": "harness_frontend_001",
        "display_label": "Frontend/demo builder",
        "skills": ["React", "Vite", "Tailwind", "Framer Motion"],
        "interests": ["demos", "polished UI", "hackathon story"],
        "preferred_role": "frontend",
        "project_vibe": "ship fast",
        "looking_for": ["backend", "AI agents"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_backend_002",
        "display_label": "Backend/API builder",
        "skills": ["FastAPI", "SQLite", "Docker"],
        "interests": ["AI agents", "developer tools", "hackathon infra"],
        "preferred_role": "backend",
        "project_vibe": "ship fast",
        "looking_for": ["frontend", "AI infra"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_ai_agent_003",
        "display_label": "AI agent builder",
        "skills": ["LLM orchestration", "tool calling", "Python", "MCP"],
        "interests": ["autonomous agents", "agent workspaces", "evals"],
        "preferred_role": "AI",
        "project_vibe": "research driven",
        "looking_for": ["backend", "data/RAG"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_infra_004",
        "display_label": "Infra/sandbox builder",
        "skills": ["Daytona", "Docker", "Terraform", "CI/CD"],
        "interests": ["dev environments", "sandboxing", "infra automation"],
        "preferred_role": "infra",
        "project_vibe": "platform first",
        "looking_for": ["frontend", "AI agents"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_product_005",
        "display_label": "Product/storytelling builder",
        "skills": ["product framing", "pitch decks", "scoping"],
        "interests": ["founder mode", "demos", "winning judges"],
        "preferred_role": "product",
        "project_vibe": "story first",
        "looking_for": ["frontend", "backend", "AI"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_design_006",
        "display_label": "Design/pitch builder",
        "skills": ["Figma", "pitch design", "motion", "branding"],
        "interests": ["polish", "demo arcs", "visual story"],
        "preferred_role": "design",
        "project_vibe": "ship fast",
        "looking_for": ["frontend", "product"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_data_007",
        "display_label": "Data/RAG builder",
        "skills": ["embeddings", "vector DB", "RAG", "Python"],
        "interests": ["retrieval", "pipelines", "evals"],
        "preferred_role": "data",
        "project_vibe": "data driven",
        "looking_for": ["backend", "AI agents"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_fullstack_008",
        "display_label": "Full-stack builder",
        "skills": ["React", "FastAPI", "Postgres", "Docker"],
        "interests": ["end-to-end apps", "DX", "shipping"],
        "preferred_role": "full-stack",
        "project_vibe": "ship fast",
        "looking_for": ["AI agents", "infra"],
        "availability": "full sprint",
    },
    {
        "harness_id": "harness_devtools_009",
        "display_label": "Devtools/harness builder",
        "skills": ["CLI", "Python", "TypeScript", "DX"],
        "interests": ["developer tools", "agent harnesses", "automation"],
        "preferred_role": "backend",
        "project_vibe": "ship fast",
        "looking_for": ["frontend", "AI"],
        "availability": "weekend only",
    },
    {
        "harness_id": "harness_mobile_010",
        "display_label": "Mobile/demo builder",
        "skills": ["React Native", "Expo", "animations"],
        "interests": ["mobile demos", "live demos", "polish"],
        "preferred_role": "frontend",
        "project_vibe": "ship fast",
        "looking_for": ["backend", "design"],
        "availability": "full sprint",
    },
]


def seed_profiles(force: bool = False) -> int:
    """Insert seed profiles that are not already present.

    Args:
        force: If True, overwrite existing seeded profiles in place.

    Returns:
        The number of seed profiles inserted (or upserted when force=True).
    """
    inserted = 0
    with get_conn() as conn:
        for profile in SEED_PROFILES:
            existing = conn.execute(
                "SELECT 1 FROM profiles WHERE harness_id = ?",
                (profile["harness_id"],),
            ).fetchone()

            if existing and not force:
                continue

            if force:
                conn.execute(
                    """
                    INSERT INTO profiles (
                        harness_id, display_label, skills, interests,
                        preferred_role, project_vibe, looking_for,
                        availability, is_seeded
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(harness_id) DO UPDATE SET
                        display_label = excluded.display_label,
                        skills = excluded.skills,
                        interests = excluded.interests,
                        preferred_role = excluded.preferred_role,
                        project_vibe = excluded.project_vibe,
                        looking_for = excluded.looking_for,
                        availability = excluded.availability,
                        is_seeded = 1,
                        updated_at = datetime('now')
                    """,
                    (
                        profile["harness_id"],
                        profile["display_label"],
                        _dumps(profile["skills"]),
                        _dumps(profile["interests"]),
                        profile["preferred_role"],
                        profile["project_vibe"],
                        _dumps(profile["looking_for"]),
                        profile["availability"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO profiles (
                        harness_id, display_label, skills, interests,
                        preferred_role, project_vibe, looking_for,
                        availability, is_seeded
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        profile["harness_id"],
                        profile["display_label"],
                        _dumps(profile["skills"]),
                        _dumps(profile["interests"]),
                        profile["preferred_role"],
                        profile["project_vibe"],
                        _dumps(profile["looking_for"]),
                        profile["availability"],
                    ),
                )
            inserted += 1
    return inserted


def list_profiles() -> list[dict[str, Any]]:
    """Return all profiles (seeded + real), with list columns decoded."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM profiles ORDER BY created_at ASC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
