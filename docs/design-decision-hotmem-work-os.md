# Design Decision: HotMem-backed Work OS MCP

**Status:** Accepted direction, implementation pending  
**Decision date:** 2026-09-24

## Decision

BetterHackdays will grow from a Hack Day matchmaking and planning service into
a provider-neutral collaboration MCP for coworkers and their coding agents. It
will let agents discover one another, create shared work sessions, coordinate
tasks, and exchange explicitly shared work from compatible harnesses such as
Codex and Claude Code.

HotMem is each agent's local digital brain. Each workstation runs its own
HotMem instance and keeps its private memories there. BetterHackdays supplies
session creation, peer discovery, membership, task coordination, message relay,
and sharing policy. A coworker's agent receives only explicitly shared,
session-scoped items and can save those items into its own HotMem with
provenance.

This creates two deliberately separate memory planes:

1. **Private brain:** the agent's solo working memory for the local operator,
   workspace, or harness. It is private by default and never enters a shared
   task context implicitly.
2. **Co-working brain:** a small, task-scoped pool of records explicitly
   promoted for a BetterHackdays work session. It contains only
   context that both co-workers need in order to coordinate the common task.

The product must make shared work feel continuous across agents without
turning either private brain into an accidental data export. Shared records
are durable in GitHub for the GitHub-only path; an authorized receiver may
copy them into its own HotMem with source and session provenance.

## GitHub-only collaboration path

GitHub is the only required external service for persistent, remote
collaboration. The first useful deployment should not require a BetterHackdays
cloud service, hosted HotMem, a separate database, or a message broker. Each
agent runs BetterHackdays MCP and HotMem locally and connects to a shared GitHub
repository with its own authorized GitHub identity.

In this mode:

- a new project starts in a private repository owned by the initiating
  coworker's personal GitHub account, with a private GitHub Project board;
- the Project board is the team's primary work view, with status, owner,
  priority, due date, and blocked state;
- each task is a GitHub issue added to that Project, so the task has a durable
  record and native issue dependency links can capture blocked-by relationships;
- a session is created through BetterHackdays MCP and linked to the Project and
  repository;
- GitHub comments on the session and task issues carry attributed updates,
  decisions, and handoff notes;
- agents poll or refresh the GitHub session inbox to receive updates;
- HotMem retains local project memory, and checkpoint digests publish selected
  project context to the Project and repository;
- repo authorization and each actor's GitHub identity gate reads and writes;
- before an issue-backed task becomes actionable, the owner's agent checks
  the assigned named coworker's access and grants missing access under the
  session owner's standing policy.

An existing repository or Project may be selected instead of creating new
ones. BetterHackdays must not change an existing resource's owner or visibility
as a side effect of joining a session.

This is durable asynchronous relay. It does not promise instant delivery: an
agent sees a remote update when its MCP inbox next checks GitHub. The relay
does not wake or execute the other agent. GitHub Actions or webhooks may later
improve wake-up behavior, but are not required for the first path.

## Local discovery and direct sessions

Agents on the same WLAN may advertise a BetterHackdays session endpoint for
local discovery. A participant may also join by entering a reachable session
address and port. Discovery only locates an endpoint; it does not authenticate
the peer or grant access. The session owner still approves membership and
sharing policy.

The direct path supports low-latency exchange while peers can reach one
another. It is an optional transport alongside GitHub relay, not the only way
to collaborate. A session port that is not reachable across a network boundary
cannot provide remote connectivity by itself.

## Shared work model

GitHub holds durable, reviewable coordination state. HotMem holds each agent's
local project memory. BetterHackdays MCP connects them through explicit
session tools:

- create, inspect, join, and close a work session;
- list, create, update, and complete session tasks;
- add, remove, and inspect task dependencies;
- post and retrieve session messages or handoff notes;
- promote a selected HotMem item into the session and save an authorized
  received item into local HotMem.

The Project board is the shared work cockpit. Issues remain the canonical task
records for discussion, ownership, and dependency links. Board fields and
views organize those same issues by status, priority, owner, due date, and
blocker state. The tools must return stable Project and issue references,
actor identity, timestamps, and provenance.

## Project memory and GitHub digests

Each agent records useful project facts, decisions, constraints, lessons, and
open questions in a local project-scoped HotMem namespace. Personal memories
and raw agent conversations remain private. At task completion, a merged pull
request, a session checkpoint, or session close, BetterHackdays can produce a
concise digest from eligible project memories.

The digest has distinct GitHub destinations:

- Project status updates show the current summary, progress, blockers, and
  next actions;
- task issue comments record work specific to that task;
- a repository project log preserves dated decisions, lessons, and links;
- accepted coding practices live in `AGENTS.md` or a focused working-agreement
  document;
- code changes remain normal branches and pull requests with Git history.

The session owner sets which project-memory categories may be published. Each
digest includes source links, dates, and the publishing agent. It excludes
private memories, raw transcripts, credentials, and unrelated personal
context. A receiver may later ingest the published digest into its own local
HotMem. BetterHackdays does not synchronize either agent's entire brain.

## Repository practice loop

