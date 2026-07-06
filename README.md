# BetterHackdays

BetterHackdays is the operating system for a live Hack Day.

It helps builders enter the same event context, become matchable, form a team,
open a room, connect the room to a workspace repo, and keep agents pointed at
the shared project state.

This README is written for us as product builders. It describes the intended
experience and the current operating loop. Development setup lives in
[Development](./docs/development.md).

## The Hack Day Scenario

Imagine the organizer is preparing Agent Sprint Hackathon in Berlin.

The event has a short window, judging criteria, tracks, team-size rules, and a
submission deadline. People will arrive with different tools, different skill
levels, and very little time to find the right collaborators.

BetterHackdays gives that event one live Hack Day session.

```text
organizer creates or wakes the Hack Day
builders connect from code agents, CLIs, IDEs, QR links, or the website
event context becomes available to every surface
participants complete a fast profile loop
matchable builders review cards and like promising teammates
mutual likes create a team room
room keywords and slugs bring people back to the right place
the team approves workspace repo setup
agents use the repo as durable project state
```

The goal is not to make people browse a dashboard. The goal is to get them from
"I just arrived" to "we know what we are building and where the work lives" as
quickly as possible.

## Step 1: The Organizer Loads Event Context

The organizer starts with raw event material:

- event page text
- rules
- tracks
- deadlines
- judging criteria
- sponsor requirements
- submission instructions

The event ingest flow normalizes that into event context and names missing
fields explicitly. That context feeds idea suggestions, timelines, checklists,
and agent-readable instructions.

Current prototype surface:

- `POST /event/ingest/text`

The useful outcome is a shared event memory:

- what the event is
- when the team must submit
- what judges care about
- which constraints matter
- what still needs clarification

## Step 2: Builders Join The Hack Day

A builder connects from a code agent, terminal client, IDE harness, QR entry,
or website.

The participant is first `active`. That means they are present, but not yet
ready to appear in matchmaking.

Current prototype surfaces:

- `POST /connect`
- `POST /survey/start`
- `POST /survey/answer`
- `GET /survey/state`

The profile loop is deliberately short. It collects enough signal to understand
skills, interests, working style, trust needs, availability, and a display
label. When the loop is done, the participant becomes `matchable`.

## Step 3: Matchable Builders Review Cards

Once matchable, a builder can review anonymized match cards.

Current prototype surfaces:

- `GET /matchmaking/cards`
- `POST /matchmaking/like`
- `POST /matchmaking/pass`
- `GET /matches`

The current scorer is simple and inspectable. It rewards shared interests,
complementary skills, role fit, and compatible project vibe. It excludes self,
already-swiped profiles, and already-matched profiles.

A mutual like creates a match. That is the handoff point from discovery into
collaboration.

## Step 4: The System Suggests What To Build And How To Start

The team does not need a long strategy document during the event. It needs a
small number of useful next moves.

Current prototype surfaces:

- `POST /planner/ideas`
- `POST /planner/timeline`
- `POST /planner/checklist`

The planner can produce:

- ranked idea directions
- a deadline-aware process timeline
- a concise prep checklist
- first-hour focus
- missing inputs
- optional deeper help

These outputs should stay short by default. Extra guidance should be available
without turning the main flow into a wall of text.

## Step 5: Slugs Resolve The Right Room

Builders need a phrase they can say, scan, paste, or hand to an agent.

Supported first-version formats:

```text
<hack-day-code>
<standalone-slug>
<hack-day-code> <room-keyword>
<hack-day-code> <team-keyword>
```

Example:

```text
daytona pillow
```

Current prototype surface:

- `POST /slug/resolve`

The resolver can return:

- Hack Day session
- active participant entry
- matchable participant setup
- matched team invite
- team room
- connected workspace repo metadata

Workspace repo metadata is only returned when the caller is authorized for the
team room. Slug possession, QR scans, and IP cluster hints do not grant access.

## Step 6: The Team Room Becomes The Collaboration Home

A team room is the post-match collaboration object.

It should hold:

- matched participant IDs
- selected idea direction
- planning notes
- shared links
- GitHub repo status
- workspace setup state
- MCP context for the team

The current prototype models this in slug resolution, timeline, and checklist
inputs. Durable team-room persistence is still a follow-up.

## Step 7: The Workspace Repo Becomes Durable Project State

After the team approves GitHub setup, the workspace repo becomes the durable
project home.

The connected repo should expose safe metadata to authorized participants:

- owner
- repo name
- default branch
- permission status
- allowed write targets
- last synced planning snapshot

The repo should never receive secrets, OAuth tokens, or private contact details
by default.

The intended workspace bundle includes:

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

## Current Operating Surfaces

```text
event ingest
  POST /event/ingest/text

participant entry and survey
  POST /connect
  POST /survey/start
  POST /survey/answer
  GET  /survey/state

matchmaking
  GET  /matchmaking/cards
  POST /matchmaking/like
  POST /matchmaking/pass
  GET  /matches

planning
  POST /planner/ideas
  POST /planner/timeline
  POST /planner/checklist

slug and room resolution
  POST /slug/resolve

health
  GET /health
```

`app.mcp_tools` is the shared function layer under these surfaces. REST routes
delegate there, and `app.mcp_server` registers the same behavior as MCP tools
without forking business logic.

## What Is Implemented Now

- FastAPI backend
- SQLite-backed profiles, swipes, matches, and survey progress
- Socratic onboarding survey
- event text ingest
- matchmaking cards, likes, passes, and mutual matches
- idea suggestions
- process timeline
- prep checklist
- slug resolution prototype
- workspace repo metadata gating inside slug resolution
- real MCP server wrapper around the shared function layer
- OKF contract for governed knowledge files
- unit and scenario integration tests

## What Is Missing For The Full Narrative

These are the places where the scenario still depends on follow-up work:

- Durable Hack Day session records instead of passing Hack Day state into
  resolver calls.
- Durable team-room records and room membership transitions.
- Real authorization and identity, beyond caller-provided participant IDs.
- GitHub repo creation or attachment flow after explicit team approval.
- Workspace bundle writer for initializing repo docs and `.betterhackdays`
  metadata.
- QR and website entry points that call the same slug resolver.
- Organizer tools for creating Hack Days, assigning codes, and managing room
  visibility.
- Contact-sharing consent flows for Discord, email, GitHub usernames, and other
  handles.
- Production persistence migrations and deployment operations.

Those should become follow-up tickets before we claim the entire Hack Day loop
is production-ready.

## Source Of Truth

- [Hack Day Session Architecture](./docs/hack-day-session-architecture.md)
- [Slug Resolution Model](./docs/slug-resolution-model.md)
- [Hackathon Playbook](./docs/hackathon-playbook.md)
- [MCP Server](./docs/mcp-server.md)
- [Development](./docs/development.md)
