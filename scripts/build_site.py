"""Render the generated reference blocks of the hack.knowb.run docs site.

The page at site/index.html is written by hand, except for the blocks between
``<!-- BEGIN GENERATED:name -->`` and ``<!-- END GENERATED:name -->`` markers.
Those blocks are rendered here from the code that actually serves the
connector, so the manual cannot drift from the tools it documents:

- ``rfps``: approved public RFPs and live public projects (connector-only
  entries never appear).
- ``requests``: the contributor request types the connector accepts.
- ``tools``: every MCP tool registered by ``app.mcp_server``.
- ``rest``: every REST route served by ``app.main``.

Usage::

    python scripts/build_site.py          # rewrite site/index.html in place
    python scripts/build_site.py --check  # exit 1 if the page is stale
"""
from __future__ import annotations

import argparse
import html
import inspect
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SITE_INDEX = ROOT / "site" / "index.html"
REPO_URL = "https://github.com/knowb-ai/BetterHackdays"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tool groups in manual order. A registered tool missing from every group is
# rendered under "Unsorted" and fails the docs test, so new tools get placed.
TOOL_GROUPS: list[tuple[str, str, list[str]]] = [
    (
        "explore",
        "Explore RFPs",
        [
            "list_project_rfps",
            "search_project_rfps",
            "read_project_rfp",
            "compare_project_rfps",
        ],
    ),
    (
        "design",
        "Public design resources",
        ["list_design_resources", "search_design_resources", "read_design_resource"],
    ),
    (
        "ideas",
        "Refine ideas",
        ["fetch_idea_catalogue", "qualify_idea", "propose_idea_catalogue_addition"],
    ),
    (
        "requests",
        "Contributor requests",
        [
            "preview_contributor_request",
            "submit_contributor_request",
            "list_contributor_requests",
        ],
    ),
    (
        "guards",
        "Permission guards",
        ["authorize_github_mutation", "grant_repository_access"],
    ),
    (
        "hackday",
        "Hack Day room",
        [
            "connect_harness",
            "update_profile",
            "start_survey",
            "answer_survey",
            "get_survey_state",
            "get_match_cards",
            "like_profile",
            "pass_profile",
            "get_matches",
            "ingest_event_text",
            "rank_idea_suggestions",
            "generate_process_timeline",
            "generate_prep_checklist",
            "resolve_slug",
        ],
    ),
]

# Tools that write, or that only ever preview a write, get a badge.
WRITE_TOOLS = {
    "propose_idea_catalogue_addition": "Writes with review",
    "submit_contributor_request": "Verified identity",
    "list_contributor_requests": "Verified identity",
    "authorize_github_mutation": "Verified identity",
    "grant_repository_access": "Preview only",
}

REQUEST_TYPE_DETAILS: dict[str, tuple[str, str]] = {
    "refinement_draft": (
        "Suggest sharper scope, outcomes, or safety notes for an existing RFP brief.",
        "Read or higher",
    ),
    "expression_of_interest": (
        "Tell the maintainers you want to work on an RFP, with no access asked for.",
        "Read or higher",
    ),
    "contribution_access_request": (
        "Ask to be considered for contributor access to the project behind an RFP.",
        "Read or higher",
    ),
    "work_elevation_request": (
        "Ask for elevated work on a project you already contribute to.",
        "Write, maintain, or admin",
    ),
}

REST_GROUPS: list[tuple[str, str, tuple[str, ...]]] = [
    ("RFPs", "rfps", ("/rfps",)),
    ("Design resources", "design", ("/design-resources",)),
    ("Ideas", "ideas", ("/ideas",)),
    ("Contributor requests", "requests", ("/contributor",)),
    (
        "Hack Day room",
        "hackday",
        (
            "/health",
            "/connect",
            "/profile",
            "/event",
            "/planner",
            "/slug",
            "/matchmaking",
            "/matches",
            "/survey",
        ),
    ),
]

HIDDEN_PARAMS = {"auth_context"}

MARKER_RE = re.compile(
    r"(<!-- BEGIN GENERATED:(?P<name>[a-z]+) -->\n)(?P<body>.*?)(\s*<!-- END GENERATED:(?P=name) -->)",
    re.DOTALL,
)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _annotation(param: inspect.Parameter) -> str:
    ann = param.annotation
    if ann is inspect.Parameter.empty:
        return ""
    if isinstance(ann, str):
        return ann
    return getattr(ann, "__name__", str(ann))


