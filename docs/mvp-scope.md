# MVP Scope

**Status:** Target scope for the HotMem-backed collaboration pivot. The
session, GitHub Project, memory digest, repository practice, and unblock tools
are not implemented yet.

## First collaboration slice

- Local BetterHackdays MCP and HotMem for each participating agent.
- MCP operations to create, inspect, join, and close a work session.
- GitHub as the only required external service.
- For new work, create a private repository and private GitHub Project under
  the initiating coworker's personal GitHub account by default.
- Allow a session owner to select an existing repository and Project without
  changing their ownership or visibility.
- Use the GitHub Project board as the primary shared work view. Start with
  status, priority, owner, due date, and blocked indicators.
- Represent every trackable task as a GitHub issue added to the Project.
  Issues retain task details and discussion; native issue dependency links
  record blocked-by relationships.
- Let agents create, update, complete, assign, and move tasks through MCP while
  keeping Project fields and issue state aligned.
- Use issue comments for task updates and Project status updates for project
  checkpoints. Agents retrieve remote changes by polling the session inbox.
- Keep project-scoped memories in each agent's local HotMem. At task completion,
  pull request merge, session checkpoint, or session close, publish a concise
  digest to the Project status, relevant issue comments, and a dated repository
  log at `docs/project-log/YYYY-MM.md`.
- Build a code-practice profile from repository instructions, build and
  dependency files, formatter/linter/test configuration, CI, and merged pull
  requests. Recheck it when code review or CI contradicts the profile. Propose
  durable practice updates to `AGENTS.md` or a working-agreement file through a
  reviewable pull request.
- Let the owner authorize a standing session rule for specifically named
  coworkers. Before an issue-backed task becomes actionable for an assignee,
  the repo owner's agent checks access and automatically invites them under
  that rule. If an unexpected block occurs while a session endpoint is
  reachable, the coworker's agent sends a task-only request through that
  endpoint. Do not rely on an inaccessible private repo to carry its own access
  request. Send only the task blocker, needed resource, and invitation status.
- Audit each access grant with the blocked task, GitHub identity, repository
  and Project, granted permission, actor, and invitation outcome in the
  session issue. Grant no admin role. Keep the task pending until the coworker
  accepts GitHub's invitations and access works.
- State clearly that personal-account private-repository access allows the
  coworker to read and push to the whole repo. The unblock message contains
  only task details, resource links, and invitation status. The collaborator
  permission covers the whole repo.
- Keep personal HotMem private during access provisioning. Project digests are
  separately published under the session's configured sharing policy; raw
  memories and conversation histories are never streamed to unblock work.
- A two-agent workflow that creates a session, tracks dependent tasks, shares
  project digests, learns repository practices, grants access under the
  session policy when needed, and continues while an agent is offline.

The Project board is the collaboration cockpit; issues are its durable task
records and dependency links. GitHub Projects supports board, table, and
roadmap views over issues and pull requests. Issues remain useful for task
discussion and native dependency relationships. See [GitHub Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects)
and [issue dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies).

For a personal-account private repository, the collaborator permission
includes write access to the whole repository. The GitHub Project has its own
access list, so BetterHackdays must invite the coworker to both resources.
Invitations are audited and require acceptance. See [personal repository permissions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)
and [Project access](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-access-to-your-projects).

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
- Granting access to identities outside the named session participants.
- Repository or Project admin grants, changing visibility of an existing
  repository or Project, or changing their owners.
- Automatic changes to durable code practices without a reviewable pull
  request.
- Treating WLAN discovery, an issue number, or a session identifier as
  authentication.
- Claims of real-time GitHub relay; agents retrieve remote updates by polling.

## Success criteria

- An agent can create a session with a private personal-account repository and
  a private Project board using the owner's GitHub authorization.
- Two coworkers' agents can see the same issue-backed task board and move work
  through its states.
- A blocked-by dependency is visible to both agents in the Project and issue.
- The owner-side agent checks access before an assigned task becomes
  actionable, then invites named coworkers under the standing policy when
  needed. The task remains pending until access is active, and the unblock
  message contains no private HotMem content.
- Each agent retains local project memory while eligible digests become
  searchable GitHub project and repository history.
- Repository practice profiles cite evidence, adapt to the current codebase,
  and update shared instructions through reviewable pull requests.
- Work remains available in GitHub while either local agent is offline.
- Session close reports access that remains on the Project and repository;
  access remains until the owner revokes it or its configured expiry arrives.
