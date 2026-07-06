# Hack Day Session Architecture

## Purpose

Define the product architecture for BetterHackdays as a live Hack Day
matchmaking and planning service.

This is the current product direction for the next architecture pass. It
replaces the earlier provider-specific deployment story with a Render-hosted
MCP/API server that coding agents and CLI clients can use during a hackathon.

## Core idea

BetterHackdays runs a public MCP/API server for a specific Hack Day.

An organizer wakes up or creates the Hack Day before the event starts. Builders
connect through a CLI, coding-agent harness, or IDE integration. The server
keeps track of active participants, completes their Socratic profiles, moves
qualified participants into matchmaking, and creates a team room when a mutual
match happens.

## Default architecture

```text
Coding agent / CLI / IDE harness
        ↓
BetterHackdays CLI or MCP client
        ↓
Public BetterHackdays MCP/API server
        ↓
Render-hosted backend
        ↓
Hack Day session state
        ↓
Participants, profiles, matchmaking, rooms
        ↓
GitHub repo and workspace setup
```

The core product should stay provider-neutral. Render is the default deployment
target for the public server, but the backend should not make provider-specific
assumptions in the product model.

## Key concepts

### Hack Day

A live work session for one hackathon, hack day, or event.

A Hack Day has:

- public endpoint
- event context
- active participants
- matchable participants
- matchmaking state
- team rooms
- optional GitHub workspace setup

### Active participant

A harness or user that has connected to the Hack Day but has not completed the
profile flow yet.

Active participants should not appear in matchmaking results until the required
profile loop is complete.

### Matchable participant

A participant with a completed Hack Day profile.

Matchable participants can browse cards, receive match suggestions, like or
pass other profiles, and be matched into a team room.

### IP cluster

A soft co-location signal based on similar network origin.

IP clustering should help prioritize nearby people at physical events, but it
must not be treated as identity, authentication, or proof of location.

### Team room

The post-match collaboration object.

A team room can hold:

- matched participant IDs
- selected idea direction
- planning notes
- shared links
- GitHub repo status
- workspace setup state
- MCP context for the team

### Workspace repo

A GitHub repository created or selected after the matched team approves the
required permissions.

The repo becomes the durable workspace for team documents, planning traces,
setup notes, and later agent-generated artifacts.

The workspace repo also acts as the team's MCP drive connector target. The
main BetterHackdays MCP server should treat this repo as the shared project
state for the team room once it has been approved and attached.

## Hack Day lifecycle

1. Organizer creates or wakes up a Hack Day.
2. Server exposes a public endpoint for the Hack Day.
3. Event context is loaded from pasted text, docs, slides, or organizer input.
4. Builder connects through CLI, MCP, or agent harness.
5. Server registers the builder as an active participant.
6. CLI asks whether the builder wants to join the Hack Day and start setup.
7. Socratic profile loop collects the required profile fields.
8. Completed participant moves into the matchable list.
9. Matchmaking prefers strong profile fit, with optional local/IP cluster boost.
10. Participants like or pass candidate profiles.
11. Mutual like creates a match.
12. Server notifies both participants or exposes the match through polling.
13. Server creates a team room.
14. Team approves GitHub permissions.
15. Server creates or attaches a shared GitHub repo.
16. Repo is registered as the team room's MCP workspace target.
17. Repo is initialized with team docs, planning files, code scaffolds, tool
    manifests, and MCP context.

## CLI and MCP experience

The CLI should be agent-friendly rather than browser-first.

The expected interaction is:

1. User or agent runs a connect command.
2. CLI calls the Hack Day MCP/API endpoint.
3. Server returns the Hack Day summary and a yes/no join prompt.
4. CLI asks the user whether to join.
5. If yes, CLI iterates through the Socratic survey questions.
6. Each answer is sent back to the server.
7. Server returns progress and the next question.
8. When complete, CLI shows that the participant is now matchable.
9. CLI can request cards, like, pass, check matches, and open team-room setup.

The same sequence should be usable from KiloCode, Warp, Codex, Cursor, Claude
Code, or another coding harness that can call MCP tools or shell commands.

## Matchmaking behavior

The first matchable version should use:

- completed Hack Day profile
- self-declared skills
- interests
- desired collaborators
- preferred role
- project vibe
- event context
- optional local/IP cluster boost

Local/IP cluster preference should be a tie-breaker or boost. It should not
override a much better skill or interest fit.

## GitHub workspace handoff

GitHub setup happens only after a mutual match and explicit approval.

The first safe workflow should be:

1. Team room is created.
2. Server asks which participant will own or create the repo.
3. Repo owner approves GitHub permissions.
4. Server creates or attaches the repo.
5. Server invites the matched teammate or records invite instructions.
6. Server initializes basic workspace docs.
7. BetterHackdays registers the repo as the team-room MCP workspace target.
8. Later BetterHackdays MCP calls read from and write to that repo as the
   durable team workspace.

