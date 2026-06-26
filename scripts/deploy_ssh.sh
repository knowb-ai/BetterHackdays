#!/usr/bin/env bash
# Deploy BetterHackdays matchmaking backend into a Daytona Sandbox via SSH.
#
# You already have an SSH command from Daytona, e.g.:
#     ssh <token>@ssh.app.daytona.io
# Pass just the "<token>@ssh.app.daytona.io" target as SSH_HOST (or --ssh-host).
#
# This script does NOT need a Daytona API key. It:
#   1. SSHes into the sandbox
#   2. Clones (or pulls) the repo
#   3. Writes a real .env from secrets in your local shell (never committed)
#   4. Installs deps in a venv
#   5. Restarts uvicorn on port 8000 in the background
#
# The preview URL (e.g. https://8000-<sandbox>.proxy.daytona.work) is whatever
# Daytona already gave you — it proxies port 8000 inside the sandbox.
#
# Usage:
#   SSH_HOST="<token>@ssh.app.daytona.io" ./scripts/deploy_ssh.sh
#   ./scripts/deploy_ssh.sh --ssh-host "<token>@ssh.app.daytona.io"
#
# To override secrets, export them locally first:
#   export DAYTONA_PREVIEW_TOKEN=...   # optional, not required by the app
set -euo pipefail

SSH_HOST="${SSH_HOST:-}"
REPO_URL="${REPO_URL:-https://github.com/knowb-ai/BetterHackdays.git}"
REPO_DIR="${REPO_DIR:-BetterHackdays}"
PORT="${PORT:-8000}"
SSH_OPTS="${SSH_OPTS:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ssh-host) SSH_HOST="$2"; shift 2 ;;
    --repo-url) REPO_URL="$2"; shift 2 ;;
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$SSH_HOST" ]]; then
  echo "error: pass SSH_HOST env var or --ssh-host \"<token>@ssh.app.daytona.io\"" >&2
  exit 2
fi

echo ">> deploying to $SSH_HOST:$PORT  (repo: $REPO_DIR)"

# Run everything inside the sandbox over a single SSH session.
ssh -o StrictHostKeyChecking=accept-new $SSH_OPTS "$SSH_HOST" bash -s <<REMOTE
set -euo pipefail
cd "\$HOME"
if [[ -d "$REPO_DIR/.git" ]]; then
  echo ">> pulling existing $REPO_DIR"
  cd "$REPO_DIR"
  git pull --ff-only
else
  echo ">> cloning $REPO_URL"
  git clone "$REPO_URL" "$REPO_DIR"
  cd "$REPO_DIR"
fi

# Write a real .env from the committed template (no secrets needed for the app,
# but list fields here so you can override them later without editing code).
cat > .env <<'ENV'
APP_NAME=betterhackdays-matchmaking
DATABASE_URL=sqlite:///./betterhackdays.db
RUNTIME_TARGET=daytona-sandbox
SEED_PROFILES=true
ENV

# Fresh venv + deps (fast on redeploys since pip caches).
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# Restart uvicorn: kill any prior instance on $PORT, start fresh in background.
pkill -f "uvicorn app.main:app --host 0.0.0.0 --port $PORT" 2>/dev/null || true
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT \
  > /tmp/bhd_uvicorn.log 2>&1 &
echo ">> uvicorn started (pid \$!), log: /tmp/bhd_uvicorn.log"
sleep 2
echo ">> health check:"
curl -sS "http://127.0.0.1:$PORT/health" || echo "(not up yet — check log)"
echo
REMOTE

echo ">> done. Use your Daytona preview URL for port $PORT, e.g.:"
echo "   https://${PORT}-<sandboxId>.proxy.daytona.work/health"
