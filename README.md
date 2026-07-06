# BetterHackdays - Hack Day Matchmaking Backend

> Join the Hack Day. Find your team. Start building.

BetterHackdays is a Hack Day matchmaking and prep system for coding agents,
CLI users, and IDE harnesses. The current backend lets harnesses such as Warp,
KiloCode, Claude Code, Cursor, Codex, and similar tools connect to a shared
Hack Day, create an anonymous builder profile, browse anonymized match cards,
and like or pass candidates to form mutual matches.

The product direction is a public MCP/API server, deployed on Render by
default, that an organizer can wake up before a hackathon starts. Participants
connect to that live Hack Day endpoint through a CLI or agent harness. Once
their profile is complete, they become matchable for that Hack Day.

Team workspace setup is not fully automated yet. The intended direction is a
post-match team room with explicit GitHub permission before a shared repository
is created or attached.

## Architecture Direction

BetterHackdays should be provider-neutral at the product layer. Render is the
default target for the public server. Other providers can be integrations, but
they should not define the product model.

```
Coding Agent / CLI / IDE Harness
        ↓
BetterHackdays CLI or MCP Client
        ↓
Public BetterHackdays MCP/API Server
        ↓
Render-hosted Backend
        ↓
Hack Day Session State
        ↓
Participants, Profiles, Matchmaking, Rooms
        ↓
GitHub Repo and Workspace Setup
```

See [Hack Day Session Architecture](./docs/hack-day-session-architecture.md)
for the current product model.

## Stack

- Python 3.10+
- FastAPI
- SQLite (stdlib `sqlite3`, list fields stored as JSON strings)
- Pydantic v2
- Uvicorn

No production auth yet. No UI. No LLM matching. No automatic GitHub repo
creation without explicit permission.

## Project structure

betterhackdays/
├── README.md
├── requirements.txt
├── .env.example
├── app/                # backend API and planning logic
│   ├── __init__.py
│   ├── main.py          # FastAPI routes (thin)
│   ├── db.py            # SQLite schema + connection helpers
│   ├── models.py        # Pydantic request/response models
│   ├── seed.py          # Anonymous builder seed data
│   ├── matchmaking.py   # Scoring heuristic, exclusions, match creation
│   ├── survey.py        # Stateful Socratic onboarding survey (8 questions)
│   └── mcp_tools.py     # MCP-friendly function layer (single source of truth)
├── client/             # terminal-side client (runs on each harness)
│   ├── __init__.py      # derives harness_id from git email, calls backend
│   └── __main__.py      # CLI: `python -m client connect | cards | like ...`
└── scripts/
    └── deploy_ssh.sh    # legacy prototype deploy helper
```

## How to run locally

```bash
cd BetterHackdays
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # optional; defaults work without it
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## How to run tests

```bash
.venv/bin/python -m unittest discover -s tests
```

## Render-hosted Hack Day Server

The intended live shape is one public server for a Hack Day.

- The organizer creates or wakes the Hack Day server before the event starts.
- The server exposes a public MCP/API endpoint.
- All harnesses connect to the same Hack Day endpoint.
- A connect request makes the harness an active participant.
- Completing the Socratic profile moves the participant into matchmaking.
- A mutual like creates a match and should lead into team-room setup.
- GitHub repo setup should happen only after explicit permission.

Example local server command before deploying to Render:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
SEED_PROFILES=true .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path                       | Purpose                                            |
|--------|----------------------------|----------------------------------------------------|
| GET    | `/health`                  | Liveness / readiness probe                          |
| POST   | `/connect`                 | Create profile **and start the onboarding survey (returns Q1)** |
| POST   | `/survey/start`            | (Re)start the survey for a harness, returns Q1      |
| POST   | `/survey/answer`           | Record one answer, update profile, return next Q + matches on finish |
| GET    | `/survey/state`            | Peek at current survey progress without advancing   |
| POST   | `/event/ingest/text`       | Normalize pasted hackathon text into event context   |
| POST   | `/planner/ideas`           | Rank concise idea suggestions by event and team fit |
| POST   | `/planner/timeline`        | Generate a deadline-aware Hack Day process timeline |
| POST   | `/profile/update`          | Upsert profile fields (skills, role, vibe, etc.)    |
| GET    | `/matchmaking/cards`       | Anonymized, scored, sorted candidate cards          |
| POST   | `/matchmaking/like`        | Like a candidate; mutual like → match               |
| POST   | `/matchmaking/pass`        | Pass on a candidate                                 |
| GET    | `/matches`                 | All open matches involving a harness                |

### Matching logic

A simple, demo-friendly heuristic (no embeddings, no LLM):

- `+2` for each shared interest
- `+2` if the candidate has a skill the user is `looking_for`
- `+2` if the user has a skill the candidate is `looking_for`
- `+1` if `project_vibe` overlaps
- `-1` if both have the exact same `preferred_role` and neither is looking for
  that role

