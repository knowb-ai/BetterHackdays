# BetterHackdays Docs

This folder records the product direction and implementation plans for
BetterHackdays.

## Current direction

- Connect coworkers and their agents through shared work sessions.
- Use HotMem as each agent's private local digital brain.
- Use a private GitHub Project board as the shared work view, backed by Issues
  for tasks and dependencies.
- Use GitHub as the only required external service for project digests, code,
  and remote updates.
- Learn repository practices from its instructions, configuration, CI, and
  reviewed changes, then propose updates through pull requests.
- Create new work under the initiating coworker's personal GitHub account in a
  private repository by default.
- Check named coworkers' access before their assigned tasks become actionable,
  then grant missing access under a standing owner-approved session policy.
  Send only task blocker details, resource links, and invitation status through
  the unblock flow.
- Support optional peer discovery and direct sessions on a local WLAN.
- Keep Hack Day matchmaking and planning as ways to find collaborators and
  prepare work.
- Treat session creation and shared memory operations as explicit MCP actions.

The collaboration pivot is accepted direction, not current implementation. The
running MCP server still exposes the existing Hack Day matchmaking and planning
tools.

## Docs

- [Product Vision](./product-vision.md)
- [Work Session and Hack Day Architecture](./hack-day-session-architecture.md)
- [HotMem Work OS MCP Decision](./design-decision-hotmem-work-os.md)
- [MCP Server](./mcp-server.md)
- [MVP Scope](./mvp-scope.md)
- [Hackathon Playbook](./hackathon-playbook.md)
- [Event Ingest](./event-ingest.md)
- [Event Ingest Schema](./event-ingest-schema.md)
- [Team Formation and Collaboration RFC](./team-formation-and-collaboration-rfc.md)
- [Slug Resolution Model](./slug-resolution-model.md)
- [One-User Validation](./one-user-validation.md)
- [Development](./development.md)
- [Idea Suggestions](./idea-suggestions.md)
- [Process Timeline](./process-timeline.md)
- [Prep Checklist](./prep-checklist.md)
