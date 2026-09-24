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
- `project_create_or_get`, `project_board_update`, and
  `project_status_publish`;
- `project_memory_capture`, `project_memory_digest_publish`, and
  `project_memory_ingest`;
- `repo_practices_analyze`, `repo_practices_validate`, and
  `repo_practices_propose`;
- `repo_access_check`, `repo_access_request`, and
  `repo_access_grant_for_unblock`;
- `memory_share`, `memory_shared_search`, and `memory_revoke`;
- optional `session_discover` for local WLAN discovery.

In the GitHub-only path, `session_create` creates a private personal-account
repository and private GitHub Project board for new work, or reuses the
resources selected by the owner. The Project is the
primary collaboration view; task cards are GitHub issues, which retain task
details and discussion and hold native dependency links. Project status updates
and issue comments carry digests and task-specific updates. Agents poll GitHub
through `session_inbox`; delivery is asynchronous. The inbox relay delivers
context when the receiving agent checks it; it does not wake or execute a
remote agent.

Each participant runs BetterHackdays MCP and HotMem locally and authorizes the
server to access the shared GitHub resources. A BetterHackdays-hosted service,
hosted HotMem, a separate database, or a message broker is not required for
this path. GitHub identity and repository and Project permissions authorize
remote reads and writes.

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

Project memory is captured locally in HotMem. At configured checkpoints,
BetterHackdays publishes a concise, source-linked digest to Project status
updates, task issue comments, and a dated repository log. Validated repository
practices are proposed in `AGENTS.md` or a working-agreement file through a
reviewable pull request. This does not publish raw HotMem records or private
conversation history.

## Task-triggered access

During session creation, the repository owner can authorize a standing rule
for specifically named coworkers. Before a task becomes actionable for an
assigned coworker, the owner-side agent checks access and, under that rule,
`repo_access_grant_for_unblock` sends the needed invitations without another
owner prompt. If an unexpected block occurs while a session endpoint is
reachable, the blocked coworker's agent sends a task-only
`repo_access_request` through that endpoint. The request does not depend on
access to the private repository that is causing the block. The owner-side
agent verifies identity, task, missing permission, and standing policy before
granting access. Only the blocker, needed resource links, and invitation
status are relayed; private HotMem content is never part of the unblock
message. The task remains pending until both invitations are accepted and
access is active. No admin access is granted. On a personal-account
private repository, collaborator access permits reading and pushing throughout
the repository, including files unrelated to the assigned task. The Project
has a separate access list. The GitHub session issue receives an attributable
audit entry with the task, reason, resources, permission, request route, actor,
and invitation outcome.
Access remains after session close until revoked or its configured expiry.

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
