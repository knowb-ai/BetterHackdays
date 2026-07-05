# Event Ingest

## Purpose

Capture hackathon details from multiple sources and normalize them into a format the product can use.

## Possible sources

- event landing page
- rules PDF
- slide deck
- registration form
- organizer writeup
- pasted text from a webpage

## Data to extract

- event name
- date and time
- deadline checkpoints
- location / format
- track or category
- judging criteria
- constraints
- sponsor requirements
- submission instructions

## M2 Prototype Endpoint

`POST /event/ingest/text` accepts pasted event text and returns normalized event context plus explicit missing fields.

Example request:

```json
{
  "source_label": "Event page paste",
  "text": "Event: Agent Sprint Hackathon\nLocation: Berlin\nStart: 2026-07-10 09:00\nEnd: 2026-07-12 18:00\nTracks: AI agents, developer tools\nTeam size: 1-4\nSubmission deadline: 2026-07-12 16:00 via https://example.com/submit\nJudging criteria: Technical execution, demo quality"
}
```

Abridged example response:

```json
{
  "status": "ingested",
  "event": {
    "event_name": "Agent Sprint Hackathon",
    "location": "Berlin",
    "starts_at": "2026-07-10 09:00",
    "ends_at": "2026-07-12 18:00",
    "tracks": ["AI agents", "developer tools"],
    "team_size": {
      "min": 1,
      "max": 4
    },
    "deadlines": [
      {
        "name": "Final submission",
        "due_at": "2026-07-12 16:00",
        "description": "Submission deadline: 2026-07-12 16:00 via https://example.com/submit"
      }
    ],
    "judging_criteria": [
      {
        "name": "Technical execution",
        "description": "Technical execution"
      },
      {
        "name": "demo quality",
        "description": "demo quality"
      }
    ],
    "open_questions": [],
    "confidence": "high"
  },
  "missing_fields": [],
  "next": "review_event_context"
}
```

## Questions to answer

- What is the smallest useful schema?
- How should conflicting source data be resolved?
- Which fields should be optional?
- What should happen when ingest confidence is low?
