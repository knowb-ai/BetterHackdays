# MCP Server

## Purpose

Expose the BetterHackdays function layer through a real MCP server entry point
for a live Hack Day.

The REST API and MCP server share `app.mcp_tools` so behavior stays aligned.
The FastAPI routes validate HTTP requests. The MCP server registers the same
plain-Python functions as tools for coding agents and harnesses.

## Entry Point

```bash
.venv/bin/python -m app.mcp_server
```

The module creates a `FastMCP` server named `betterhackdays-hack-day` and
registers the current tool layer.

## Registered Tools

- `connect_harness`
- `update_profile`
- `get_match_cards`
- `like_profile`
- `pass_profile`
- `get_matches`
- `start_survey`
- `answer_survey`
- `get_survey_state`
- `ingest_event_text`
- `rank_idea_suggestions`
- `generate_process_timeline`
- `generate_prep_checklist`
- `resolve_slug`

## Hack Day Connection Flow

1. The organizer creates or wakes the public Hack Day MCP/API service.
2. A CLI, IDE, or coding agent harness connects to that endpoint.
3. The harness calls `connect_harness` or `start_survey`.
4. The participant answers survey questions through `answer_survey`.
5. When the profile is complete, the participant becomes matchable.
6. The harness calls match, planner, and slug tools as the event progresses.

This flow keeps the product provider-neutral. Render can host the public
service, but the MCP model should not depend on Render-specific assumptions.

## Render-Oriented Deployment

The same application can expose REST and MCP entry points from one deployed
service shape:

- REST: `uvicorn app.main:app`
- MCP: `.venv/bin/python -m app.mcp_server`

Render deployment should set the same environment values for both entry
points, especially `DATABASE_URL`, `APP_NAME`, and `SEED_PROFILES`.

The MCP entry point initializes the SQLite schema before registering tools.
Production deployment still needs durable database and auth decisions before
public writes are enabled.

## Workspace Repo Connector Model

The main BetterHackdays MCP server owns Hack Day and team-room state. A
connected GitHub workspace repo is the durable team drive for project state.

The MCP-facing workspace repo connector model includes:

- owner
- repo
- default branch
- permission status
- allowed write targets
- last synced planning snapshot

Initial allowed write targets:

- `README.md`
- `AGENTS.md`
- `docs/event-context.md`
- `docs/team-profile.md`
- `docs/idea.md`
- `docs/process-plan.md`
- `docs/checklist.md`
- `docs/submission.md`
- `.betterhackdays/session.json`
- `.betterhackdays/tooling.md`
- `.betterhackdays/skills/`

Future team-room MCP tools should be able to:

- create or update planning docs
- create starter code
- add or update `AGENTS.md`
- add tool manifests
- add skill stubs
- record decisions and traces
- summarize current workspace state
- prepare submission artifacts

Repo writes must be explicit, reviewable project state. The MCP layer must not
write secrets, OAuth tokens, or private contact details into workspace repos,
and it should avoid overwriting participant-authored files without drift
checks.
