# One-User Validation

## Purpose

Validate the full Hack Day experience with one human operator and one seeded
companion profile.

This is a smoke test for the product narrative, not a substitute for multi-user
event testing. One user can verify the end-to-end flow by driving one active
harness and one seeded match target.

## Validation Goal

Prove that a single operator can move through the full flow with one seeded
companion and get a believable Hack Day result from the current runtime
surfaces.

The run should answer four questions:

- does the harness connect cleanly
- does the survey complete and persist
- do the planning and matching surfaces stay coherent
- does the MCP server expose the same tool layer as REST

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

## Operator Assumptions

- one human operator
- one seeded companion profile already available in the database
- temporary SQLite database for the run
- local `uvicorn` or direct route calls, not production deployment
- the operator can inspect JSON responses and compare them to the playbook

## Sample Inputs

Use one event, one harness, and one companion profile.

Suggested event text:

```text
Event: Agent Sprint Hackathon
Location: Berlin
Timezone: Europe/Berlin
Start: 2026-07-10 09:00
End: 2026-07-12 18:00
Tracks: AI agents, developer tools
Team size: 1-4
Submission deadline: 2026-07-12 16:00 via https://example.com/submit
Judging criteria: Technical execution, demo quality
Submission requirements: Repository URL, demo video
```

Suggested harness id:

```text
harness_alice
```

Suggested companion shape:

- display label: `Bob`
- skills: `backend`, `FastAPI`, `GitHub workspace setup`
- interests: `developer tools`, `AI agents`
- preferred role: `backend`
- project vibe: `ship fast`
- looking for: `frontend`
- availability: `full sprint`

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
2. Ingest the hackathon event text and confirm the normalized event has the
   expected title, location, tracks, deadline, and judging criteria.
3. Connect one harness and complete the survey.
4. Seed or create one complementary builder profile.
5. Load match cards and verify the expected candidate appears first or near
   the top.
6. Like the candidate from both sides so a mutual match exists and the match
   appears for both harnesses.
7. Run planner ideas, timeline, and checklist against the same event and
   confirm the outputs mention the event deadlines and workspace repo context.
8. Resolve a Hack Day slug and confirm room metadata only appears for the
   authorized caller.
9. Start the MCP server entry point and confirm the tool surface registers.

## QA Checklist

- `/connect` returns a profile and survey question 1
- `/survey/answer` advances the survey and persists progress
- `/matchmaking/cards` returns a stable deck with the seeded companion visible
- `/matchmaking/like` from both sides creates a match
- `/planner/ideas` returns four ranked idea types
- `/planner/timeline` includes the final submission deadline
- `/planner/checklist` includes workspace next steps when room context exists
- `/slug/resolve` hides workspace repo metadata from unauthorized callers
- `app.mcp_server.create_server()` returns a `FastMCP` server with registered tools

## Integration Coverage

The run should touch these layers in one pass:

- event ingest route and `app.mcp_tools.ingest_event_text`
- survey routes and survey persistence
- matchmaking routes and `app.mcp_tools.like_profile`
- planner routes and the shared planner functions
- slug resolution route and the shared resolver
- MCP server registration through `app.mcp_server`

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

## Evidence To Capture

- command used to run the app
- event ingest response
- survey completion response
- match card response
- mutual match response
- planner responses
- slug resolution response
- MCP server registration result
- any missing inputs or mismatches with the README

## Failure Signals

- survey resets unexpectedly
- matching deck excludes the seeded companion
- planner outputs miss deadline or repo context
- slug resolution leaks workspace metadata
- MCP server fails to register the current tool layer

## Exit Criteria

- The flow works end to end for one operator.
- The README narrative matches the actual surfaces.
- Missing follow-up work is called out clearly before the run is treated as
  production validation.
