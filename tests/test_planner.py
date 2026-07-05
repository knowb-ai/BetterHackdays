from __future__ import annotations

import unittest

from app import mcp_tools
from app.main import planner_ideas as planner_ideas_route
from app.models import EventContext, IdeaSuggestionsRequest, Profile


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


if __name__ == "__main__":
    unittest.main()
