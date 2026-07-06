"""MCP server entry point for BetterHackdays Hack Day tools."""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import mcp_tools
from .db import init_db


SERVER_NAME = "betterhackdays-hack-day"


WORKSPACE_REPO_CONNECTOR_MODEL = {
    "owner": "GitHub owner or organization for the connected workspace repo.",
    "repo": "GitHub repository name used as durable team project state.",
    "default_branch": "Default branch for reviewable workspace writes.",
    "permission_status": "Current permission state for the team room.",
    "allowed_write_targets": [
        "README.md",
        "AGENTS.md",
        "docs/event-context.md",
        "docs/team-profile.md",
        "docs/idea.md",
        "docs/process-plan.md",
        "docs/checklist.md",
        "docs/submission.md",
        ".betterhackdays/session.json",
        ".betterhackdays/tooling.md",
        ".betterhackdays/skills/",
    ],
    "last_synced_planning_snapshot": (
        "Timestamp or identifier for the latest team-room planning state synced "
        "to the workspace repo."
    ),
}


TOOL_DESCRIPTIONS: dict[str, str] = {
    "connect_harness": "Connect a coding harness and create an active participant profile.",
    "update_profile": "Update profile fields used by matchmaking and planning.",
    "get_match_cards": "Return anonymized, scored candidate match cards.",
    "like_profile": "Like a candidate and create a match when the like is mutual.",
    "pass_profile": "Pass on a candidate without creating a match.",
    "get_matches": "Return open matches for a harness.",
    "start_survey": "Start or restart the Socratic onboarding survey.",
    "answer_survey": "Record one onboarding survey answer.",
    "get_survey_state": "Read survey progress without advancing it.",
    "ingest_event_text": "Normalize pasted hackathon text into event context.",
    "rank_idea_suggestions": "Rank concise idea suggestions from event and team signals.",
    "generate_process_timeline": "Generate a deadline-aware Hack Day execution timeline.",
    "generate_prep_checklist": "Generate immediate prep tasks and first-hour focus.",
    "resolve_slug": "Resolve Hack Day codes, standalone slugs, and room keywords.",
}


def _load_fastmcp() -> type[Any]:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "The BetterHackdays MCP server requires the `mcp` package. "
            "Install dependencies with `.venv/bin/pip install -r requirements.txt`."
        ) from exc
    return FastMCP


def _register_tool(server: Any, name: str, func: Callable[..., Any]) -> None:
    description = TOOL_DESCRIPTIONS.get(name, name.replace("_", " "))
    tool_decorator = server.tool(name=name, description=description)
    tool_decorator(func)


def create_server(fastmcp_cls: Optional[type[Any]] = None) -> Any:
    """Create and populate the MCP server without starting transport."""
    init_db()
    cls = fastmcp_cls or _load_fastmcp()
    server = cls(SERVER_NAME)
    for name, func in mcp_tools.MCP_TOOLS.items():
        _register_tool(server, name, func)
    return server


def main() -> None:
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
