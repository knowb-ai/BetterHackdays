# Process Timeline

## Purpose

Provide a simple execution plan from event discovery to demo day.

## Example stages

- before the event
- first 30 minutes
- first 2 hours
- same day validation
- demo preparation
- final submission

## What the timeline should include

- key tasks
- deadlines
- decision checkpoints
- risk flags
- optional help prompts

## Prototype API

`POST /planner/timeline`

The request accepts normalized event context, plus optional Hack Day, team
room, and workspace repo context.

```json
{
  "event": {
    "event_name": "Agent Sprint Hackathon",
    "starts_at": "2026-07-10 09:00",
    "ends_at": "2026-07-12 18:00",
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
  "stages": [
    {
      "stage": "first_30_minutes",
      "label": "First 30 minutes",
      "when": "At kickoff: 2026-07-10 09:00",
      "tasks": [
        "Pick the smallest credible project direction and define the demo promise.",
        "Assign roles for build, demo, pitch, and submission ownership."
      ],
      "decision_checkpoint": "Can you explain the idea and demo in one sentence?",
      "risk_flags": [
        "Too many ideas or unclear ownership will slow the team immediately."
      ],
      "optional_help": [
        "Ask for a scope cut or role split."
      ]
    },
    {
      "stage": "final_submission",
      "label": "Final submission",
      "when": "2026-07-12 16:00",
      "deadline": {
        "name": "Final submission",
        "due_at": "2026-07-12 16:00",
        "description": "Submit repo and demo video."
      },
      "tasks": [
        "Submit only polished, working artifacts.",
        "Verify links, repo access, demo video, and project summary.",
        "Keep a final fallback package ready in case deployment fails."
      ],
      "decision_checkpoint": "Are all required artifacts submitted and accessible?",
      "risk_flags": [
        "Late uploads, private repos, and broken links are avoidable losses."
      ],
      "optional_help": [
        "Ask for a final submission checklist."
      ]
    }
  ],
  "timeline_signals": [
    "default_hack_day_stages",
    "event_deadlines",
    "hack_day_state:workspace_connected",
    "workspace_repo_connected"
  ],
  "missing_inputs": [],
  "next": "review_timeline"
}
```

The full response uses six stages:

- `before_event`
- `first_30_minutes`
- `first_2_hours`
- `validation`
- `demo_prep`
- `final_submission`

## Missing deadline behavior

When event dates or deadlines are missing, the timeline still returns default
Hack Day stages. Missing fields are listed in `missing_inputs` so the CLI,
agent, or user can decide whether to ask for more context.

## Workspace repo behavior

When a team room has a connected workspace repo, timeline tasks can point to
repo docs such as `docs/process-plan.md`, `docs/checklist.md`, and
`docs/submission.md`. The timeline should not assume repo setup exists before
the team has explicitly approved GitHub workspace handoff.

## Open questions

- Should timelines be template-based or generated per event?
- How much should the timeline adapt to team size?
- What is the ideal default detail level?
