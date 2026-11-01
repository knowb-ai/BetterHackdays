+++
title = "Quickstart"
weight = 20
+++

You need Python 3.12, Git, and an MCP-capable agent such as Claude Code. Reading RFPs needs no account. Submitting a request needs a GitHub token for *your own* account, because the token is how the connector knows who you are.

<ol class="steps">

{% step(title="Clone and install", id="qs-clone") %}
```bash
git clone https://github.com/knowb-ai/BetterHackdays.git
cd BetterHackdays
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
{% end %}

{% step(title="Connect your agent", id="qs-connect") %}
Pick your client. Run the command from the repository root so the paths resolve.

<div class="tabs" data-tabs><div class="tablist" role="tablist" aria-label="MCP client"><button role="tab" id="tab-cc" aria-controls="panel-cc" aria-selected="true">Claude Code</button><button role="tab" id="tab-json" aria-controls="panel-json" aria-selected="false" tabindex="-1">Any MCP client</button><button role="tab" id="tab-rest" aria-controls="panel-rest" aria-selected="false" tabindex="-1">REST</button></div><div role="tabpanel" id="panel-cc" aria-labelledby="tab-cc">

```bash
claude mcp add betterhackdays \
  -e PYTHONPATH="$PWD" \
  -e DATABASE_URL="sqlite:///$PWD/betterhackdays.db" \
  -- "$PWD/.venv/bin/python" -m app.mcp_server
claude mcp list   # betterhackdays: ... ✔ Connected
```

</div><div role="tabpanel" id="panel-json" aria-labelledby="tab-json" hidden>

```json
{
  "mcpServers": {
    "betterhackdays": {
      "command": "/path/to/BetterHackdays/.venv/bin/python",
      "args": ["-m", "app.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/BetterHackdays",
        "DATABASE_URL": "sqlite:////path/to/BetterHackdays/betterhackdays.db"
      }
    }
  }
}
```

</div><div role="tabpanel" id="panel-rest" aria-labelledby="tab-rest" hidden>

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
# in another terminal
curl -s "http://localhost:8000/rfps/search?q=inbox"
```

{% note() %}Interactive API docs: `http://localhost:8000/docs`.{% end %}

</div></div>
{% end %}

{% step(title="Ask in plain language", id="qs-ask") %}
Your agent picks the right tool. Try:

<div class="prompts">

- “List the KnowB RFPs and group them by theme.”
- “Compare MarkSweep and Subtracktor for a two-person weekend team.”
- “Would a calendar-aware inbox triage idea qualify for the catalogue?”
- “Draft an expression of interest for Underminer and show me the preview.”

</div>
{% end %}

{% step(title="Add your identity, only to send requests", id="qs-identity") %}
Give the server a fine-grained GitHub token for your own account in `GITHUB_TOKEN`. Keep it in your client's local config or a secret manager, never in a repository or a chat message. The connector resolves your login from the token with GitHub; it never accepts a login you type.
{% end %}

</ol>
