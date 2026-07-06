from __future__ import annotations

import unittest

from app import mcp_tools
from app.main import (
    planner_checklist as planner_checklist_route,
    planner_ideas as planner_ideas_route,
    planner_timeline as planner_timeline_route,
)
from app.models import (
    EventContext,
    HackDayContext,
    IdeaSuggestionsRequest,
    PrepChecklistRequest,
    ProcessTimelineRequest,
    Profile,
    TeamRoomContext,
    WorkspaceRepoContext,
)


EVENT_CONTEXT = {
    "event_name": "Agent Sprint Hackathon",
    "description": "Build useful AI agent workflows for developer teams.",
    "format": "hybrid",
    "location": "Berlin",
    "timezone": "Europe/Berlin",
    "starts_at": "2026-07-10 09:00",
    "ends_at": "2026-07-12 18:00",
    "tracks": ["AI agents", "developer tools"],
    "team_size": {"min": 1, "max": 4},
    "deadlines": [
        {
            "name": "Final submission",
            "due_at": "2026-07-12 16:00",
            "description": "Submit repo and demo video.",
        }
    ],
    "judging_criteria": [
        {"name": "Technical execution", "description": "Working implementation"},
        {"name": "Demo quality", "description": "Clear demo story"},
    ],
    "rules": [],
    "constraints": [],
    "sponsors": [],
    "submission": {
        "url": "https://example.com/submit",
        "requirements": ["Repository URL", "demo video"],
    },
    "allowed_tools": ["Python", "FastAPI"],
    "recommended_tools": ["agent frameworks"],
    "open_questions": [],
    "confidence": "high",
    "sources": [],
    "source_notes": [],
}


PROFILE = {
    "harness_id": "harness_alice",
    "display_label": "Alice",
    "skills": ["FastAPI", "Python", "AI agents"],
    "interests": ["developer tools", "automation"],
    "preferred_role": "backend",
    "project_vibe": "ship fast",
    "looking_for": ["design"],
    "availability": "full sprint",
}