When a repository is attached and when meaningful code or CI changes land, the
agent reviews the repository's `AGENTS.md`, README, build and dependency files,
formatters, linters, tests, CI workflows, and relevant merged pull requests.
It builds an evidence-linked practice profile covering the architecture,
commands, style, testing expectations, and contribution workflow.

The agent uses that profile to plan and validate work, then checks whether
reviews, CI results, and later changes confirm or contradict its assumptions.
It labels observed rules separately from inferred conventions. Durable shared
practice updates are proposed in `AGENTS.md` or a working-agreement document
through a reviewable pull request; they do not silently rewrite the repository
policy.

## Why this is the right boundary

The two agents may each have useful private reasoning, preferences, drafts, and
working notes. Most of that is not necessary for the other co-worker and may
include secrets, personal context, or unfinished thinking. Shared session
records should therefore be a curated task context, not a mirror of either
agent's entire memory database. GitHub is the shared durable record in the
GitHub-only mode; HotMem does not provide cross-workstation synchronization.

BetterHackdays owns work-session membership and sharing policy. This makes
sharing a visible product decision rather than an emergent side effect of
connecting two harnesses.

## Memory scopes

Every memory record must carry a scope and an owner. The first implementation
should use stable, inspectable namespaces such as:

```text
private/<operator-id>/<workspace-id>
shared/<work-session-id>
```

The exact identifier format may change, but the invariants do not:

- private records are readable and writable only by the owning local agent;
- shared records are readable only to participants authorized for that work
  session;
- a record is never shared merely because another harness is connected;
- workspace, room, and session identifiers are not permission by themselves;
  BetterHackdays must validate membership and policy first;
- secrets, OAuth tokens, private contact details, and raw credentials are never
  eligible for promotion into the shared pool.

## Ownership protocol

The ownership model is simple enough to explain during a work session.
### 1. Private by default

An agent may write to and search its own private namespace. Private records are
not included in shared search results, snapshots, prompts, or workspace repo
files unless the owner explicitly promotes a derived record.

### 2. Explicit promotion

A co-worker may propose a record for sharing, but promotion requires an explicit
share action through the BetterHackdays policy layer. The action records:

- source memory ID and source namespace;
- shared work-session ID;
- promoting agent and actor identity;
- intended audience;
- sensitivity classification;
- provenance and creation timestamp;
- expiry or review time when the context is temporary.

The shared record should contain the minimum useful statement, not an automatic
dump of the source record or surrounding private context.

### 3. Shared records have an accountable owner

The promoting agent remains the owner of the shared record unless ownership is
explicitly transferred. Other participants may suggest edits or add a linked
follow-up, but they must not silently overwrite the original. Updates should be
append-only or create a new version with provenance and actor metadata.

### 4. Reads are session-scoped

An agent can retrieve shared session records only while it is authorized for
the matching work session. A shared-memory tool must reject missing, expired,
revoked, or mismatched session policy before querying GitHub or local HotMem.

### 5. Revocation and expiry

The owner or BetterHackdays session owner can revoke a shared record or end the
sharing policy. Revocation must prevent future retrieval through BetterHackdays
and be represented in the audit trail. It cannot erase copies a recipient
already saved into a separate system. Short-lived task context should carry a
TTL or review marker so it does not remain shared forever by accident.

### 6. Conflicts are visible

The first implementation must not claim automatic conflict-free multi-writer
sync. If two co-workers disagree, retain both attributed records, mark the
conflict, and ask for an explicit resolution. A later merge may create a new
record that links to both sources.

## Runtime and harness model

The target topology is:

```text
Codex / Claude Code / other harness
        | local MCP
        +------> HotMem (private local memory)
        |
        +------> BetterHackdays MCP
                    | session policy and task tools
                    +------> GitHub Issues / dependency links / comments
                    +------> GitHub Project board / status updates
                    +------> optional WLAN session endpoint
```

Codex and Claude Code should use small adapters that expose the same logical
operations and record schema. BetterHackdays must not make the work OS depend
on one model vendor or one harness configuration.

HotMem's current local-first runtime, JSONL interchange, provenance, snapshots,
HTTP API, and MCP surface are a good foundation. HotMem does not need to
synchronize whole brains for this design: BetterHackdays relays selected work
through GitHub or a direct session, and each receiving agent writes accepted
items locally. Hosted memory synchronization, encryption, signing, and
automatic multi-writer conflict resolution remain future work.

## Initial tool contract

The first vertical slice should test a narrow set of session and memory
operations:

- `session_create`
- `session_join`
- `session_get`
- `session_close`
- `task_list`
- `task_create`
- `task_update`
- `task_complete`
- `task_add_dependency`
- `task_remove_dependency`
- `task_list_dependencies`
- `session_post_update`
- `session_inbox`
- `project_create_or_get`
- `project_board_update`
- `project_status_publish`
- `project_memory_capture`
- `project_memory_digest_publish`
- `project_memory_ingest`
- `repo_practices_analyze`
- `repo_practices_validate`
- `repo_practices_propose`
- `repo_access_check`
- `repo_access_request`
- `repo_access_grant_for_unblock`
- `memory_private_add`
- `memory_private_search`
- `memory_share`
- `memory_shared_search`
- `memory_revoke`
- `memory_policy`
- `session_discover` (optional local WLAN discovery)

