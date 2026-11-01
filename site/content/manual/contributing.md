+++
title = "Contributing"
weight = 110
+++

BetterHackdays is developed in the open at [knowb-ai/BetterHackdays](https://github.com/knowb-ai/BetterHackdays). Issues and small, reviewable pull requests are welcome.

<div class="ticks">

- Run the test suite before you open a pull request: `.venv/bin/python -m unittest discover -s tests -v`.
- If you change `README.md`, `agents.md`, or `docs/*.md`, update their OKF checksums and run `python scripts/validate_okf.py`.
- If you change the connector's tools or routes, run `python scripts/build_site.py` so this manual stays in step.
- Use conventional commit prefixes: `feat:`, `fix:`, `chore:`.
- Read [agents.md](https://github.com/knowb-ai/BetterHackdays/blob/main/agents.md) if an agent is working with you.

</div>

{% cards(cols=2) %}
saber :: License :: No license has been declared yet. Until one is, the code is public to read but not licensed for reuse. Ask at [ping@knowb.run](mailto:ping@knowb.run).
ember :: Security :: Found a way around a permission check? Please email [ping@knowb.run](mailto:ping@knowb.run) instead of opening a public issue.
{% end %}
