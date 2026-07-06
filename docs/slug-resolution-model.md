# Slug Resolution Model

## Purpose

Define the first concrete model for resolving Hack Day codes, standalone slugs,
room keywords, and team keywords.

This model turns the room and slug RFC inventory into prototype rules that can
guide CLI, MCP, QR, website, and agent-harness entry points.

## Supported input formats

The first prototype supports four human-entered formats:

```text
<hack-day-code>
<standalone-slug>
<hack-day-code> <room-keyword>
<hack-day-code> <team-keyword>
```

Examples:

```text
daytona
pillow
daytona pillow
daytona apex
```

The parser should normalize whitespace and casing before resolution. It should
not treat punctuation, accents, transliteration, or multilingual aliases as a
first-version requirement.

## Resolution order

Resolution should prefer explicit Hack Day namespaces before global standalone
slugs.

1. If the input has one token, try a Hack Day code.
2. If no active Hack Day code matches, try a globally unique standalone slug.
3. If the input has two tokens, resolve the first token as a Hack Day code.
4. Inside that Hack Day namespace, resolve the second token as a room keyword
   or team keyword.
5. If multiple targets match, return an ambiguous result and ask the caller for
   more context.
6. If no target matches, return a not-found result with safe next actions.

Standalone slugs are allowed only when they are globally unique and unexpired.
Event-prefixed room and team keywords only need to be unique inside the Hack
Day namespace.

## Prototype rules

- Hack Day codes are unique while the Hack Day is active.
- Room and team keywords are unique inside a Hack Day.
- Standalone slugs are globally unique while active.
- Temporary slugs can expire after the Hack Day ends.
- A team-room slug can resolve before a workspace repo exists.
- A team-room slug keeps resolving to the same room after the workspace repo is
  connected.
- Slug identity is separate from IP cluster and co-location hints.
- IP cluster hints may improve discovery or ranking, but never grant access.

## Resolution targets

A resolved input can target one of these objects:

- Hack Day session
- active participant entry
- matchable participant setup
- matched team invite
- team room
- connected workspace repo metadata

The resolver should return a typed target instead of forcing each surface to
infer the meaning of a slug.

## Participant states

The first model distinguishes these participant and room states:

- `active`: the participant connected to the Hack Day but has not completed the
  required profile flow.
- `matchable`: the participant completed the required profile flow and can
  appear in matchmaking.
- `matched`: the participant has a mutual match but the team room is not fully
  set up.
- `room_created`: the team room exists and can hold planning state.
- `workspace_connected`: the team room has an approved connected workspace
  repo.

State transitions should be explicit. A user should not become `matchable`
only because they entered a room keyword. A room should not expose repo
metadata only because a participant shares an IP cluster or scans a QR code.

## Entry point behavior

All entry points should call the same resolver and adapt the response to their
surface.

- CLI: returns a compact summary, next action, and optional confirmation
  prompt.
- MCP: returns structured JSON for agent tools and follow-up calls.
- QR: resolves to a website or deep link that calls the same resolver.
- Website: shows the safe public summary first, then prompts for authentication
  or consent when needed.
- Agent harness: loads the Hack Day or team-room context and asks permission
  before sharing contact details or repo metadata.

## Prototype API

`POST /slug/resolve`

The request passes the raw code or phrase plus the candidate Hack Day state
that the current prototype can search.

```json
{
  "raw_input": "daytona pillow",
  "caller_participant_id": "alice",
  "hack_days": [
    {
      "hack_day_id": "hack_day_1",
      "code": "daytona",
      "name": "Daytona Hack Day",
      "status": "active",
      "participant_states": [
        {"participant_id": "alice", "state": "workspace_connected"}
      ],
      "team_rooms": [
        {
          "room_id": "room_1",
          "keyword": "pillow",
          "join_mode": "invite_only",
          "participant_ids": ["alice"],
          "state": "workspace_connected",
          "workspace_repo": {
            "owner": "team-daytona",
            "repo": "pillow",
            "default_branch": "main",
            "permission_status": "connected",
            "allowed_write_targets": ["README.md", "docs/*.md"],
            "last_synced_planning_snapshot": "2026-07-06T10:00:00Z"
          }
        }
      ]
    }
  ],
  "standalone_slugs": []
}
```

Example response:

```json
{
  "status": "resolved",
  "input": "daytona pillow",
  "normalized_tokens": ["daytona", "pillow"],
  "target_type": "team_room",
  "target_id": "room_1",
  "hack_day_id": "hack_day_1",
  "participant_state": "workspace_connected",
  "room_state": "workspace_connected",
  "safe_summary": "Team room: pillow",
  "next": "open_workspace_repo",
  "workspace_repo": {
    "owner": "team-daytona",
    "repo": "pillow",
    "default_branch": "main",
    "permission_status": "connected",
    "allowed_write_targets": ["README.md", "docs/*.md"],
    "last_synced_planning_snapshot": "2026-07-06T10:00:00Z"
  },
  "required_authorization": [],
  "matches": []
}
```

The same behavior is exposed through the MCP-friendly `resolve_slug` function
in `app.mcp_tools`.

## Prototype data model

```text
HackDay
  id
  code
  name
  status
  starts_at
  ends_at
  expires_at
  event_context_id

SlugAlias
  id
  slug
  namespace_hack_day_id
  target_type
  target_id
  visibility
  join_mode
  expires_at
  created_by_participant_id

ParticipantState
  participant_id
  hack_day_id
  state
  profile_completed_at
  matched_team_room_id

TeamRoom
  id
  hack_day_id
  keyword
  join_mode
  participant_ids
  selected_idea_id
  workspace_connection_id

WorkspaceRepoConnection
  id
  team_room_id
  owner
  repo
  default_branch
  permission_status
  connected_participant_ids
  allowed_write_targets
  last_synced_planning_snapshot

ResolvedSlug
  status
  input
  normalized_tokens
  target_type
  target_id
  hack_day_id
  participant_state
  safe_summary
  next
  workspace_repo
  required_authorization
```

`workspace_repo` is present only when the caller is authorized for the team
room and the room has `workspace_connected` state.

## Workspace repo exposure

A connected workspace repo can expose this metadata to authorized team-room
participants:

- owner
- repo name
- default branch
- permission status
- allowed write targets
- last synced planning snapshot

The resolver must not expose repo metadata to participants who are not
authorized for the team room.

## Security and privacy constraints

- Invite-only rooms require explicit authorization before joining.
- Approval-gated rooms return a request-access next action instead of room
  membership.
- Contact handles are shared only after participant consent.
- Repo metadata is visible only to authorized team-room participants.
- Slug possession alone is not proof of identity.
- QR scans do not bypass authentication, consent, or join-mode rules.
- IP cluster and co-location hints never grant room, slug, or repo access.
- Public summaries should avoid private participant details.
- Secrets, OAuth tokens, and private contact details must not be written into
  workspace repos.

## Non-goals for the first implementation

- Multilingual slug generation.
- Global slug marketplace or reservation UI.
- Automatic GitHub permission changes from slug resolution.
- IP-based authentication.
- Public exposure of private room state.
- Permanent slug reuse policy beyond the event expiration window.
- Full website routing and QR generation.

## Open questions

- Should standalone slugs be disabled for large public events unless explicitly
  reserved?
- What is the default expiration window after a Hack Day ends?
- Which participant identity proof is enough for invite-only room access?
- Should organizers be able to attach an existing standalone slug to an
  official Hack Day after creation?
