from __future__ import annotations

import os
import tempfile
import unittest

from app import survey
from app.db import init_db
from app.main import (
    ingest_event_text,
    like,
    planner_checklist,
    planner_ideas,
    planner_timeline,
    slug_resolve,
    survey_answer,
    survey_start,
    update_profile,
)
from app.models import (
    ConnectRequest,
    EventContext,
    EventIngestTextRequest,
    IdeaSuggestionsRequest,
    PrepChecklistRequest,
    ProcessTimelineRequest,
    SlugResolveRequest,
    SwipeRequest,
    SurveyAnswerRequest,
    UpdateProfileRequest,
)


class HackDayScenarioIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/scenario.db"
        survey._SESSIONS.clear()
        init_db()

    def tearDown(self) -> None:
        survey._SESSIONS.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.tmp.cleanup()

    def test_full_hack_day_operations_scenario(self) -> None:
        event_response = ingest_event_text(
            EventIngestTextRequest(
                source_label="Organizer event page",
                text=(
                    "Event: Agent Sprint Hackathon\n"
                    "Location: Berlin\n"
                    "Timezone: Europe/Berlin\n"
                    "Start: 2026-07-10 09:00\n"
                    "End: 2026-07-12 18:00\n"
                    "Tracks: AI agents, developer tools\n"
                    "Team size: 1-4\n"
                    "Submission deadline: 2026-07-12 16:00 via https://example.com/submit\n"
                    "Judging criteria: Technical execution, demo quality\n"
                    "Submission requirements: Repository URL, demo video"
                ),
            )
        )
        self.assertEqual(event_response.status, "ingested")
        self.assertEqual(event_response.event.event_name, "Agent Sprint Hackathon")
        event = event_response.event

        start = survey_start(ConnectRequest(harness_id="harness_alice"))
        self.assertEqual(start.question.num, 1)

        for answer in [
            "Yes, regularly I code",
            "Yes, in the last 6 months",
            "Finding someone with the right skills",
            "Discord / Slack",
            "5",
            "Hackathons",
            "verified commits and mutual vibe match",
            "Yes, call me Alice",
        ]:
            survey_result = survey_answer(
                SurveyAnswerRequest(harness_id="harness_alice", answer=answer)
            )

        self.assertTrue(survey_result.done)
        self.assertEqual(survey_result.harness_id, "harness_alice")

        update_profile(
            UpdateProfileRequest(
                harness_id="harness_bob",
                display_label="Bob",
                skills=["backend", "FastAPI", "GitHub workspace setup"],
                interests=["developer tools", "AI agents"],
                preferred_role="backend",
                project_vibe="ship fast",
                looking_for=["frontend"],
                availability="full sprint",
            )
        )

        first_like = like(
            SwipeRequest(
                from_harness_id="harness_alice",
                to_harness_id="harness_bob",
            )
        )
        self.assertEqual(first_like.status, "liked")
        self.assertFalse(first_like.mutual_match)

        second_like = like(
            SwipeRequest(
                from_harness_id="harness_bob",
                to_harness_id="harness_alice",
            )
        )
        self.assertEqual(second_like.status, "matched")
        self.assertTrue(second_like.mutual_match)
        self.assertIsNotNone(second_like.match_id)

        ideas = planner_ideas(
            IdeaSuggestionsRequest(
                event=event,
                topics=["workspace automation"],
            )
        )
        self.assertEqual(ideas.status, "ranked")
        self.assertEqual(len(ideas.ideas), 4)

        event_context = EventContext(**event.model_dump())
        timeline = planner_timeline(
            ProcessTimelineRequest(
                event=event_context,
                hack_day={"participant_state": "matched"},
                team_room={"room_id": "room_1", "slug": "pillow"},
                workspace_repo={
                    "owner": "team-daytona",
                    "repo": "pillow",
                    "default_branch": "main",
                    "connected": True,
                },
            )
        )
        self.assertEqual(timeline.status, "generated")
        self.assertIn("workspace_repo_connected", timeline.timeline_signals)

        checklist = planner_checklist(
            PrepChecklistRequest(
                event=event_context,
                hack_day={"participant_state": "matched"},
                team_room={"room_id": "room_1", "slug": "pillow"},
                workspace_repo={
                    "owner": "team-daytona",
                    "repo": "pillow",
                    "default_branch": "main",
                    "connected": True,
                },
            )
        )
        self.assertEqual(checklist.status, "generated")
        self.assertIn("workspace_repo_connected", checklist.checklist_signals)

        resolved = slug_resolve(
            SlugResolveRequest(
                raw_input="daytona pillow",
                caller_participant_id="harness_alice",
                hack_days=[
                    {
                        "hack_day_id": "hack_day_1",
                        "code": "daytona",
                        "name": "Daytona Hack Day",
                        "status": "active",
                        "participant_states": [
                            {
                                "participant_id": "harness_alice",
                                "state": "workspace_connected",
                            }
                        ],
                        "team_rooms": [
                            {
                                "room_id": "room_1",
                                "keyword": "pillow",
                                "join_mode": "invite_only",
                                "participant_ids": ["harness_alice", "harness_bob"],
                                "state": "workspace_connected",
                                "workspace_repo": {
                                    "owner": "team-daytona",
                                    "repo": "pillow",
                                    "default_branch": "main",
                                    "permission_status": "connected",
                                    "allowed_write_targets": [
                                        "README.md",
                                        "docs/*.md",
                                    ],
                                    "last_synced_planning_snapshot": (
                                        "2026-07-06T10:00:00Z"
                                    ),
                                },
                            }
                        ],
                    }
                ],
            )
        )
        self.assertEqual(resolved.status, "resolved")
        self.assertEqual(resolved.target_type, "team_room")
        self.assertEqual(resolved.next, "open_workspace_repo")
        self.assertEqual(resolved.workspace_repo.owner, "team-daytona")


if __name__ == "__main__":
    unittest.main()