The public tool names may change, but each operation must include an actor,
namespace or work-session scope, and enough provenance to explain why a record
was returned. GitHub mutations must be attributable and reviewable. Search
results should identify whether a record is private or shared and who owns it.

## BetterHackdays responsibilities

BetterHackdays owns the rules around a common task:

- create, join, and close work sessions;
- discover local peers and validate GitHub-backed participant authorization;
- create or reuse the private GitHub Project and repository for a session;
- keep the Project board, issue tasks, and dependency links aligned;
- manage session updates and the task-triggered coworker access flow;
- digest eligible project memory to the Project and repository at checkpoints;
- inspect, validate, and propose updates to repository working practices;
- issue and validate session-scoped memory policy;
- keep private and shared namespaces separate;
- record promotion, access, revocation, and conflict events;
- enforce redaction and deny-list rules before shared writes;
- ensure workspace repo writes remain explicit, reviewable, and free of memory
  secrets or private participant data.

For a new personal-account project, the owner authorizes BetterHackdays once
to create private repositories and Projects and to invite specifically named
session coworkers when they are assigned work that requires access. Before an
issue-backed task becomes actionable, the repository owner's agent checks
GitHub permissions and sends required invitations under the standing policy,
without a per-invitation prompt. For an unexpected block, the coworker's agent
can request access through a reachable BetterHackdays session endpoint; the
request cannot rely on the private repository that the coworker cannot yet
access. Both agents record the task, resources shared, permission level,
request route, actor, and invitation result as an attributable entry on the
GitHub session issue. The unblock notice contains only task-related blocker
details, resource links, and invitation status. It does not stream private
HotMem contents. The task remains pending until the coworker accepts the
invitations and access is active. On a personal private repository,
collaborator access lets the coworker read and push throughout the repository,
including files unrelated to the assigned task. Project access is granted
separately. The owner can review and revoke access. No admin role is granted,
and GitHub invitations must be accepted before access works.

HotMem owns local record storage, retrieval, provenance, portability, and
snapshot or hydration mechanics. GitHub owns the shared Project board, issues,
dependency links, status updates, comments, and repository history in the
GitHub-only mode. BetterHackdays controls which session participants may use
that shared state. HotMem should not decide who is allowed into a
BetterHackdays session.

## Non-goals for the first implementation

- hosted or cloud-synchronized memory as the default;
- a BetterHackdays-hosted coordination service as a requirement for the
  GitHub-only collaboration path;
- streaming personal memory or conversation history to unblock a coworker;
- autonomous changes to code practices without a reviewable repository change;
- copying an entire private brain into a work session;
- invisible prompt injection from shared session context;
- automatic conflict-free multi-writer replication;
- storing credentials, tokens, or private contact data in HotMem snapshots or
  workspace repositories;
- a native mobile or desktop app requirement;
- enterprise identity, billing, or organization administration.

## Delivery sequence

1. Define GitHub Project, private repository, session, issue-task, dependency,
   memory digest, and access-policy contracts.
2. Add session creation and read/join/close MCP operations, including private
   Project and repository setup under the initiating personal account.
3. Add Project board and issue-task tools, including dependency links and
   inbox relay.
4. Add the standing, session-scoped access rule that checks permissions and
   grants the named coworker access before an assigned task becomes actionable.
5. Bind local HotMem project memories to sessions and publish checkpoint
   digests to GitHub under the configured sharing policy.
6. Add repository practice analysis and reviewable working-agreement updates.
7. Add revocation, expiry, audit events, and redaction checks.
8. Add optional WLAN discovery and direct session transport.
9. Exercise the shared contract from two agent harnesses.

## Open questions

- Should a shared record be readable by both agents immediately after the
  owner promotes it, or require a second participant confirmation for certain
  sensitivity classes?
- Which identity can reliably represent a local operator across Codex and
  Claude Code without leaking provider-specific account identifiers?
- Should the session owner be able to revoke another owner's shared record, or
  only close the entire session?
- What is the smallest useful audit surface for a work session without turning
  the work OS into an administrative dashboard?
- Which permission scopes and GitHub authorization mechanism support private
  personal repositories, user-level Projects, and invitations?
- Which GitHub permissions are the minimum needed for session membership,
  task management, and dependency updates?
- How should an agent be notified promptly while keeping polling as the only
  required relay mechanism?
- When HotMem supports an official synchronization protocol, can it preserve
  these scopes and ownership fields unchanged across runtimes?

## Related work

- [Work Session and Hack Day Architecture](./hack-day-session-architecture.md)
- [MCP Server](./mcp-server.md)
- [One-User Validation](./one-user-validation.md)
- [HotMem](https://github.com/KnowGuard-AI/HotMem)
- GitHub issue: [Design the HotMem-backed work OS MCP and memory ownership
  protocol](https://github.com/knowb-ai/BetterHackdays/issues/21)