Each card includes a human-readable `match_reason`. Cards are sorted by
`match_score` descending. The deck excludes self, already-liked, already-passed,
and already-matched profiles. The final `/survey/answer` (when `done=true`)
also returns the top 5 match cards inline by calling this same engine, so the
onboarding loop flows straight into matches without a separate call.

## Socratic onboarding survey

`/connect` no longer just hands back an empty profile — it kicks off a
**stateful 8-question street survey** (the GitCommitted survey) that builds the
profile progressively. Each `POST /survey/answer`:

1. Records the answer
2. Maps it onto profile fields (`skills`, `preferred_role`, `availability`,
   `interests`, `project_vibe`, `looking_for`, `display_label`)
3. Returns the next question and progress (`3/8`, etc.)

The **last answer** sets `done: true` and attaches the top 5 match cards inline.
Answering `No` to the screener (Q1) ends the survey early with `matches: []`.
Survey progress is persisted in SQLite keyed by `harness_id`, so restarted
backends can resume at the next unanswered question. Calling `/connect` or
`/survey/start` intentionally restarts the survey at Q1 for that harness.

The 8 questions cover: screener → event attendance → hardest part of finding
teamates → how you find collaborators today → appeal (1-5) → where you'd use it
→ what builds trust → close + a name to call you.

### Test a live Hack Day endpoint

Set `BASE` to the public Render URL for the active Hack Day server:

```
BASE=https://<betterhackdays-render-service>
```

Run the full loop in one go. The harness id can be derived automatically from
your local `git config user.email` so the raw email is never sent:

```bash
BASE="https://<betterhackdays-render-service>"
HID="harness_$(printf 'betterhackdays:%s' "$(git config --get user.email)" | shasum -a 256 | cut -c1-12)"

curl -s "$BASE/health"   # -> {"status":"ok"}

# 1) /connect -> creates profile, returns Q1
curl -s -X POST "$BASE/connect" -H 'Content-Type: application/json' \
  -d "{\"harness_id\":\"$HID\"}" | jq '.question'

# 2) Answer Q1 (screener; infers skills + role)
curl -s -X POST "$BASE/survey/answer" -H 'Content-Type: application/json' \
  -d "{\"harness_id\":\"$HID\",\"answer\":\"Yes, regularly I code\"}" | jq '{saved, next_question: .next_question.num}'

# 3-8) Repeat for each answer; the 8th returns done=true + matches inline
for ans in "Yes, in the last 6 months" "Finding someone with the right skills" \
           "Discord / Slack" "4" "Hackathons" \
           "verified commits and mutual vibe match" "Yes, call me Zubin"; do
  curl -s -X POST "$BASE/survey/answer" -H 'Content-Type: application/json' \
    -d "{\"harness_id\":\"$HID\",\"answer\":\"$ans\"}" | jq '{done, progress: .next_question.progress, matches: (.matches|length)}'
done

# After the loop, pull the full live deck any time
curl -s "$BASE/matchmaking/cards?harness_id=$HID" | jq '.cards[] | {display_label, match_score, match_reason}'
```

## Terminal client (auto-identity via MCP)

Every harness connects by **invoking MCP on the terminal side** — no manual
`harness_id`, no login, no API key. The `client/` package derives a stable,
anonymous `harness_id` automatically and forwards tool calls to the shared
backend:

1. Reads local `git config user.email`
2. SHA-256 hashes it (with a salt) → `harness_<12hex>`
3. Sends only that hash to `/connect` — the raw email never leaves your machine

Override identity with `$BETTERHACKDAYS_HARNESS_ID` if you need a fixed id.

```bash
export BETTERHACKDAYS_BACKEND_URL=https://<betterhackdays-render-service>

python -m client whoami               # show derived harness_id
python -m client connect              # auto-connect (no args)
python -m client update display_label="AI builder" skills=FastAPI,AI -- preferred_role=product
python -m client cards                # get match cards
python -m client like harness_backend_002
python -m client pass harness_frontend_001
python -m client matches
```

The same functions are importable for a real MCP server:

```python
from client import connect, get_match_cards, like_profile, get_matches
connect()                       # uses derived harness_id automatically
like_profile("harness_backend_002")
```

## Example curl commands

