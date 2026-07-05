# BetterHackdays — Harness Matchmaking Backend

> Find your team. Spawn your workspace. Start building.

This is the first work package of **BetterHackdays**: a Daytona-native
hackathon coordination system. It implements the **matchmaking layer** — a
shared backend that lets coding harnesses (Warp, Claude Code, Cursor, Codex,
etc.) connect, create an anonymous builder profile, browse anonymized match
cards, and like/pass candidates to form mutual matches.

This package does **not** provision team workspaces yet. That comes in the
next work package, and it will use Daytona to spawn a private team sandbox
only **after** a mutual match is confirmed.

## Why Daytona

BetterHackdays is **Daytona-native**. The matchmaking server itself is
designed to run inside one long-lived **Daytona Sandbox**. All harnesses
connect to the same backend URL exposed by that sandbox — there is not one
sandbox per builder.

**Architecture note:** _The matchmaking server runs in a Daytona Sandbox.
Team workspaces are not created per user. They are created only after mutual
matches, in a later package._

```
Harness / IDE / Agent Client
        ↓
Shared BetterHackdays MCP/API Server
        ↓
Long-lived Daytona Sandbox
        ↓
SQLite / File DB
        ↓
Anonymous Builder Registry
        ↓
Matchmaking Engine
```

## Stack

- Python 3.10+
- FastAPI
- SQLite (stdlib `sqlite3`, list fields stored as JSON strings)
- Pydantic v2
- Uvicorn

No auth. No UI. No LLM matching. No Daytona SDK provisioning in this package.

## Project structure

betterhackdays/
├── README.md
├── requirements.txt
├── .env.example
├── app/                # backend (runs inside Daytona Sandbox)
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
    └── deploy_ssh.sh    # one-shot deploy into a Daytona Sandbox via SSH
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
python3 -m unittest discover -s tests
```

## Running inside Daytona Sandbox

This service is intended to run inside **one long-lived Daytona Sandbox**.

- Create a single Daytona Sandbox and run the FastAPI server inside it
  (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).
- The sandbox exposes the FastAPI service on a stable URL.
- **All harnesses connect to the same backend URL** — there is one shared
  matchmaking server, not one sandbox per builder.
- Every builder is identified by a `harness_id`. Seeded spoof users also use
  fake `harness_id` values (e.g. `harness_backend_002`).
- Future team provisioning will use Daytona to create private team sandboxes
  **only after a mutual match**.

Example inside a Sandbox:

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
Survey state is held in memory keyed by `harness_id`, so a restarted backend
resets in-progress sessions (profiles persist in SQLite).

The 8 questions cover: screener → event attendance → hardest part of finding
teamates → how you find collaborators today → appeal (1-5) → where you'd use it
→ what builds trust → close + a name to call you.

### Test the live service (1-day demo deployment)

The backend is deployed in a Daytona Sandbox and kept alive for ~24h:

```
BASE=https://8000-839f8b4c-960f-4a90-9b60-a431090a7dc6.proxy.daytona.work
```

Run the full loop in one go — the harness id is derived automatically from
your local `git config user.email` (SHA-256, never sent raw), so no login:

```bash
BASE="https://8000-839f8b4c-960f-4a90-9b60-a431090a7dc6.proxy.daytona.work"
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
export BETTERHACKDAYS_BACKEND_URL=https://8000-<sandbox>.proxy.daytona.work

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
BASE=http://localhost:8000   # or the Daytona proxy URL above

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
    "looking_for":["frontend","backend","Daytona sandbox builder"],
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
builder profiles**. No real names, emails, or personal data — only fake
`harness_id` values and archetype labels covering the roles needed for a demo
sprint:

- frontend / demo builder
- backend / API builder
- AI agent builder
- infra / sandbox builder
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

Copy `.env.example` to `.env` (optional — defaults work out of the box):

```ini
APP_NAME=betterhackdays-matchmaking
DATABASE_URL=sqlite:///./betterhackdays.db
RUNTIME_TARGET=daytona-sandbox
SEED_PROFILES=true
```

## Known limitations

- No authentication or identity — any `harness_id` is accepted.
- SQLite is single-file; fine for a demo, not for horizontal scale.
- Matching is a tiny keyword heuristic, deliberately not LLM/embedding based.
- No concurrency control beyond SQLite's default locking.
- No persistence migrations; schema is created with `CREATE TABLE IF NOT EXISTS`.
- Seeded profiles are static and not generated from real data.

## Next work package: Daytona team workspace provisioning

This package only solves matchmaking. The next package will, after a mutual
match, use the Daytona SDK to provision a **private team sandbox** (repo
seeding, shared dev environment) for the matched pair/team — so that "find your
team → spawn your workspace → start building" becomes the full loop.