def format_signature(name: str, func: Callable[..., Any]) -> str:
    parts = []
    for param in inspect.signature(func).parameters.values():
        if param.name in HIDDEN_PARAMS or param.kind is inspect.Parameter.VAR_KEYWORD:
            continue
        piece = f'<span class="sig-p">{esc(param.name)}</span>'
        ann = _annotation(param)
        if ann:
            piece += f': <span class="sig-t">{esc(ann)}</span>'
        if param.default is not inspect.Parameter.empty:
            piece += f' = <span class="sig-d">{esc(repr(param.default))}</span>'
        parts.append(piece)
    return f'<span class="sig-n">{esc(name)}</span>({", ".join(parts)})'


def grouped_tools() -> list[tuple[str, str, list[str]]]:
    from app import mcp_tools

    registered = list(mcp_tools.MCP_TOOLS)
    placed = {name for _, _, names in TOOL_GROUPS for name in names}
    groups = [
        (key, title, [n for n in names if n in mcp_tools.MCP_TOOLS])
        for key, title, names in TOOL_GROUPS
    ]
    unsorted = [n for n in registered if n not in placed]
    if unsorted:
        groups.append(("unsorted", "Unsorted", unsorted))
    return groups


def render_tools() -> str:
    from app import mcp_server, mcp_tools

    lines = [
        f'<p class="ref-count"><strong>{len(mcp_tools.MCP_TOOLS)}</strong> tools registered by '
        f'<code>{esc(mcp_server.SERVER_NAME)}</code>.</p>'
    ]
    for key, title, names in grouped_tools():
        lines.append(f'<h4 class="ref-group" id="tools-{key}">{esc(title)}</h4>')
        lines.append('<div class="ref-list">')
        for name in names:
            func = mcp_tools.MCP_TOOLS[name]
            desc = mcp_server.TOOL_DESCRIPTIONS.get(name, name.replace("_", " "))
            badge = WRITE_TOOLS.get(name)
            badge_html = f' <span class="badge">{esc(badge)}</span>' if badge else ""
            lines.append(
                f'<article class="ref-item" id="tool-{esc(name)}" data-search="{esc(name)} {esc(desc)}">'
                f'<h5><a class="anchor" href="#tool-{esc(name)}" aria-label="Link to {esc(name)}">#</a>'
                f"<code>{esc(name)}</code>{badge_html}</h5>"
                f"<p>{esc(desc)}</p>"
                f'<pre class="sig"><code>{format_signature(name, func)}</code></pre>'
                "</article>"
            )
        lines.append("</div>")
    return "\n".join(lines)


def _route_auth(route: Any) -> bool:
    for dep in route.dependant.dependencies:
        call = getattr(dep, "call", None)
        if call is not None and call.__name__.startswith("_request_auth_context"):
            return True
    return False


def render_rest() -> str:
    from fastapi.routing import APIRoute

    from app.main import app

    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    rows: dict[str, list[str]] = {key: [] for _, key, _ in REST_GROUPS}
    rows["other"] = []
    for route in routes:
        key = "other"
        for _, group_key, prefixes in REST_GROUPS:
            if any(route.path == p or route.path.startswith(p + "/") for p in prefixes):
                key = group_key
                break
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            auth = (
                '<span class="badge">Bearer token</span>' if _route_auth(route) else ""
            )
            slug = re.sub(r"[^a-z0-9]+", "-", route.path.lower()).strip("-") or "root"
            rows[key].append(
                f'<tr id="route-{esc(method.lower())}-{esc(slug)}" data-search="{esc(method)} {esc(route.path)}">'
                f'<td><span class="verb verb-{esc(method.lower())}">{esc(method)}</span></td>'
                f"<td><code>{esc(route.path)}</code></td>"
                f"<td>{auth}</td></tr>"
            )
    lines = [
        f'<p class="ref-count"><strong>{len(routes)}</strong> routes served by '
        "<code>app.main:app</code>. Interactive docs run at <code>/docs</code> on any local server.</p>"
    ]
    groups = list(REST_GROUPS) + [("Other", "other", ())]
    for title, key, _ in groups:
        if not rows[key]:
            continue
        lines.append(f'<h4 class="ref-group" id="rest-{key}">{esc(title)}</h4>')
        lines.append(
            '<div class="table-wrap"><table class="ref-table"><thead><tr>'
            '<th scope="col">Method</th><th scope="col">Path</th><th scope="col">Auth</th>'
            "</tr></thead><tbody>"
        )
        lines.extend(rows[key])
        lines.append("</tbody></table></div>")
    return "\n".join(lines)


