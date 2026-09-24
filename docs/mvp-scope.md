# MVP Scope

**Status:** Target scope for the HotMem-backed collaboration pivot. The
session, GitHub task, relay, and memory-sharing tools are not implemented yet.

## First collaboration slice

- Local BetterHackdays MCP and HotMem for each participating agent.
- MCP operations to create, inspect, join, and close a work session.
- A shared GitHub repository as the only required external service.
- A GitHub session issue to record purpose, participants, policy, and status.
- GitHub issues as shared tasks, with native dependency relationships for
  blocked work.
- GitHub comments as durable, attributed progress updates and handoff notes.
- MCP tools to list tasks, create and update tasks, manage dependencies, and
  read or post session updates.
- Inbox polling so an agent can retrieve remote changes on its next check.
- Explicit promotion of selected HotMem memories into a session and explicit
  receipt into the other agent's local HotMem with provenance.
- Repository permissions and GitHub actor identity checked before reads and
  writes.
- A private shared repository whenever session content is not intended to be
  public.
- A two-agent workflow that can create a session, coordinate dependent tasks,
  exchange updates, and continue after one agent goes offline.

GitHub Projects boards are optional. The core task list and dependency graph
must work with GitHub issues alone. The GitHub relay is durable and
asynchronous; the first slice does not promise instant delivery.

## Follow-up capability

- Local WLAN peer discovery and direct connections through a reachable session
  address and port.
- Direct delivery for peers that can reach one another, while retaining GitHub
  as the durable shared record.
- Existing Hack Day event ingest, profile setup, matchmaking, idea suggestions,
  and prep planning as optional ways to form a work session.

## Out of scope for the first collaboration slice

- A BetterHackdays-hosted coordination service as a required dependency.
- Hosted or automatically synchronized HotMem brains.
- A separate hosted database, message broker, or notification service.
- Automatic sharing of private memories or full conversation histories.
- Automatic conflict-free multi-writer memory synchronization.
- Silent or non-reviewable GitHub mutations.
- Creating GitHub repositories or granting permissions without participant
  approval.
- Treating WLAN discovery, an issue number, or a session identifier as
  authentication.
- Claims of real-time GitHub relay; agents retrieve remote updates by polling.

## Success criteria

- An agent can create a session from MCP using an authorized GitHub repository.
- Two coworkers' agents can read and update the same task list.
- A blocked-by dependency is visible to both agents.
- Each agent can retrieve attributed updates from the other through GitHub.
- Each agent's private HotMem remains local unless its owner explicitly shares
  a selected item.
- A receiver can save an accepted shared item into local HotMem with its source
  and session provenance intact.
- Work remains available in GitHub while either local agent is offline.
