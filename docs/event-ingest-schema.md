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

Field-level source notes should point important extracted fields back to the source that produced them:

```json
{
  "field": "event_name",
  "source_label": "Event page paste",
  "confidence": "high",
  "note": "Extracted from pasted text."
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
  "sources": [],
  "source_notes": []
}
```

## Required Fields

- response `status`
- response `event`
- response `missing_fields`
- response `next`
- event `confidence`
- event `open_questions`
- event `sources`
- event `source_notes`

Within `event`, every domain field should be optional for M2. Missing data should be explicit rather than guessed.

## Field Catalog

| Field | Type | M2 Required | Notes |
| --- | --- | --- | --- |
| `event_name` | string | no | Best available name or title. |
| `description` | string | no | Short event summary when obvious. |
| `format` | string | no | One of `in_person`, `online`, or `hybrid` when clear. |
| `location` | string | no | Venue, city, or remote location details. |
| `timezone` | string | no | IANA timezone or source-provided text. |
| `starts_at` | string | no | Source-provided date or datetime. |
| `ends_at` | string | no | Source-provided date or datetime. |
| `tracks` | string array | no | Themes, categories, or tracks. |
| `team_size` | object | no | `min` and `max` when stated. |
| `deadlines` | object array | no | Named deadline checkpoints. |
| `judging_criteria` | object array | no | Criteria used for scoring or prizes. |
| `rules` | string array | no | Rules directly stated in the source. |
| `constraints` | string array | no | Required or limiting conditions. |
| `sponsors` | object array | no | Sponsor names and requirements when stated. |
| `submission` | object | no | Submission URL and requirements. |
| `allowed_tools` | string array | no | Tools explicitly allowed. |
| `recommended_tools` | string array | no | Tools recommended by organizers. |
| `open_questions` | string array | yes | Missing or ambiguous fields to review. |
| `confidence` | string | yes | One of `high`, `medium`, or `low`. |
| `sources` | object array | yes | Source documents or pasted text metadata. |
| `source_notes` | object array | yes | Field-level extraction notes. |

## Confidence

Use a simple string for M2:

- `high`: field values are directly stated in the source
- `medium`: field values are inferred from nearby text
- `low`: important fields are missing or ambiguous

For the first pasted-text prototype, field-level `source_notes` should only claim `high` confidence when values are directly extracted from pasted text. Later ingest modes can add more nuanced confidence.

## Conflict Handling

When sources disagree:

- keep the latest directly stated value
- add the conflict to `open_questions`
- keep source notes so the user can review the ambiguity

M2 only accepts one pasted-text source per request, so conflict handling is documented for the schema but not yet implemented as a multi-source merge.

## Answers to Event Ingest Open Questions

- Smallest useful schema: the response shape above, with optional domain fields, explicit `missing_fields`, and required confidence/source metadata.
- Conflicting source data: carry conflicts in `open_questions` and `source_notes`; multi-source conflict resolution is outside the first endpoint.
- Optional fields: all event domain fields are optional for M2 because pasted text may be incomplete.
- Low confidence: return `confidence: "low"` and list missing or unclear fields instead of inventing values.

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
