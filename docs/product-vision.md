# Product Vision

## One-liner

BetterHackdays connects coworkers and their agents in shared work sessions,
using HotMem for each agent's private digital brain and a GitHub Project board
for shared work, backed by issue tasks, dependencies, and repository history.

## Problem

Coworkers and their agents often lose time on:

- finding the right person or agent to collaborate with
- keeping private agent context separate from shared work
- tracking tasks, dependencies, decisions, and handoffs across agents
- losing coordination context when a local session ends
- learning a codebase's conventions before contributing

## Product promise

The system should make it easy to start and sustain shared work:

- discover peers on a local WLAN or join a reachable session address and port
- create and manage a work session from MCP
- keep each agent's private memories in its local HotMem instance
- share selected work explicitly with session participants
- coordinate issue-backed tasks and dependencies on a shared GitHub Project
- relay durable updates through GitHub so remote agents can pick them up
- distill essential local HotMem project memory into GitHub project and repo logs
- inspect and adapt to repository practices as code and CI evolve
- create new work in a private repo under the initiating coworker's personal
  GitHub account by default
- check access before assigned tasks become actionable and automatically
  invite the named coworker under a standing owner-approved session policy;
  relay only task blocker details, needed links, and invitation status
- optionally use Hack Day matchmaking and planning as a way to form a team

## Current architecture direction

BetterHackdays should work as a local MCP bridge first. Each coworker's agent
connects to local HotMem and BetterHackdays MCP. GitHub is the only required
external service for persistent remote coordination; local WLAN discovery and
direct session connections are optional ways to find and reach a nearby peer.

Participants connect through a coding agent or compatible MCP client. An agent
can create a session, invite or admit coworkers, coordinate GitHub issues and
dependencies, and explicitly relay useful work. Hack Day matchmaking remains
available as one way to discover collaborators and start a session. The Project
board is the shared work view; GitHub Issues hold task discussion and dependency
links. Each agent keeps its HotMem locally and publishes only configured,
project-safe digests.

## Core principles

- Quick first result
- Clear and concise UI copy
- Optional depth, never mandatory walls of text
- Useful for coworkers before and during a live event
- Useful for solo builders, pairs, and existing teams
- Agent-friendly CLI and MCP flows
- Owner approval for a bounded session policy that governs memory digests and
  task-triggered access grants
- Auditable GitHub changes, with no admin access granted by the agent

## Current source of truth

- [Hack Day Session Architecture](./hack-day-session-architecture.md)
- [HotMem-backed Work OS MCP Decision](./design-decision-hotmem-work-os.md)
- [MVP Scope](./mvp-scope.md)

## Open questions

- How should agents authenticate local WLAN discovery without treating discovery as trust?
- What is the smallest permission set for task, dependency, and update tools?
- How quickly should agents poll GitHub for new session updates?
- How should HotMem represent a received item while preserving its source and sharing scope?
