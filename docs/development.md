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

The connector manual in `site/` is a [Zola](https://www.getzola.org/) site,
published by GitHub Pages to the custom domain https://hack.knowb.run.

- Each section of the one-page manual is a Markdown file in
  `site/content/manual/`, ordered by `weight`. Add a file to add a section.
- Components are shortcodes in `site/templates/shortcodes/`.
- The MCP tool, REST route, public RFP, and request type references render from
  `site/data/reference.json`, generated from the code.

```bash
.venv/bin/python scripts/build_site.py          # refresh site/data/reference.json
.venv/bin/python scripts/build_site.py --check  # fail if it is stale
zola --root site serve                          # preview at 127.0.0.1:1111
```

`tests/test_docs_site.py` checks the sources everywhere, and checks a real build
wherever `zola` is installed, including the Pages workflow. Deployment and
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
