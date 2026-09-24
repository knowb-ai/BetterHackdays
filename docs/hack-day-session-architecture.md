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

The first remote path uses a private personal-account repository and its GitHub
Project board:

- the Project board is the primary shared work view, with status, priority,
  owner, due date, and blocked state;
- each task is a GitHub issue added to the board, with task description,
  assignee, and discussion;
- GitHub issue dependency links represent blocked-by relationships;
- issue comments and Project status updates hold attributable progress and
  handoff notes;
- each agent polls the session and task issues for new work;
- local HotMem retains project memory; checkpoint digests publish selected
  project context to GitHub.

The repository's collaborators and GitHub permissions authorize reads and
writes. A session invite or issue number alone does not grant access.
For work that should remain private, the default is a private repository owned
by the session initiator's personal GitHub account and a private user-level
Project. An existing repository or Project may be reused without changing its
owner or visibility.

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

1. An agent calls `session_create` with a purpose, named coworker identities,
   sharing policy, and either an existing GitHub workspace or a request to
   create one.
2. Under the initiating owner's GitHub authorization, BetterHackdays creates
   or selects the private repository and private Project, then links a session
   record to both.
3. Coworkers join through the GitHub session reference or a reachable local
   session endpoint. The session confirms their GitHub identities.
4. Agents create GitHub issues for tasks, add them to the Project board, and
   record dependencies with GitHub's issue dependency relationships.
5. Agents post task updates as issue comments and publish project checkpoints
   as Project status updates. Coworkers retrieve changes through
   `session_inbox`.
6. Each agent captures useful project memory in its local HotMem. At a task,
   merged-PR, or session checkpoint, the agent publishes an eligible digest to
   the Project and repository log.
7. Before an issue-backed task becomes actionable for an assigned coworker,
   the repository owner's agent checks their access. Under the standing policy,
   it invites the named coworker to the repository and Project when access is
   missing. If an unexpected access block occurs while a session endpoint is
   reachable, the coworker's agent sends a task-only request through that
   endpoint and the owner-side agent checks and grants it under the same rule.
   Only the task blocker, resource links, and invitation status are relayed.
   The task stays pending until GitHub invitations are accepted and access is
   active.
8. A participant or session owner closes the session. The Project, repository,
   task history, and access remain governed by the owner's GitHub settings.

Session creation must be an MCP operation. It is not implied by connecting a
harness or discovering a peer.

## Session and task records

The session record should identify:

- session ID and purpose;
- shared repository, GitHub Project, and session owner;
- authorized GitHub participants;
- sharing policy and expiry or review time;
- standing access-grant policy for specifically named coworkers;
- session status and creation time;
- links to active task issues.

The GitHub Project board is the primary place coworkers review and move shared
work. [GitHub Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects)
can show the same issues in board, table, or roadmap views with fields for
status, priority, owner, and due date. Each task remains a GitHub issue with a
stable issue number, author, assignee when available, and discussion history.
[Issue dependency links](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies)
express which tasks block other tasks, and GitHub shows blocked issues on
Project boards. The board organizes work; the issue is the task record.

BetterHackdays tools should make the board, task list, and dependency graph
easy to read and update from an agent, while keeping GitHub as the durable
source of truth. Updates should be idempotent where possible and include the
GitHub actor and source memory or session reference when relevant.

## Project memory and repo practices

HotMem accumulates project-scoped decisions, constraints, lessons, and open
questions locally for each agent. At task completion, pull request merge,
session checkpoint, or close, the agent creates a short digest under the
session's configured sharing policy:

- Project status updates contain current progress, blockers, and next actions;
- issue comments contain task-specific details;
- `docs/project-log/YYYY-MM.md` keeps dated decisions and lessons;
- `AGENTS.md` or a working-agreement document contains validated code
  practices;
- code changes are committed to branches and reviewed through pull requests.

Digests link back to their source issues or pull requests and omit personal
memories, raw transcripts, and credentials. Coworkers can read published
project information through GitHub access and may ingest it into their own
HotMem. This does not sync either agent's full memory store.

At repository attach and after meaningful code or CI changes, an agent inspects
`AGENTS.md`, README, build and dependency files, format and test configuration,
CI workflows, and relevant merged pull requests. It records observed rules
separately from inferred conventions, uses them to plan and validate work, and
revisits assumptions when review feedback or CI disagrees. Changes to durable
working agreements go through a reviewable pull request.

## Task-triggered coworker access

At session setup, the personal repository owner authorizes a standing rule for
specifically named coworkers. It runs without a prompt for each invitation.
Before a task becomes actionable for an assigned coworker, the repository
owner's agent checks access and sends the required invitations under that
policy. If an unexpected block occurs, the coworker's agent sends an access
request through a reachable BetterHackdays session endpoint; this request
cannot depend on the private GitHub repository because the coworker may not
have access to it yet. The repository owner's agent checks the access failure
and standing policy, then sends the invitation without another owner prompt.
The session audit, recorded as an attributable entry on the GitHub session
issue, records the task, resource, reason, permission, actor, request route,
and invitation outcome. The request and unblock notice contain only
task-related blocker details, needed resource links, and invitation status.
They do not include private HotMem content. The task remains pending until the
coworker accepts the invitations and access is active.

GitHub grants separate access to a personal private repository and its
user-level Project, so both invitations are required. GitHub invitations still
require acceptance. On a personal private repository, the collaborator role
allows read and write access throughout the repository, including pushing
files unrelated to the assigned task. See [personal repository permissions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)
and [Project access](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-access-to-your-projects).
The unblock notice contains only task details, resource links, and invitation
status. GitHub collaborator access covers the repository. BetterHackdays does
not grant repository or Project admin rights.
Owners can revoke access through GitHub at any time. Access persists after a
session closes unless the owner configured an expiry; the session close flow
reports active collaborator access for review.

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
- `project_create_or_get`, `project_board_update`, and
  `project_status_publish`;
- `project_memory_capture`, `project_memory_digest_publish`, and
  `project_memory_ingest`;
- `repo_practices_analyze`, `repo_practices_validate`, and
  `repo_practices_propose`;
- `repo_access_check`, `repo_access_request`, and
  `repo_access_grant_for_unblock`;
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