```bash
BASE=http://localhost:8000   # or the active Render Hack Day URL

# Health
curl "$BASE/health"

# Connect a harness (starts the survey, returns Q1)
curl -X POST "$BASE/connect" \
  -H "Content-Type: application/json" \
  -d '{"harness_id":"warp_zubin_001"}'

# Answer the next survey question (advances the loop)
curl -X POST "$BASE/survey/answer" \
  -H "Content-Type: application/json" \
  -d '{"harness_id":"warp_zubin_001","answer":"Yes, regularly I code"}'

# Ingest pasted event text
curl -X POST "$BASE/event/ingest/text" \
  -H "Content-Type: application/json" \
  -d '{
    "source_label":"Event page paste",
    "text":"Event: Agent Sprint Hackathon\nLocation: Berlin\nStart: 2026-07-10 09:00\nEnd: 2026-07-12 18:00\nTracks: AI agents, developer tools\nTeam size: 1-4\nSubmission deadline: 2026-07-12 16:00 via https://example.com/submit\nJudging criteria: Technical execution, demo quality\nSubmission requirements: Repository URL, demo video"
  }'

# Update profile
curl -X POST "$BASE/profile/update" \
  -H "Content-Type: application/json" \
  -d '{
    "harness_id":"warp_zubin_001",
    "display_label":"AI infra/product builder",
    "skills":["product","AI agents","FastAPI"],
    "interests":["developer tools","hackathon infra","agent workspaces"],
    "preferred_role":"product/infra",
    "project_vibe":"ship fast",
    "looking_for":["frontend","backend","GitHub workspace setup"],
    "availability":"full sprint"
  }'

# Get matchmaking cards
curl "$BASE/matchmaking/cards?harness_id=warp_zubin_001"

# Like a candidate (mutual like creates a match)
curl -X POST "$BASE/matchmaking/like" \
  -H "Content-Type: application/json" \
  -d '{"from_harness_id":"warp_zubin_001","to_harness_id":"harness_backend_002"}'

# Pass on a candidate
curl -X POST "$BASE/matchmaking/pass" \
  -H "Content-Type: application/json" \
  -d '{"from_harness_id":"warp_zubin_001","to_harness_id":"harness_frontend_001"}'

# Get matches
curl "$BASE/matches?harness_id=warp_zubin_001"
```

> Tip: to make a like turn into a mutual match, have the seeded builder "like"
> the connecting harness too, e.g. by swapping the IDs:
>
> ```bash
> curl -X POST "$BASE/matchmaking/like" \
>   -H "Content-Type: application/json" \
>   -d '{"from_harness_id":"harness_backend_002","to_harness_id":"warp_zubin_001"}'
> ```

## Seeded profiles

On startup (when `SEED_PROFILES=true`), the backend seeds **10 anonymous
builder profiles**. No real names, emails, or personal data. Only fake
`harness_id` values and archetype labels covering the roles needed for a demo
sprint:

- frontend / demo builder
- backend / API builder
- AI agent builder
- infra / platform builder
- product / storytelling builder
- design / pitch builder
- data / RAG builder
- full-stack builder
- devtools / harness builder
- mobile / demo builder

Re-running startup does **not** overwrite profiles that already exist. Calling
`seed.seed_profiles(force=True)` (e.g. via a script) resets seeded profiles to
their canonical seed values.

## MCP tool abstraction

`app/mcp_tools.py` exposes plain-Python functions that are the **single source
of truth** for all business logic. The FastAPI routes in `app/main.py` are thin
wrappers that validate input and delegate to these functions, so REST and MCP
behavior can never drift.

Functions:

- `connect_harness(harness_id)`
- `update_profile(harness_id, ...)`
- `get_match_cards(harness_id)`
- `like_profile(from_harness_id, to_harness_id)`
- `pass_profile(from_harness_id, to_harness_id)`
- `get_matches(harness_id)`

They always return plain dicts/lists (no Pydantic models), so they can be
registered directly with an MCP server (e.g. `mcp.server.fastmcp.FastMCP`) in a
follow-up work package. A `MCP_TOOLS` registry dict is included for that
purpose.

## Environment

Copy `.env.example` to `.env` (optional; defaults work out of the box):

```ini
APP_NAME=betterhackdays-matchmaking
DATABASE_URL=sqlite:///./betterhackdays.db
RUNTIME_TARGET=render-hack-day
SEED_PROFILES=true
```

## Known limitations

- No production authentication or identity yet. Any `harness_id` is accepted.
- SQLite is single-file; fine for a demo, not for horizontal scale.
- Matching is a tiny keyword heuristic, deliberately not LLM/embedding based.
- No concurrency control beyond SQLite's default locking.
- No persistence migrations; schema is created with `CREATE TABLE IF NOT EXISTS`.
- Seeded profiles are static and not generated from real data.
- Team rooms and GitHub repo setup are documented direction, not implemented.

## Next work package: Hack Day sessions and team rooms

This package currently solves matchmaking, event ingest, and early planning
helpers. The next architecture slice should introduce Hack Day session state:
active participants, matchable participants, local/IP cluster hints, team rooms,
and GitHub repo handoff after mutual match and explicit permission.

The target loop is:

```text
join Hack Day
complete profile
match with teammate
create team room
approve GitHub setup
start building in a shared repo
```