def public_rfps() -> list[dict[str, Any]]:
    from app import rfp_connector

    entries = []
    for rfp in rfp_connector.WEBSITE_RFPS.values():
        if rfp.get("visibility") == "public_website" and rfp.get("listed_on_website"):
            entries.append(
                {"id": rfp["rfp_id"], "title": rfp["title"], "tags": rfp["tags"],
                 "summary": rfp["summary"], "kind": "Website RFP"}
            )
    for rfp in rfp_connector.LIVE_PUBLIC_PROJECT_TEMPLATES.values():
        entries.append(
            {"id": rfp["rfp_id"], "title": rfp["title"], "tags": rfp["tags"],
             "summary": rfp["curated_summary"], "kind": "Live project"}
        )
    return entries


def render_rfps() -> str:
    lines = ['<ol class="board" aria-label="Approved public RFPs">']
    for i, rfp in enumerate(public_rfps(), start=1):
        live = rfp["kind"] == "Live project"
        tags = "".join(f"<li>{esc(t)}</li>" for t in rfp["tags"][:3])
        lines.append(
            f'<li class="board-row{" is-live" if live else ""}" id="rfp-{esc(rfp["id"])}" data-search="{esc(rfp["title"])} {esc(" ".join(rfp["tags"]))}">'
            f'<span class="board-no">{i:02d}</span>'
            f'<span class="board-title">{esc(rfp["title"])}</span>'
            f'<code class="board-id">{esc(rfp["id"])}</code>'
            f'<span class="board-kind"><span class="led" aria-hidden="true"></span>{esc(rfp["kind"])}</span>'
            f'<ul class="board-tags">{tags}</ul>'
            f'<p class="board-summary">{esc(rfp["summary"])}</p>'
            "</li>"
        )
    lines.append("</ol>")
    return "\n".join(lines)


def render_requests() -> str:
    from app import rfp_connector

    lines = [
        '<div class="table-wrap"><table class="ref-table req-table"><thead><tr>'
        '<th scope="col">Request type</th><th scope="col">Use it to</th>'
        '<th scope="col">Requester needs on BetterHackdays</th></tr></thead><tbody>'
    ]
    for key, label in rfp_connector.ALLOWED_CONTRIBUTOR_REQUEST_TYPES.items():
        purpose, permission = REQUEST_TYPE_DETAILS.get(key, ("Undocumented.", "Undocumented"))
        lines.append(
            f'<tr id="request-{esc(key)}" data-search="{esc(label)} {esc(key)}">'
            f"<td><strong>{esc(label)}</strong><br><code>{esc(key)}</code></td>"
            f"<td>{esc(purpose)}</td><td>{esc(permission)}</td></tr>"
        )
    lines.append("</tbody></table></div>")
    return "\n".join(lines)


RENDERERS: dict[str, Callable[[], str]] = {
    "rfps": render_rfps,
    "requests": render_requests,
    "tools": render_tools,
    "rest": render_rest,
}


def render_page(source: str) -> str:
    seen: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name not in RENDERERS:
            raise KeyError(f"Unknown generated block: {name}")
        seen.add(name)
        return match.group(1) + RENDERERS[name]() + match.group(4)

    rendered = MARKER_RE.sub(replace, source)
    missing = set(RENDERERS) - seen
    if missing:
        raise KeyError(f"site/index.html is missing generated blocks: {sorted(missing)}")
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if site/index.html is stale")
    args = parser.parse_args(argv)

    source = SITE_INDEX.read_text(encoding="utf-8")
    rendered = render_page(source)
    if args.check:
        if rendered != source:
            print("site/index.html is stale. Run: python scripts/build_site.py", file=sys.stderr)
            return 1
        print("site/index.html is up to date.")
        return 0
    if rendered != source:
        SITE_INDEX.write_text(rendered, encoding="utf-8")
        print("Rewrote site/index.html.")
    else:
        print("site/index.html already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
