+++
title = "Configuration"
weight = 80
+++

All settings are environment variables. Copy `.env.example` to `.env` for local runs. Everything is optional for reading.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./betterhackdays.db` | Local store for Hack Day state and private request records. |
| `GITHUB_TOKEN` | unset | Your own GitHub token. Identifies you for submits and lists over MCP. |
| `KENOBI_GITHUB_TOKEN` | unset | Maintainers only: KnowB GitHub App installation token for reviewed writes. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | unset, port `587` | Mail route for requests. Without it, submits return an unsent draft. |
| `APP_NAME` | `betterhackdays-matchmaking` | Title of the REST app. |
| `SEED_PROFILES` | `true` | Seeds demo profiles for the Hack Day room. |
