# Work Session and Hack Day Architecture

## Purpose

Define BetterHackdays as the MCP bridge that lets coworkers and their agents
find one another, create a work session, coordinate shared work, and explicitly
relay useful context between their local HotMem brains.

Hack Day matchmaking remains a supported way to discover collaborators. The
underlying work session also supports coworkers and teams who already know who
they want to work with.

## Core model

Each agent uses its local HotMem instance as its private digital brain.
BetterHackdays owns session identity, participant membership, task operations,
message relay, and sharing policy. GitHub is the durable shared coordination
store for remote sessions that need no BetterHackdays-hosted service.

The first remote path uses one shared GitHub repository:

- a session issue records the session identity, participants, and policy link;
- task issues hold descriptions, owners, status, and discussion;
- GitHub issue dependency links represent blocked-by relationships;
- issue comments hold attributable updates and handoff notes;
- each agent polls the session and task issues for new work;
- accepted shared context may be written into that agent's local HotMem.

The repository's collaborators and GitHub permissions authorize reads and
writes. A session invite or issue number alone does not grant access.

## Architecture

```text
Coworker agent A                         Coworker agent B
  | local MCP                               | local MCP
  +--> HotMem A (private brain)             +--> HotMem B (private brain)
  +--> BetterHackdays MCP                   +--> BetterHackdays MCP
           |                                      |
           +------ GitHub session repo -----------+
                  session issue
                  task issues + dependency links
                  update comments

Optional: local peer discovery and direct session connection over WLAN
```

The first useful deployment runs BetterHackdays MCP and HotMem on each
workstation. GitHub is the only required external service for durable remote
coordination. A hosted BetterHackdays server, hosted memory store, message
broker, and separate database are not prerequisites.

## Session lifecycle

1. An agent calls `session_create` with a shared GitHub repository, a purpose,
   participant identities, and the requested sharing policy.
2. BetterHackdays checks the caller's GitHub access and creates a labeled
   session issue or reports why it cannot.
3. Coworkers join through the GitHub session reference or by discovering a
   reachable local session endpoint. The session owner confirms membership.
4. Agents create tasks as GitHub issues and record dependencies using GitHub's
   issue dependency relationships.
5. Agents post progress, decisions, and handoff notes as attributed issue
   comments. Other agents retrieve updates through `session_inbox`.
6. An agent may explicitly promote a derived HotMem memory into the session.
   The receiving agent can accept it into its own local HotMem with source,
   author, session, and timestamp metadata.
7. A participant or session owner closes the session. The GitHub record and
   tasks remain available according to repository access and retention policy.

Session creation must be an MCP operation. It is not implied by connecting a
harness or discovering a peer.

## Session and task records

The session issue or equivalent GitHub record should identify:

- session ID and purpose;
- shared repository and session owner;
- authorized GitHub participants;
- sharing policy and expiry or review time;
- session status and creation time;
- links to active task issues.

Each task should remain a GitHub issue with a stable issue number, author,
assignee when available, status, and discussion history. Native issue
dependency links should express which tasks are blocked by other tasks. A
GitHub Project board can add a convenient view, but issues and dependency links
are sufficient for the core workflow.

BetterHackdays tools should make the task list and dependency graph easy to
read from an agent, while keeping GitHub as the durable source of truth.
Updates should be idempotent where possible and include the GitHub actor and
source memory or session reference when relevant.

## Discovery and transport

### GitHub relay

GitHub relay supports coworkers on different networks without exposing a local
port or running a BetterHackdays cloud service. Each agent checks the session
issue, task issues, and comments for new updates. Delivery is asynchronous and
depends on the receiving agent polling or otherwise refreshing its inbox. The
relay delivers context; it does not wake or execute the remote agent.

### Local WLAN or reachable session port

Agents on the same WLAN may discover a BetterHackdays endpoint and connect
directly. A coworker may also enter a reachable address and port. This can
provide lower-latency exchange while the endpoint is reachable. Peer discovery
only locates an endpoint; it does not authenticate or authorize a participant.
The GitHub session policy or an explicit owner approval still controls access.

The GitHub path remains available for durable updates when a peer endpoint is
offline. A session port alone does not make a workstation reachable through a
firewall or NAT.

## Memory and sharing boundary

- HotMem stores private working memory locally for each agent.
- BetterHackdays validates session membership and sharing policy before a
  shared-memory read or write.
- Sharing sends a selected, useful statement or artifact reference, not a copy
  of a private brain or an unfiltered conversation history.
- A receiver stores accepted items in its own HotMem with provenance; it does
  not gain access to the sender's private namespace.
- Secrets, credentials, access tokens, and private contact details are not
  eligible for shared memory or GitHub records.
- Revocation prevents future retrieval through BetterHackdays and is recorded
  in the session history. It cannot erase information a recipient already
  copied into a separate system, so the product must show the audience before
  sharing.
- Conflicting updates remain attributed and visible until a coworker resolves
  them. The first version does not claim automatic conflict-free merging.

## MCP contract direction

The first collaboration surface should include:

- `session_create`, `session_get`, `session_join`, and `session_close`;
- `session_inbox` and `session_post_update`;
- `task_list`, `task_create`, `task_update`, and `task_complete`;
- `task_add_dependency`, `task_remove_dependency`, and
  `task_list_dependencies`;
- `memory_share`, `memory_shared_search`, and `memory_revoke`;
- optional `session_discover` for local WLAN discovery.

Every write should be attributable to an authorized GitHub actor or confirmed
local participant. Tools should return issue links and structured status so an
agent can report what changed and identify blocked work.

## Hack Day entry point

Hack Day event ingest, profile setup, idea suggestions, and matchmaking remain
useful discovery and planning features. A mutual match can invite participants
into a BetterHackdays work session backed by a shared GitHub repository. Once
the session exists, the same task, dependency, relay, and HotMem sharing model
applies whether the coworkers met through matchmaking or already knew one
another.
