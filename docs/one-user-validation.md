# One-User Validation

## Purpose

Validate the full Hack Day experience with one human operator and one seeded
companion profile.

This is a smoke test for the product narrative, not a substitute for multi-user
event testing. One user can verify the end-to-end flow by driving one active
harness and one seeded match target.

## What This Covers

- event ingest
- connect and survey flow
- match cards and mutual like
- idea suggestions
- process timeline
- prep checklist
- slug resolution
- MCP server registration
- README-driven operating narrative

## What It Does Not Cover

- real multi-user behavior under concurrency
- organizer tooling
- QR entry
- browser-first room management
- live GitHub workspace writes
- real authorization and identity

## Setup

Use the repo virtualenv and temporary SQLite database for the run.

```bash
.venv/bin/pip install -r requirements.txt
DATABASE_URL=sqlite:///./tmp/one-user-validation.db \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Keep a second terminal for the client or for direct HTTP calls.

## Validation Path

1. Confirm the service is up.
2. Ingest the hackathon event text.
3. Connect one harness and complete the survey.
4. Seed or create one complementary builder profile.
5. Load match cards and verify the expected candidate appears.
6. Like the candidate from both sides so a mutual match exists.
7. Run planner ideas, timeline, and checklist against the same event.
8. Resolve a Hack Day slug and confirm room metadata only appears for the
   authorized caller.
9. Start the MCP server entry point and confirm the tool surface registers.

## Seeded Companion

Use a seeded profile such as a backend or design builder to act as the one
companion in a single-user run. The purpose is to validate the product shape,
not to simulate a live crowd.

## Expected Signals

- survey progress advances and persists
- match cards are returned in a stable order
- a mutual like creates a match
- planner outputs stay short and actionable
- slug resolution returns safe metadata
- unauthorized callers do not see workspace repo details
- MCP server startup succeeds

## Exit Criteria

- The flow works end to end for one operator.
- The README narrative matches the actual surfaces.
- Missing follow-up work is called out clearly before the run is treated as
  production validation.
