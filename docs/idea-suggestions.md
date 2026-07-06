# Idea Suggestions

## Purpose

Suggest project ideas that fit the event and the team.

## Ranking signals

- hackathon theme match
- feasibility within the time window
- fit with team skills
- novelty versus risk
- judging alignment
- ability to demo quickly

## Output types

- safe default idea
- ambitious idea
- niche idea
- fast-to-build fallback idea

## Prototype API

`POST /planner/ideas`

The request accepts the normalized event context from event ingest, plus optional
profile, team, and topic signals.

```json
{
  "event": {
    "event_name": "Agent Sprint Hackathon",
    "tracks": ["AI agents", "developer tools"],
    "judging_criteria": [
      {"name": "Technical execution"},
      {"name": "Demo quality"}
    ],
    "confidence": "high"
  },
  "profile": {
    "harness_id": "harness_alice",
    "display_label": "Alice",
    "skills": ["FastAPI", "Python", "AI agents"],
    "interests": ["developer tools"],
    "looking_for": ["design"]
  },
  "topics": ["workspace automation"]
}
```

Example response:

```json
{
  "status": "ranked",
  "ideas": [
    {
      "idea_type": "safe_default",
      "summary": "AI agents command center for teams to make faster decisions",
      "why_it_fits": "Maps directly to AI agents and can show Technical execution in one clear demo.",
      "main_tradeoff": "Less surprising, but easiest to scope and explain.",
      "score": 92,
      "signals": [
        "Track fit: AI agents",
        "Judging fit: Technical execution",
        "Topic fit: workspace automation",
        "Skill fit: fastapi, python"
      ]
    }
  ],
  "ranking_signals": [
    "event_tracks",
    "judging_criteria",
    "profile_or_team_skills",
    "chosen_topics"
  ],
  "next": "review_ideas"
}
```

The full response always includes four idea types:

- `safe_default`
- `ambitious`
- `niche`
- `fast_fallback`

## UX notes

- Keep suggestions short.
- Explain why each idea is a fit.
- Show tradeoffs clearly.
- Let the user refine by topic, stack, or team profile.
