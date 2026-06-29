# Team Formation and Collaboration RFC

Status: Idea inventory / RFC draft

Decision status: No product decisions made

Purpose: Preserve, structure, and extend the original hackathon follow-up notes
so the group can discuss scope, priority, feasibility, and product direction.

## Source and Interpretation Boundary

This document is not a transcript of the original note.

It is a structured synthesis that includes:

- ideas directly captured from the original note
- normalized wording that groups related ideas together
- inferred implications that make the idea easier to discuss
- additional risks and open questions added for group review

The group should treat every item as discussion material until it is explicitly
accepted, changed, deferred, or removed.

## Summary

BetterHackdays could help hackathon participants find the right team, load the
right event context, and move from "we just met" to "we can build together"
faster.

The existing product direction already treats matchmaking as a core module.
This RFC adds a broader idea inventory around onboarding, profile exchange,
workspace setup, room joining, and agent/MCP context loading. It should not
demote matchmaking to a side feature.

The combined idea is to let event hosts, room creators, teams, and participants
use matchmaking, simple event codes, room keywords, QR codes, websites, IDEs,
CLIs, or agent/MCP flows to find collaborators and start collaboration.

This document is not an implementation plan. It is an inventory of ideas to
support group discussion.

## Problem

Hackathon participants often lose useful building time before they can work
together.

There are two related problems:

- finding the right teammates or team
- getting that team into a work-ready state

The first problem is where the existing BetterHackdays matchmaking direction
comes into play. Participants may arrive alone, join unbalanced groups, miss
good collaborators, or struggle to understand who would be a useful fit.

The second problem starts once people have found or formed a team. A typical
setup flow may require:

- exchanging GitHub usernames
- exchanging Discord, WhatsApp, email, or other contact handles
- spelling names and usernames in a loud venue
- creating a repository
- inviting every participant to the repository
- sharing workspace links
- configuring permissions and privileges
- finding the event rules and judging criteria
- checking the timeline and submission requirements
- agreeing on communication, file sharing, brainstorming, and presentation tools

For a small team of around four people, setup alone can easily cost 10 to 20
minutes before the team is ready to build.

BetterHackdays can treat both team discovery and team setup as product
problems.

## Core Idea

The idea has two equal pillars for group discussion:

- help participants find better teams through matchmaking
- help formed teams become work-ready through onboarding and setup

An event host or room creator can preload context and publish a simple code.

The code can act as:

- a direct invite into an event
- a direct invite into an event room or team
- a matchmaking entry point
- a prefix or namespace for room and team keywords
- an entry point for MCP or Markdown context loading
- a way to show the event information before people start building
- a shortcut for collaboration setup
- a lightweight alternative to manually exchanging many identifiers

Example:

```text
betterhackdays.com daytona pillow
```

In this example, `daytona` could identify the event and `pillow` could identify
a room, team, or temporary invite.

The participant can enter this phrase into a website, prompt, harness, IDE, or
terminal. The app or agent resolves the code, loads event context, and helps the
participant find, join, or continue with the right room or team.

If direct joining is not available yet, the participant should at least see:

- event topic
- room or team topic
- relevant participants
- matching information
- required profile or contact information
- joining state
- next setup steps

## Event Context Preloading

Event hosts should be able to prepare context before or during an event.

The event code can be published through:

- event program website
- event description
- same-day presentation slides
- venue screens
- printed QR codes
- sponsor pages
- organizer announcements

This gives hosts a reason to prepare context before the event starts. The code
becomes useful both for humans and for agents.

Possible event context:

- event name
- theme
- tracks or categories
- sponsors
- rules
- judging criteria
- winning conditions
- allowed tools
- recommended tools
- timeline
- deadlines
- submission requirements
- location or room structure
- optional participant list
- organizer instructions
- setup guidance
- constraints or forbidden approaches

This context can later be used for:

- idea suggestions
- project scoping
- role suggestions
- work distribution
- process guidance
- timeline reminders
- final presentation preparation
- sponsor and judging alignment

The same mechanism should also work on a smaller scale. A room creator could
prepare a room in advance, define a topic, and publish a room keyword.

## Room and Team Keywords

Participants should be able to exchange simple suffix keywords instead of many
different identifiers.

The keywords should be:

- easy to remember
- easy to dictate
- easy to spell
- short
- human-friendly
- usable in a loud event environment

The system should investigate existing approaches for human-readable temporary
codes. A simple English word list or another proven word dictionary may be
enough for early versions.

Possible formats:

