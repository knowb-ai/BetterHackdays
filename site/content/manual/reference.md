+++
title = "Reference"
weight = 70

[extra]
toc = true
+++

Both references below are rendered from `data/reference.json`, which `scripts/build_site.py` generates from the running code. A test fails if it falls out of date.

### MCP tools {#reference-tools}

{{ tool_reference() }}

### REST API {#reference-rest}

The REST routes call the same functions as the MCP tools. Routes marked <span class="badge">Bearer token</span> read your identity from an `Authorization: Bearer` header and nothing else.

{{ rest_reference() }}
