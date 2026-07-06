# Prep Checklist

## Purpose

Give a builder or team the shortest useful list of actions to take now.

The checklist is the most immediate planner output. Idea suggestions answer
what to build. The timeline answers when to do the work. The checklist answers
what to do next.

## Prototype API

`POST /planner/checklist`

The request accepts normalized event context, optional profile/team context,
and optional Hack Day, team room, and workspace repo context.

```json
{
  "event": {
    "event_name": "Agent Sprint Hackathon",
    "tracks": ["AI agents", "developer tools"],
    "deadlines": [
      {
        "name": "Final submission",
        "due_at": "2026-07-12 16:00",
        "description": "Submit repo and demo video."
      }
    ],
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
    "interests": ["developer tools"]
  },
  "hack_day": {
    "participant_state": "matchable"
  },
  "team_room": {
    "room_id": "room_123",
    "slug": "agent-sprint"
  },
  "workspace_repo": {
    "owner": "team-agent-sprint",
    "repo": "betterhackdays-agent-sprint",
    "connected": true
  }
}
```

Example response:

```json
{
  "status": "generated",
  "sections": [
    {
      "section": "prep_tasks",
      "title": "Prep for Agent Sprint Hackathon",
      "items": [
        {
          "task": "Review the event context.",
          "why": "Rules, tracks, judging criteria, and submission requirements shape every later decision.",
          "done_hint": "You can name the track, judging criteria, and final submission requirement.",
          "linked_doc": "docs/event-context.md"
        }
      ]
    },
    {
      "section": "workspace_next_steps",
      "title": "Workspace next steps",
      "items": [
        {
          "task": "Use team-agent-sprint/betterhackdays-agent-sprint as the source of truth.",
          "why": "The connected repo is the team-room MCP workspace target.",
          "done_hint": "Team docs and code changes land in the connected repo.",
          "linked_doc": "README.md"
        }
      ]
    }
  ],
  "checklist_signals": [
    "hack_day_state:workspace_connected",
    "event_deadlines",
    "profile_or_team_skills",
    "workspace_repo_connected"
  ],
  "missing_inputs": [],
  "next": "act_on_checklist"
}
```

## Sections

The full response uses five sections:

- `prep_tasks`
- `first_hour_focus`
- `missing_inputs`
- `optional_help`
- `workspace_next_steps`

## State behavior

- Active participants see profile-completion tasks before matchmaking tasks.
- Matchable participants see match-card and team-gap tasks.
- Team rooms see idea-lock and ownership tasks.
- Connected workspace repos add repo docs and agent-guidance tasks.

## Workspace repo behavior

The checklist only treats a workspace repo as ready when it is explicitly
connected. Until then, GitHub setup remains a permissioned post-match next
step.

Checklist output should never suggest writing secrets, OAuth tokens, or private
contact details into repo files.
