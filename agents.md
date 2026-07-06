# Agentic Development Guidelines

This file is the shared working agreement for agents contributing to BetterHackdays.

## Working principles

- Keep changes small, readable, and easy to review.
- Prefer documentation and code that make the next agent faster.
- Preserve the current product direction unless the task explicitly changes it.
- Avoid noisy edits that do not move the work forward.
- Use concise language in repo docs and code comments.

## Commit discipline

- Always save work in commit messages.
- Use conventional commit prefixes:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `chore:` for maintenance, docs, and cleanup
- Keep the summary short and specific.
- Example: `feat: add hackathon prep docs scaffold`

## Current working state

The repo is currently centered on the BetterHackdays matchmaking backend, with a new docs scaffold for the broader hackathon-success product direction.

### Active direction

- Matchmakers and team formation remain part of the product.
- The next layer is preparation for hackathon success.
- The docs now track:
  - product vision
  - hackathon playbook
  - event ingest
  - idea suggestions
  - process timeline
  - MVP scope

### Current repo shape

- `README.md` describes the matchmaking backend.
- `app/` contains the FastAPI service and matchmaking engine.
- `client/` contains the terminal-side client.
- `docs/` now holds the planning stubs for the broader product.

## Agent workflow

- Check the current branch and git status before editing.
- Read the smallest set of relevant files first.
- Make the minimum change needed for the task.
- Keep docs aligned with the actual repo state.
- Keep governed knowledge files aligned with the repo OKF contract in `.okf/manifest.json`.
- When changing `README.md`, `agents.md`, or `docs/*.md`, update the matching OKF sidecar checksums.
- Run `python scripts/validate_okf.py` before handoff when governed knowledge files change.
- Verify the result before handing off.

## Writing rules

- Do not use em dashes as separators or formatting elements.
- Use hyphens for lists and separators.
- Keep headings and instructions direct.
- Favor short paragraphs over long blocks of text.

## Handoff note

If an agent changes behavior, workflow, or repo expectations, update this file in the same change so the next contributor has one source of truth.
