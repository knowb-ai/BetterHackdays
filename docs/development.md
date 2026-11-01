# Development

Development on BetterHackdays is code-agent-first unless someone explicitly
asks for manual-only work.

Agents should read `agents.md`, check branch and git status, make small
reviewable changes, run the relevant checks, and keep the OKF contract aligned
when governed knowledge files change.

## Local Runtime

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs are available at:

```text
http://localhost:8000/docs
```

Run the MCP entry point with:

```bash
.venv/bin/python -m app.mcp_server
```

Optional environment values live in `.env.example`.

## Tests

Use the repo virtualenv:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/validate_okf.py
```

The scenario integration test is:

```bash
.venv/bin/python -m unittest tests/test_hackday_scenario_integration.py
```

## Docs Site

The connector manual in `site/` is a static page published to
https://hack.knowb.run by GitHub Pages. Its MCP tool, REST route, public RFP,
and request type references are generated from the code:

```bash
.venv/bin/python scripts/build_site.py          # refresh site/index.html
.venv/bin/python scripts/build_site.py --check  # fail if it is stale
python3 -m http.server -d site 8080             # preview at localhost:8080
```

`tests/test_docs_site.py` runs the same check in the suite. Deployment and
custom domain setup are documented on the page under "Deploying this site".

## OKF Contract

The repo enforces OKF metadata for:

- `README.md`
- `agents.md`
- `docs/*.md`

When those files change, update the matching sidecars and manifests, then run:

```bash
.venv/bin/python scripts/validate_okf.py
```

## Agent Workflow

- Keep changes scoped to the current ticket.
- Prefer route functions and `app.mcp_tools` for integration tests so REST and
  MCP behavior stay aligned.
- Use temporary SQLite databases in tests.
- Do not write secrets, tokens, or private contact details into repo docs or
  generated workspace files.
- Commit with conventional prefixes.
