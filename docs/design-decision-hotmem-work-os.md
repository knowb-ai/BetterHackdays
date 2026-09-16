# Design Decision: HotMem-backed Work OS MCP

**Status:** Accepted direction, implementation pending  
**Decision date:** 2026-09-16

## Decision

BetterHackdays will grow from a Hack Day matchmaking and planning service into
a provider-neutral work OS MCP that can be used from OpenAI Codex, Claude Code,
and other compatible coding-agent harnesses.

HotMem will be the local-first memory sidecar. Each workstation runs its own
HotMem instance. BetterHackdays supplies the work-session identity, team-room
membership, tool policy, and sharing boundaries. The sidecar remains the local
source of truth for memory records.

This creates two deliberately separate memory planes:

1. **Private brain:** the agent's solo working memory for the local operator,
   workspace, or harness. It is private by default and never enters a shared
   task context implicitly.
2. **Co-working brain:** a small, task-scoped pool of records explicitly
   promoted for a BetterHackdays team room or work session. It contains only
   context that both co-workers need in order to coordinate the common task.

The product must make the second plane feel like a shared memory pool without
turning the first plane into an accidental data export.

## Why this is the right boundary

The two agents may each have useful private reasoning, preferences, drafts, and
working notes. Most of that is not necessary for the other co-worker and may
include secrets, personal context, or unfinished thinking. The shared pool
should therefore be a curated task context, not a mirror of either agent's
entire memory database.

BetterHackdays already owns Hack Day, team, and workspace state. Extending that
policy layer to memory makes sharing a product decision that is visible to the
participants, rather than an emergent side effect of connecting two harnesses.

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

The ownership model is intentionally simple enough to explain during a live
Hack Day.

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

An agent can search shared memory only while it is authorized for the matching
work session or team room. A shared-memory tool must reject missing, expired,
revoked, or mismatched session policy before querying HotMem.

### 5. Revocation and expiry

The owner or BetterHackdays session owner can revoke a shared record or end the
sharing policy. Revocation must prevent future retrieval and be represented in
the audit trail. Short-lived task context should carry a TTL or review marker so
it does not remain shared forever by accident.

### 6. Conflicts are visible

The first implementation must not claim automatic conflict-free multi-writer
sync. If two co-workers disagree, retain both attributed records, mark the
conflict, and ask for an explicit resolution. A later merge may create a new
record that links to both sources.

## Runtime and harness model

The target topology is:

```text
Codex / Claude Code / other harness
        | MCP stdio adapter
        v
Local HotMem sidecar (SQLite, private and shared namespaces)
        | explicit policy calls
        v
BetterHackdays MCP server (session, membership, sharing rules)
        |
        v
Team room and optional GitHub workspace repo
```

Codex and Claude Code should use small adapters that expose the same logical
operations and record schema. BetterHackdays must not make the work OS depend
on one model vendor or one harness configuration.

HotMem's current local-first runtime, JSONL interchange, provenance, snapshots,
HTTP API, and MCP surface are a good foundation. Hosted memory synchronization,
encryption, signing, and automatic multi-writer conflict resolution remain
future work and are not prerequisites for the first vertical slice.

## Initial tool contract

The first vertical slice should test a narrow set of policy-aware operations:

- `memory_private_add`
- `memory_private_search`
- `memory_share`
- `memory_shared_search`
- `memory_revoke`
- `memory_snapshot`
- `memory_policy`

The public tool names may change, but each operation must include an actor,
namespace or work-session scope, and enough provenance to explain why a record
was returned. Search results should identify whether a record is private or
shared and who owns it.

## BetterHackdays responsibilities

BetterHackdays owns the rules around a common task:

- create and close the work session or team room;
- authenticate or authorize participating harnesses;
- issue and validate session-scoped memory policy;
- keep private and shared namespaces separate;
- record promotion, access, revocation, and conflict events;
- enforce redaction and deny-list rules before shared writes;
- ensure workspace repo writes remain explicit, reviewable, and free of memory
  secrets or private participant data.

HotMem owns local record storage, retrieval, provenance, portability, and
snapshot or hydration mechanics. It should not decide who is allowed into a
BetterHackdays team room.

## Non-goals for the first implementation

- hosted or cloud-synchronized memory as the default;
- copying an entire private brain into a team room;
- invisible prompt injection from a shared pool;
- automatic conflict-free multi-writer replication;
- storing credentials, tokens, or private contact data in HotMem snapshots or
  workspace repositories;
- a native mobile or desktop app requirement;
- enterprise identity, billing, or organization administration.

## Delivery sequence

1. Add a local policy object that binds a HotMem instance to a BetterHackdays
   work-session ID and authorized actors.
2. Implement private add/search and shared promotion/search with a test double
   before connecting multiple live harnesses.
3. Add revocation, TTL, audit events, and redaction checks.
4. Exercise the same contract from Codex and Claude Code adapters.
5. Add explicit snapshot/export and restore flows for handoff or recovery.
6. Validate the end-to-end path with the seeded companion scenario from issue
   #20.

## Open questions

- Should a shared record be readable by both agents immediately after the
  owner promotes it, or require a second participant confirmation for certain
  sensitivity classes?
- Which identity can reliably represent a local operator across Codex and
  Claude Code without leaking provider-specific account identifiers?
- Should the session owner be able to revoke another owner's shared record, or
  only close the entire shared pool?
- What is the smallest useful audit surface for a live Hack Day without turning
  the work OS into an administrative dashboard?
- When HotMem supports an official synchronization protocol, can it preserve
  these scopes and ownership fields unchanged across runtimes?

## Related work

- [Hack Day Session Architecture](./hack-day-session-architecture.md)
- [MCP Server](./mcp-server.md)
- [One-User Validation](./one-user-validation.md)
- [HotMem](https://github.com/KnowGuard-AI/HotMem)
- GitHub issue: [Design the HotMem-backed work OS MCP and memory ownership
  protocol](https://github.com/knowb-ai/BetterHackdays/issues/21)
