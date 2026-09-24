# MCP Server

## Purpose

BetterHackdays MCP is the local bridge between a coworker's agent, its local
HotMem instance, session policy, and shared GitHub work. It creates and manages
sessions, tasks, dependencies, updates, and explicit memory sharing.

The current server still exposes the Hack Day matchmaking and planning tool
layer. Work-session creation, GitHub task coordination, HotMem sharing policy,
peer discovery, and message relay are the accepted direction and are not yet
implemented.

## Current entry point

```bash
.venv/bin/python -m app.mcp_server
```

The current module creates a `FastMCP` server named
`betterhackdays-hack-day`. REST routes and MCP tools share `app.mcp_tools`.
Run behavior and environment requirements are described in
[Development](./development.md).

## Currently registered tools

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

These tools support Hack Day onboarding, matchmaking, and planning. They do not
create a shared work session or connect agents to GitHub or HotMem.

## Target session tools

The first collaboration surface should include:

- `session_create`, `session_get`, `session_join`, and `session_close`;
- `session_inbox` and `session_post_update`;
- `task_list`, `task_create`, `task_update`, and `task_complete`;
- `task_add_dependency`, `task_remove_dependency`, and
  `task_list_dependencies`;
- `memory_share`, `memory_shared_search`, and `memory_revoke`;
- optional `session_discover` for local WLAN discovery.

In the GitHub-only path, `session_create` records the session in a shared
repository. Tasks are GitHub issues, dependency relationships use GitHub's
issue dependency feature, and comments provide durable updates and handoffs.
Agents poll GitHub through `session_inbox`; delivery is asynchronous. GitHub
Projects can provide a board view but are optional. The inbox relay delivers
context when the receiving agent checks it; it does not wake or execute a
remote agent.

Each participant runs BetterHackdays MCP and HotMem locally and authorizes the
server to access the shared repository. A BetterHackdays-hosted service,
hosted HotMem, a separate database, or a message broker is not required for
this path. GitHub identity and repository permissions authorize remote reads
and writes. Use a private repository when session content is not intended to
be public.

## Optional local discovery

On a shared WLAN, `session_discover` may find an advertised BetterHackdays
session endpoint. A participant may also enter a reachable address and port.
Discovery only locates the endpoint. The session still requires explicit
membership approval and policy checks. Direct connections can provide
lower-latency exchange when the endpoint is reachable; GitHub remains the
durable remote relay when an agent is offline.

## HotMem boundary

HotMem stores and retrieves each agent's local memories. BetterHackdays checks
session membership and sharing policy before it relays a selected memory or
returns session context. The sender shares a useful derived item, not an
unfiltered private brain. The receiver can explicitly save the received item
into its own HotMem with the author, source, session, and timestamp preserved.

Revocation blocks future reads through BetterHackdays. It cannot remove a copy
already accepted into another agent's local memory, so tools must show the
audience and sharing scope before a write.

## GitHub write policy

GitHub owns durable task and discussion state in the GitHub-only mode.
BetterHackdays tools should return issue links and structured status for every
write. Mutations must be attributable to an authorized GitHub actor and
reviewable by repository collaborators. The MCP layer must not write secrets,
OAuth tokens, or private contact details to GitHub. It should avoid overwriting
participant-authored files without drift checks.

Hack Day matchmaking remains an optional way to find collaborators and start
a work session. The session, task, dependency, relay, and HotMem sharing tools
also support coworkers who already know one another.