```text
<event-code> <room-keyword>
<event-code> <team-keyword>
```

Room and team codes may be temporary because many hackathon rooms and teams do
not need to exist for long.

Open design options:

- expire team or room codes after the event
- expire codes after a fixed time to live
- allow reuse after days or weeks
- make codes unique only inside an event namespace
- make codes globally unique
- let users choose custom keywords
- generate safe random words

Collisions become more important if the system scales to many users or many
events.

## Join Flow

The ideal join flow is short and practical.

Example team invite flow:

1. A participant wants to invite another participant into a team.
2. They say a simple phrase, such as `betterhackdays.com daytona pillow`.
3. The other participant enters or scans the phrase.
4. BetterHackdays resolves the temporary team keyword.
5. The participant joins the team or requests access.
6. The system shows the topic, room, participants, and setup requirements.
7. The participant approves any required profile or contact sharing.
8. The team becomes closer to a work-ready state.

The same flow should work for:

- an event code only
- an event plus room keyword
- an event plus team keyword
- a QR code
- a prompt in an agent harness
- an IDE or CLI command
- a website join page

## Entry Points

The system should not depend on a single surface.

Possible entry points:

- website
- IDE
- agent harness
- terminal CLI
- VS Code extension
- mobile QR code scan
- event landing page
- white-labeled partner page

The same event and room context should be usable across surfaces.

Participants can then decide whether they want to use BetterHackdays from a
browser, coding harness, prompt, terminal, IDE extension, or phone.

## MCP and Markdown Instruction Files

The website can serve a Markdown instruction file for the initial prompt or
agent flow.

The file can include:

- event metadata
- room metadata
- team metadata
- MCP server information
- available tools
- allowed actions
- join instructions
- admin and gate rules
- profile requirements
- setup steps

An agent can check the website, retrieve the Markdown file, load MCP
information, and help the user join the event or room.

The instruction file can be white-labeled or hosted by other event or sponsor
websites.

Example partner-hosted entry point:

```text
daytona.com/berlinhackathon
```

That page could serve or point to BetterHackdays context.

BetterHackdays could also provide a generator for event-specific MCP or
Markdown instruction files, possibly under a BetterHackdays MCP or event
management area.

## Profiles and Contact Sharing

The goal is to reduce the manual contact-information and privilege-sharing
stage.

Instead of exchanging everything manually, participants can maintain a
BetterHackdays profile.

Possible profile fields:

- GitHub username
- email
- Discord handle
- WhatsApp or phone number
- preferred communication tool
- preferred coding tools
- collaboration tools
- skills
- interests
- project preferences
- previous work
- portfolio links
- GitHub repositories
- uploaded CV
- LinkedIn profile
- Xing profile
- authenticated integrations

Users should control what is shared by default.

Room creators may request specific fields for a room. For example:

- Room A requires GitHub username and Discord.
- Room B requires GitHub username and email.
- Room C requires only temporary room participation.

Sharing should be explicit when sensitive fields are involved.

Useful tool and setup categories:

- version control
- repositories
- brainstorming
- communication
- text chat
- small file sharing
- large file sharing, including video files
- media artifact generation
- presentation generation
- screenshots and screencaps

Some tools may be enabled by the user, the room creator, or the event host.

## Tool and Workspace Setup

BetterHackdays could move beyond "join a room" into "be ready to work".

Possible setup targets:

- GitHub repositories
- repository invites
- code workspaces
- IDE environments
- communication channels
- file-sharing spaces
- brainstorming boards
- task boards
- project templates
- presentation tools
- media or artifact generation tools
- screenshot and screencap workflows
- team documentation

The early version should probably avoid dangerous automation. A repo invite
helper or setup checklist may be safer than fully automatic privilege changes.

The long-term goal is to let a participant join an event or room and have the
minimum required workspace, links, and permissions prepared quickly.

## Access Control and Admin Management

Room creators and event hosts may need different join modes.

Possible join modes:

- accept all
- whitelist only
- approval gate
- invite-only
- temporary keyword access
- event-code access
- profile-required access

Possible admin features:

- room creator rights
- event host rights
- granting admin rights to others
- accepting participants
- rejecting participants
- blocking participants
- banning participants
- removing participants from a room
- assigning participants to teams
- moving participants between teams
- controlling enabled tools
- controlling requested profile fields
- managing room or team visibility
- handling late arrivals
- handling no-shows

Some admin actions could be exposed through MCP, but authorization must be
clear before any admin operation is automated.

## Matchmaking

Matchmaking is a core BetterHackdays module.

