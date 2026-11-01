"""Generate the reference data for the hack.knowb.run docs site.

The manual in site/ is a Zola site. Its sections are Markdown files in
site/content/, and its reference tables are rendered by shortcodes from
site/data/reference.json. This script writes that file from the code that
actually serves the connector, so the manual cannot drift from it:

- ``rfps``: approved public RFPs and live public projects (connector-only
  entries never appear).
- ``request_types``: the contributor request types the connector accepts.
- ``tool_groups``: every MCP tool registered by ``app.mcp_server``.
- ``route_groups``: every REST route served by ``app.main``.

Usage::

    python scripts/build_site.py          # rewrite site/data/reference.json
    python scripts/build_site.py --check  # exit 1 if it is stale
"""
from __future__ import annotations

import argparse
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_JSON = ROOT / "site" / "data" / "reference.json"

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


def _annotation(param: inspect.Parameter) -> str:
    ann = param.annotation
    if ann is inspect.Parameter.empty:
        return ""
    if isinstance(ann, str):
        return ann
    return getattr(ann, "__name__", str(ann))


def tool_params(func: Callable[..., Any]) -> list[dict[str, str]]:
    params = []
    for param in inspect.signature(func).parameters.values():
        if param.name in HIDDEN_PARAMS or param.kind is inspect.Parameter.VAR_KEYWORD:
            continue
        default = "" if param.default is inspect.Parameter.empty else repr(param.default)
        params.append({"name": param.name, "type": _annotation(param), "default": default})
    return params


def grouped_tools() -> list[tuple[str, str, list[str]]]:
    from app import mcp_tools

    placed = {name for _, _, names in TOOL_GROUPS for name in names}
    groups = [
        (key, title, [n for n in names if n in mcp_tools.MCP_TOOLS])
        for key, title, names in TOOL_GROUPS
    ]
    unsorted = [n for n in mcp_tools.MCP_TOOLS if n not in placed]
    if unsorted:
        groups.append(("unsorted", "Unsorted", unsorted))
    return groups


def tool_groups() -> list[dict[str, Any]]:
    from app import mcp_server, mcp_tools

    return [
        {
            "key": key,
            "title": title,
            "tools": [
                {
                    "name": name,
                    "description": mcp_server.TOOL_DESCRIPTIONS.get(name, name.replace("_", " ")),
                    "badge": WRITE_TOOLS.get(name, ""),
                    "params": tool_params(mcp_tools.MCP_TOOLS[name]),
                }
                for name in names
            ],
        }
        for key, title, names in grouped_tools()
    ]


def _route_auth(route: Any) -> bool:
    for dep in route.dependant.dependencies:
        call = getattr(dep, "call", None)
        if call is not None and call.__name__.startswith("_request_auth_context"):
            return True
    return False


def api_routes() -> list[Any]:
    from fastapi.routing import APIRoute

    from app.main import app

    return [r for r in app.routes if isinstance(r, APIRoute)]


def route_groups() -> list[dict[str, Any]]:
    rows: dict[str, list[dict[str, Any]]] = {key: [] for _, key, _ in REST_GROUPS}
    rows["other"] = []
    for route in api_routes():
        key = "other"
        for _, group_key, prefixes in REST_GROUPS:
            if any(route.path == p or route.path.startswith(p + "/") for p in prefixes):
                key = group_key
                break
        slug = re.sub(r"[^a-z0-9]+", "-", route.path.lower()).strip("-") or "root"
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            rows[key].append(
                {
                    "id": f"route-{method.lower()}-{slug}",
                    "method": method,
                    "path": route.path,
                    "auth": _route_auth(route),
                }
            )
    groups = list(REST_GROUPS) + [("Other", "other", ())]
    return [
        {"key": key, "title": title, "routes": rows[key]}
        for title, key, _ in groups
        if rows[key]
    ]


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


def request_types() -> list[dict[str, str]]:
    from app import rfp_connector

    rows = []
    for key, label in rfp_connector.ALLOWED_CONTRIBUTOR_REQUEST_TYPES.items():
        purpose, permission = REQUEST_TYPE_DETAILS.get(key, ("Undocumented.", "Undocumented"))
        rows.append({"key": key, "label": label, "purpose": purpose, "permission": permission})
    return rows


def build_reference() -> dict[str, Any]:
    from app import mcp_server, mcp_tools

    return {
        "server": mcp_server.SERVER_NAME,
        "tool_count": len(mcp_tools.MCP_TOOLS),
        "tool_groups": tool_groups(),
        "route_count": len(api_routes()),
        "route_groups": route_groups(),
        "rfps": public_rfps(),
        "request_types": request_types(),
    }


def render_reference() -> str:
    return json.dumps(build_reference(), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the reference is stale")
    args = parser.parse_args(argv)

    rendered = render_reference()
    current = REFERENCE_JSON.read_text(encoding="utf-8") if REFERENCE_JSON.exists() else ""
    if args.check:
        if rendered != current:
            print("site/data/reference.json is stale. Run: python scripts/build_site.py", file=sys.stderr)
            return 1
        print("site/data/reference.json is up to date.")
        return 0
    if rendered != current:
        REFERENCE_JSON.parent.mkdir(parents=True, exist_ok=True)
        REFERENCE_JSON.write_text(rendered, encoding="utf-8")
        print("Wrote site/data/reference.json.")
    else:
        print("site/data/reference.json already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