class PlannerTest(unittest.TestCase):
    def test_ranked_ideas_include_required_types_and_short_explanations(self) -> None:
        result = mcp_tools.rank_idea_suggestions(
            EVENT_CONTEXT,
            profile=PROFILE,
            topics=["workspace automation"],
        )

        idea_types = {idea["idea_type"] for idea in result["ideas"]}
        self.assertEqual(
            idea_types,
            {"safe_default", "ambitious", "niche", "fast_fallback"},
        )
        self.assertEqual(result["status"], "ranked")
        self.assertEqual(result["next"], "review_ideas")
        self.assertIn("event_tracks", result["ranking_signals"])
        self.assertIn("profile_or_team_skills", result["ranking_signals"])
        for idea in result["ideas"]:
            self.assertLessEqual(len(idea["why_it_fits"]), 140)
            self.assertTrue(idea["main_tradeoff"])

    def test_event_and_profile_signals_are_visible_in_top_ranked_idea(self) -> None:
        result = mcp_tools.rank_idea_suggestions(
            EVENT_CONTEXT,
            profile=PROFILE,
            topics=["workspace automation"],
        )

        top = result["ideas"][0]
        joined_signals = " | ".join(top["signals"])
        self.assertIn("Track fit: AI agents", joined_signals)
        self.assertIn("Judging fit: Technical execution", joined_signals)
        self.assertIn("Skill fit:", joined_signals)
        self.assertIn("Topic fit: workspace automation", joined_signals)
        self.assertGreaterEqual(top["score"], result["ideas"][-1]["score"])

    def test_sparse_context_still_returns_actionable_fallbacks(self) -> None:
        result = mcp_tools.rank_idea_suggestions(
            {"event_name": "Tiny Hackathon", "confidence": "low"},
        )

        self.assertEqual(len(result["ideas"]), 4)
        self.assertEqual(result["ranking_signals"], ["fallback_defaults"])
        self.assertTrue(all(idea["summary"] for idea in result["ideas"]))

    def test_route_returns_typed_response_shape(self) -> None:
        request = IdeaSuggestionsRequest(
            event=EventContext(**EVENT_CONTEXT),
            profile=Profile(**PROFILE),
            topics=["workspace automation"],
        )

        response = planner_ideas_route(request)

        self.assertEqual(response.status, "ranked")
        self.assertEqual(len(response.ideas), 4)
        self.assertEqual(response.ideas[0].idea_type in {
            "safe_default",
            "ambitious",
            "niche",
            "fast_fallback",
        }, True)
        self.assertIn("event_tracks", response.ranking_signals)

    def test_process_timeline_returns_required_stages_and_deadline(self) -> None:
        result = mcp_tools.generate_process_timeline(
            EVENT_CONTEXT,
            hack_day={"participant_state": "matchable"},
        )

        self.assertEqual(result["status"], "generated")
        self.assertEqual(result["next"], "review_timeline")
        self.assertEqual(
            [stage["stage"] for stage in result["stages"]],
            [
                "before_event",
                "first_30_minutes",
                "first_2_hours",
                "validation",
                "demo_prep",
                "final_submission",
            ],
        )
        final_stage = result["stages"][-1]
        self.assertEqual(final_stage["deadline"]["due_at"], "2026-07-12 16:00")
        self.assertIn("event_deadlines", result["timeline_signals"])
        self.assertIn("hack_day_state:matchable", result["timeline_signals"])

    def test_process_timeline_reports_missing_deadline_context(self) -> None:
        result = mcp_tools.generate_process_timeline(
            {"event_name": "Tiny Hackathon", "confidence": "low"},
        )

        self.assertIn("deadlines", result["missing_inputs"])
        self.assertIn("starts_at", result["missing_inputs"])
        self.assertIn("missing_inputs", result["timeline_signals"])
        final_stage = result["stages"][-1]
        self.assertEqual(final_stage["when"], "At the published submission deadline")
        self.assertIsNone(final_stage.get("deadline"))

    def test_process_timeline_adds_workspace_repo_tasks_for_team_room(self) -> None:
        result = mcp_tools.generate_process_timeline(
            EVENT_CONTEXT,
            team_room={"room_id": "room_123", "slug": "agent-sprint"},
            workspace_repo={
                "owner": "team-agent-sprint",
                "repo": "betterhackdays-agent-sprint",
                "default_branch": "main",
                "connected": True,
            },
        )

        all_tasks = " ".join(
            task
            for stage in result["stages"]
            for task in stage["tasks"]
        )
        self.assertIn(
            "team-agent-sprint/betterhackdays-agent-sprint",
            all_tasks,
        )
        self.assertIn("workspace_repo_connected", result["timeline_signals"])
        self.assertIn("hack_day_state:workspace_connected", result["timeline_signals"])

    def test_process_timeline_does_not_assume_disconnected_repo_is_ready(self) -> None:
        result = mcp_tools.generate_process_timeline(
            EVENT_CONTEXT,
            team_room={"room_id": "room_123", "slug": "agent-sprint"},
            workspace_repo={
                "owner": "team-agent-sprint",
                "repo": "betterhackdays-agent-sprint",
                "connected": False,
            },
        )

        all_tasks = " ".join(
            task
            for stage in result["stages"]
            for task in stage["tasks"]
        )
        self.assertIn("permissioned next step", all_tasks)
        self.assertIn("hack_day_state:team_room", result["timeline_signals"])
        self.assertNotIn("workspace_repo_connected", result["timeline_signals"])

    def test_process_timeline_reports_deadline_without_due_date(self) -> None:
        event = dict(EVENT_CONTEXT)
        event["deadlines"] = [
            {
                "name": "Final submission",
                "due_at": None,
                "description": "Submit repo and demo video.",
            }
        ]

        result = mcp_tools.generate_process_timeline(event)

        self.assertIn("deadline_due_at", result["missing_inputs"])
        self.assertIn("event_deadlines", result["timeline_signals"])

    def test_timeline_route_returns_typed_response_shape(self) -> None:
        request = ProcessTimelineRequest(
            event=EventContext(**EVENT_CONTEXT),
            profile=Profile(**PROFILE),
            hack_day=HackDayContext(participant_state="matchable"),
            team_room=TeamRoomContext(room_id="room_123", slug="agent-sprint"),
            workspace_repo=WorkspaceRepoContext(
                owner="team-agent-sprint",
                repo="betterhackdays-agent-sprint",
                connected=True,
            ),
        )

        response = planner_timeline_route(request)

        self.assertEqual(response.status, "generated")
        self.assertEqual(response.stages[-1].deadline.due_at, "2026-07-12 16:00")
        self.assertIn("workspace_repo_connected", response.timeline_signals)

    def test_prep_checklist_active_participant_prompts_profile_completion(self) -> None:
        result = mcp_tools.generate_prep_checklist(
            EVENT_CONTEXT,
            hack_day={"participant_state": "active"},
        )

        tasks = " ".join(
            item["task"]
            for section in result["sections"]
            for item in section["items"]
        )
        self.assertIn("Finish the profile loop", tasks)
        self.assertIn("hack_day_state:active", result["checklist_signals"])
        self.assertIn("profile_skills", result["missing_inputs"])

    def test_prep_checklist_matchable_participant_mentions_cards(self) -> None:
        result = mcp_tools.generate_prep_checklist(
            EVENT_CONTEXT,
            profile=PROFILE,
            hack_day={"participant_state": "matchable"},
        )

        tasks = " ".join(
            item["task"]
            for section in result["sections"]
            for item in section["items"]
        )
        self.assertIn("Review match cards", tasks)
        self.assertIn("profile_or_team_skills", result["checklist_signals"])
        self.assertNotIn("profile_skills", result["missing_inputs"])

    def test_prep_checklist_team_room_keeps_repo_permissioned_until_connected(self) -> None:
        result = mcp_tools.generate_prep_checklist(
            EVENT_CONTEXT,
            profile=PROFILE,
            team_room={"room_id": "room_123", "slug": "agent-sprint"},
            workspace_repo={
                "owner": "team-agent-sprint",
                "repo": "betterhackdays-agent-sprint",
                "connected": False,
            },
        )

        tasks = " ".join(
            item["task"]
            for section in result["sections"]
            for item in section["items"]
        )
        self.assertIn("permissioned", tasks)
        self.assertIn("workspace_repo", result["missing_inputs"])
        self.assertNotIn("workspace_repo_connected", result["checklist_signals"])

    def test_prep_checklist_connected_workspace_references_repo_docs(self) -> None:
        result = mcp_tools.generate_prep_checklist(
            EVENT_CONTEXT,
            profile=PROFILE,
            team_room={"room_id": "room_123", "slug": "agent-sprint"},
            workspace_repo={
                "owner": "team-agent-sprint",
                "repo": "betterhackdays-agent-sprint",
                "connected": True,
            },
        )

        linked_docs = {
            item["linked_doc"]
            for section in result["sections"]
            for item in section["items"]
            if item["linked_doc"]
        }
        tasks = " ".join(
            item["task"]
            for section in result["sections"]
            for item in section["items"]
        )
        self.assertIn("team-agent-sprint/betterhackdays-agent-sprint", tasks)
        self.assertIn("AGENTS.md", linked_docs)
        self.assertIn("docs/checklist.md", linked_docs)
        self.assertIn("workspace_repo_connected", result["checklist_signals"])

    def test_prep_checklist_sparse_context_still_returns_actionable_sections(self) -> None:
        result = mcp_tools.generate_prep_checklist(
            {"event_name": "Tiny Hackathon", "confidence": "low"},
        )

        self.assertEqual(
            [section["section"] for section in result["sections"]],
            [
                "prep_tasks",
                "first_hour_focus",
                "missing_inputs",
                "optional_help",
                "workspace_next_steps",
            ],
        )
        self.assertIn("tracks", result["missing_inputs"])
        self.assertIn("judging_criteria", result["missing_inputs"])
        self.assertIn("missing_inputs", result["checklist_signals"])

    def test_checklist_route_returns_typed_response_shape(self) -> None:
        request = PrepChecklistRequest(
            event=EventContext(**EVENT_CONTEXT),
            profile=Profile(**PROFILE),
            hack_day=HackDayContext(participant_state="matchable"),
            team_room=TeamRoomContext(room_id="room_123", slug="agent-sprint"),
            workspace_repo=WorkspaceRepoContext(
                owner="team-agent-sprint",
                repo="betterhackdays-agent-sprint",
                connected=True,
            ),
        )

        response = planner_checklist_route(request)

        self.assertEqual(response.status, "generated")
        self.assertEqual(response.next, "act_on_checklist")
        self.assertIn("workspace_repo_connected", response.checklist_signals)
        self.assertEqual(response.sections[0].section, "prep_tasks")


if __name__ == "__main__":
    unittest.main()
