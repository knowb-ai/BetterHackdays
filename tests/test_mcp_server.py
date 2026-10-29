from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any, Callable

from app import mcp_server, survey


class FakeFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: dict[str, dict[str, Any]] = {}

    def tool(self, *, name: str, description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name] = {
                "description": description,
                "func": func,
            }
            return func

        return decorator


class McpServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/mcp.db"
        survey._SESSIONS.clear()

    def tearDown(self) -> None:
        survey._SESSIONS.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.tmp.cleanup()

    def test_create_server_registers_current_tool_layer(self) -> None:
        server = mcp_server.create_server(FakeFastMCP)

        self.assertEqual(server.name, "betterhackdays-hack-day")
        self.assertEqual(
            set(server.tools),
            {
                "connect_harness",
                "update_profile",
                "get_match_cards",
                "like_profile",
                "pass_profile",
                "get_matches",
                "start_survey",
                "answer_survey",
                "get_survey_state",
                "ingest_event_text",
                "rank_idea_suggestions",
                "generate_process_timeline",
                "generate_prep_checklist",
                "resolve_slug",
                "list_project_rfps",
                "read_project_rfp",
                "search_project_rfps",
                "compare_project_rfps",
                "list_design_resources",
                "read_design_resource",
                "search_design_resources",
                "fetch_idea_catalogue",
                "qualify_idea",
                "propose_idea_catalogue_addition",
                "preview_contributor_request",
                "submit_contributor_request",
                "list_contributor_requests",
                "authorize_github_mutation",
                "grant_repository_access",
            },
        )
        self.assertIn("Hack Day", server.tools["resolve_slug"]["description"])
        self.assertIn("RFP", server.tools["list_project_rfps"]["description"])

    def test_registered_survey_tools_use_shared_function_layer(self) -> None:
        server = mcp_server.create_server(FakeFastMCP)

        started = server.tools["start_survey"]["func"]("harness_alice")
        self.assertEqual(started["status"], "survey_started")

        answered = server.tools["answer_survey"]["func"](
            "harness_alice",
            "Yes, regularly I code",
        )
        self.assertEqual(answered["answered"], 1)

        state = server.tools["get_survey_state"]["func"]("harness_alice")
        self.assertEqual(state["progress"], "1/8")

    def test_workspace_repo_connector_model_lists_safe_write_targets(self) -> None:
        model = mcp_server.WORKSPACE_REPO_CONNECTOR_MODEL

        self.assertIn("owner", model)
        self.assertIn("repo", model)
        self.assertIn("allowed_write_targets", model)
        self.assertIn("AGENTS.md", model["allowed_write_targets"])
        self.assertIn(".betterhackdays/session.json", model["allowed_write_targets"])


if __name__ == "__main__":
    unittest.main()