The open product question is not whether matchmaking matters. It is how much
weight matchmaking should get in the first product slices, and how it should
connect to onboarding, profile exchange, room joining, and workspace setup.

Some participants need help finding the right team. Some teams already exist
and only need fast setup. The product should support both cases without letting
one erase the other.

Simple matching options:

- random team assignment
- manual room joining by keyword
- organizer-created teams
- participants joining whichever team invited them

Advanced matching options:

- skill-based matching
- interest-based matching
- tool-based matching
- idea-based matching
- role balancing
- forced premade groups
- dynamic on-the-fly groups
- hybrid premade teams plus backfill

Important edge cases:

- participants arrive late
- participants leave
- participants drop out
- no-shows
- last-minute participants
- premade teams missing people
- teams needing backfill
- teams needing skill balancing

Participants who want to prepare can share more data for matching.

Possible data sources:

- GitHub repositories
- repository summaries
- tools used in repositories
- skills inferred from repositories
- self-declared skills
- self-declared interests
- jobs or projects mentioned in profiles
- LinkedIn
- Xing
- CV upload

The original idea references Standout.com-style agentic headhunting or
repo-scanning tools where repositories are scanned and summarized to infer
skills and tools.

Those summaries could help with:

- matching
- idea generation
- team role suggestions
- work distribution
- guidance and advice

## Main Product Modules

The idea can be split into three modules. The current repo already has a
matchmaking-centered backend, while this RFC adds more detail around onboarding
and setup. The group should decide whether these modules should be equal
product pillars, or whether one should lead the next milestone.

Each module can be useful alone or combined with the others.

### Matchmaking Module

Purpose:

- find teammates
- find ideas
- form teams
- balance skills
- support organizer-driven team formation
- hand off matched participants into room onboarding and workspace setup

Inputs may include participant profiles, skills, repo summaries, interests,
tool preferences, event context, and sponsor or theme constraints.

### Setup Module

Purpose:

- exchange contact data
- set up workspaces
- set up permissions
- set up repositories
- set up communication channels
- connect tools
- move participants into a work-ready state

Inputs may include event codes, room codes, participant profiles, tool
pre-authentication, and room creator configuration.

### Advisory Module

Purpose:

- process guidance
- hackathon best practices
- standardized hackathon advice
- team role suggestions
- work distribution
- timeline support
- idea refinement
- presentation guidance
- artifact generation guidance

Inputs may include event context, rules, theme, sponsors, judging criteria,
timeline, selected tools, and team composition.

## QR and Mobile Onboarding

QR codes could support:

- joining an event
- joining a room
- joining a team
- loading setup instructions
- loading venue information
- sharing participant or team invite data

The first practical blocker at many physical events is Wi-Fi access. Before a
laptop can be useful, the participant may need the venue Wi-Fi password.

BetterHackdays could explore combining Wi-Fi onboarding with event or team
entry.

Possible flow:

1. Participant scans a QR code with their phone.
2. The phone receives venue Wi-Fi details.
3. The participant joins venue Wi-Fi.
4. BetterHackdays continues the event or team setup flow.
5. The setup is transferred or pushed to the laptop if possible.
6. The participant joins the event and team.
7. Contact sharing, tool setup, and permissions continue through the profile.

Ideal future state:

- one code scan starts the participant setup
- profile and tool permissions are already configured
- very few extra authentications are needed during the event
- very few questions are asked during the event
- the participant can start working quickly

Open question: how securely and practically can Wi-Fi details and setup state
be passed from mobile to laptop?

## White-Label and Partner Hosting

The instruction Markdown or context endpoint does not have to live only on
BetterHackdays.

An event host, sponsor, or partner could host the entry page and point to
BetterHackdays context.

Possible examples:

- event website publishes the event code
- sponsor page embeds the QR code
- partner page serves the initial Markdown instruction file
- BetterHackdays generates the context file and the partner hosts it

This may make the system easier to adopt at real events.

## Long-Term Direction

The idea could evolve into a broader hackathon management platform.

Possible future areas:

- event management
- participant list management
- room management
- team management
- sponsor and theme integration
- judging and rules context
- workspace provisioning
- tool permission management
- matchmaking
- advisory agents
- artifact and presentation support
- reusable collaboration setup outside hackathons

The same approach may be useful for other temporary collaboration scenarios
where a group needs to become work-ready quickly.

## Suggested MVP Options

This section is not a decision. It lists possible first slices.

Matchmaking-first slice:

- keep the current matchmaking loop central
- improve participant profiles for better match quality
- make event context influence match suggestions
- show why a teammate or team is a fit
- define the handoff from a match into room joining or setup

Smallest event-code slice:

- event code creation
- event context Markdown
- public event join page
- room or team keyword
- QR code for event or room
- basic join state

Profile and setup slice:

- participant profile
- GitHub username collection
- manual contact sharing preferences
- team page with members and links
- simple setup checklist

Agent and MCP slice:

- Markdown instruction generator
- MCP metadata in the event context
- prompt-friendly join instructions
- CLI or harness join command

Workspace helper slice:

- GitHub repository invite helper
- communication handle sharing
- shared link collection
- permission checklist

Matchmaking slice:

- self-declared skills
- role suggestions
- simple team balancing
- late-arrival and backfill support
- clear transition from matched team to setup flow

Later platform slice:

- advanced admin management
- repo scanning
- CV or LinkedIn/Xing import
- workspace provisioning
- Wi-Fi and mobile-to-laptop setup

## Non-Goals for an Early Version

The early version should probably not try to solve everything at once.

Possible non-goals:

- full automatic LinkedIn, Xing, or CV scanning
- fully automated cross-tool permission management
- production-grade event management platform
- automatic setup for every possible tool
- advanced moderation
- automatic block or ban actions through MCP
- mobile-to-laptop Wi-Fi handoff across every platform
- complex matchmaking before basic joining works

## Risks and Constraints

Privacy risks:

- profile data can become sensitive
- CV, LinkedIn, Xing, and repository scanning need consent
- contact sharing defaults must be clear
- users need a way to revoke sharing

Security risks:

- repository invites and tool permissions can be dangerous
- admin actions need clear authorization
- block, ban, and grant-admin actions should not be casually automated
- Wi-Fi credentials should not be exposed through public artifacts without care

Product risks:

- too many integrations can make the first version too complex
- event hosts need simple setup or they will not prepare context
- participants need fast value, not long onboarding
- matching should not block teams that only want quick setup

Scale risks:

- temporary codes can collide
- code reuse rules need to be clear
- event namespaces may be needed
- long-lived rooms may need different handling than one-day rooms

## Open Questions

Event and room codes:

- What exact format should event codes use?
- Should codes be URL paths, prompt tokens, QR payloads, or all of them?
- Should team keywords be one word, two words, or custom?
- Should codes be globally unique or only unique within an event?
- How long should codes be reserved?
- Can codes be reused after days or weeks?
- How do we prevent collisions at scale?

Context and MCP:

- What should the Markdown instruction format look like?
- Where should MCP information live?
- Should BetterHackdays host the context?
- Should event hosts be able to white-label the context?
- How much context should be public?
- How does the agent know which actions are allowed?

Profiles and privacy:

- What profile information should exist?
- What is shared by default?
- What always requires explicit consent?
- Can room creators request specific fields?
- Can users override room defaults?
- How are GitHub, Discord, WhatsApp, LinkedIn, Xing, and CV data handled safely?
- How do users revoke access?

Tool setup:

- Which tools should be supported first?
- Should GitHub repository setup be the first integration?
- Should communication setup be manual or automated?
- How do we handle permissions and privilege sharing?
- How do we avoid over-automating dangerous admin actions?

Admin and gates:

- Who can create rooms?
- Who can approve participants?
- Who can grant admin rights?
- Who can block or ban users?
- Should block or ban be available through MCP?
- What audit log is needed?

Matchmaking:

- Is matchmaking the lead product promise, an equal pillar with setup, or a
  module used only in some flows?
- Should matchmaking be event-level or room-level?
- Should matchmaking participation be optional by default for participants and
  events?
- How should the current matchmaking backend stay visible in the broader
  product direction?
- How much data is needed for useful matching?
- Should matching use repo scans, self-declared skills, CVs, LinkedIn/Xing, or
  all of them?
- How should a successful match hand off into profile sharing, room joining,
  and workspace setup?
- How should late arrivals, no-shows, and dropouts be handled?

QR and Wi-Fi:

- Should QR codes represent events, rooms, teams, Wi-Fi credentials, or combined
  setup bundles?
- How should Wi-Fi credentials be protected?
- Can setup be transferred from mobile to laptop?
- Which parts are feasible across platforms?

Group decision:

- Which ideas belong in the BetterHackdays product?
- Which ideas are useful but too large for now?
- Which ideas should become issues?
- Which ideas should be removed or explicitly deferred?
- Should the next milestone be matchmaking-first, setup-first, or a balanced slice?
- What is the first slice worth prototyping?
