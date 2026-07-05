# Event Ingest Schema

Status: M2 draft

Linked issues:

- #8 Define the event ingest schema
- #6 Prototype pasted text event ingest

## Goal

Define the smallest event context shape that can support hackathon prep, idea suggestions, and deadline-aware planning.

## Source Model

Every ingest result should keep source information so agents can explain where a field came from and what still needs review.

```json
{
  "source_type": "pasted_text",
  "source_label": "Event page paste",
  "source_url": null,
  "captured_at": "2026-07-05T00:00:00Z"
}
```

## Event Context

```json
{
  "event_name": "Example Hackathon",
  "description": "Short event summary.",
  "format": "in_person",
  "location": "Berlin",
  "timezone": "Europe/Berlin",
  "starts_at": "2026-07-10T09:00:00+02:00",
  "ends_at": "2026-07-12T18:00:00+02:00",
  "tracks": ["AI agents", "developer tools"],
  "team_size": {
    "min": 1,
    "max": 4
  },
  "deadlines": [
    {
      "name": "Final submission",
      "due_at": "2026-07-12T16:00:00+02:00",
      "description": "Submit demo link and repository."
    }
  ],
  "judging_criteria": [
    {
      "name": "Technical execution",
      "description": "Quality and completeness of the build."
    }
  ],
  "rules": ["Use allowed APIs only."],
  "constraints": ["Must submit a public demo video."],
  "sponsors": [
    {
      "name": "Example Sponsor",
      "requirements": ["Use sponsor API for prize eligibility."]
    }
  ],
  "submission": {
    "url": "https://example.com/submit",
    "requirements": ["Project name", "Repository URL", "Demo URL"]
  },
  "allowed_tools": ["Python", "FastAPI"],
  "recommended_tools": ["Daytona"],
  "open_questions": ["What is the exact team size limit?"],
  "confidence": "medium",
  "sources": []
}
```

## Required Fields

- `event_name`
- `source_type`
- `confidence`
- `open_questions`

All other fields should be optional for M2. Missing data should be explicit rather than guessed.

## Confidence

Use a simple string for M2:

- `high`: field values are directly stated in the source
- `medium`: field values are inferred from nearby text
- `low`: important fields are missing or ambiguous

## Conflict Handling

When sources disagree:

- keep the latest directly stated value
- add the conflict to `open_questions`
- keep source notes so the user can review the ambiguity

## M2 Boundaries

In scope:

- `POST /event/ingest/text`
- pasted text as the first ingest source
- deterministic extraction where possible
- explicit missing fields
- schema that later planner and idea modules can consume

Out of scope:

- PDF parsing
- slide parsing
- browser ingestion
- account or organizer permissions
- automated deadline reminders