The system should avoid dangerous automation until permission and ownership
rules are clear.

## Workspace repo as MCP drive connector

The workspace repo is not just a code repository. After mutual match and
permission approval, it becomes the connected drive for the team's BetterHackdays
MCP session.

The main BetterHackdays MCP server owns the Hack Day and team-room state. The
workspace repo owns the durable project state. Agent and CLI calls should use
both:

```text
Agent / CLI
        ↓
BetterHackdays MCP server
        ↓
Team room session state
        ↓
GitHub workspace repo connector
        ↓
Docs, code, tools, skills, traces, and artifacts
```

The team room should store the repo connection metadata:

- GitHub owner and repo name
- default branch
- installation or permission status
- connected participant IDs
- active idea or project direction
- last synced planning snapshot
- allowed write targets
- audit log of server-created changes

The MCP server should then expose team-room tools that operate on this repo,
such as:

- create or update planning docs
- create starter code structure
- add or update agent instructions
- add recommended tool manifests
- add skill extension stubs
- record decisions and planning traces
- summarize current workspace state
- prepare submission artifacts

## Workspace initialization bundle

When the repo is first connected, BetterHackdays should add a small, useful
workspace bundle instead of a large generated dump.

The initial bundle should include:

- `README.md` with team, event, project direction, and quickstart
- `AGENTS.md` with team-specific agent guidelines
- `docs/event-context.md` with normalized event context and source notes
- `docs/team-profile.md` with consented team role and skill summary
- `docs/idea.md` with selected or ranked idea direction
- `docs/process-plan.md` with the timeline and milestones
- `docs/checklist.md` with immediate next actions
- `docs/submission.md` with deadlines and submission requirements
- `.betterhackdays/session.json` with non-secret team-room metadata
- `.betterhackdays/tooling.md` with recommended tools and manual setup steps

Secrets, OAuth tokens, contact details, and private participant data should not
be written into the repo by default.

## Code, tools, and skill extensions

BetterHackdays may also add optional project scaffolding when the team approves
it. This should be explicit and reviewable.

Possible additions:

- lightweight app or API scaffold based on the selected idea
- test skeletons
- `.env.example`
- issue or task list
- MCP tool manifest notes
- connector setup instructions
- agent skill extension stubs
- prompt or command snippets for the team's preferred harnesses

Skill extensions should start as editable files in the repo, not hidden server
state. The goal is for coding agents to see and improve the team's workflow in
the same place as the code.

Suggested skill extension layout:

```text
.betterhackdays/
  session.json
  tooling.md
  skills/
    README.md
    demo-prep.md
    submission-check.md
    judge-alignment.md
```

These files should describe how agents can help this specific team, using this
specific event context, without requiring the main BetterHackdays repo to hold
team-specific instructions.

## Sync model

The main BetterHackdays server should treat the workspace repo as appendable
and reviewable project state.

Recommended rules:

- prefer pull-request or branch-based writes when automation becomes risky
- keep generated docs concise and easy to edit
- never overwrite user edits without detecting drift
- commit generated changes with conventional commit messages
- record what tool created a change and why
- allow the team to disconnect or rotate the workspace repo

The first prototype can use direct commits after explicit approval. Later
versions should support safer branch or pull-request flows.

## Workspace docs to initialize

A new team repo should start with concise files such as:

- `README.md` with project direction and team members
- `docs/team-profile.md`
- `docs/event-context.md`
- `docs/idea.md`
- `docs/process-plan.md`
- `docs/checklist.md`
- `docs/submission.md`
- `.betterhackdays/session.json`
- `.betterhackdays/tooling.md`
- `AGENTS.md` or equivalent agent instructions

These files make the repo useful for coding agents immediately.

## Privacy and safety rules

- Do not expose a participant in matchmaking before profile completion.
- Do not use IP cluster as identity.
- Do not share contact details without explicit consent.
- Do not create or invite users to GitHub repos without explicit permission.
- Do not write secrets, tokens, or private contact data into workspace repos.
- Do not overwrite participant-authored repo files without drift checks.
- Do not let admin or organizer actions happen through MCP without clear auth.
- Keep sensitive profile fields scoped to the Hack Day unless the user opts in.

## Open questions

- How does an organizer authenticate to create or wake a Hack Day?
- Should each Hack Day have a human-readable code, URL slug, or both?
- Should Hack Day endpoints be isolated by path, token, subdomain, or database row?
- What is the first notification mechanism: polling, webhook, email, or CLI loop?
- What GitHub permissions are required for the first safe repo handoff?
- Should repo writes happen directly, through branches, or through pull requests?
- Which files belong in the first workspace initialization bundle?
- How long should Hack Day session data live after the event ends?
