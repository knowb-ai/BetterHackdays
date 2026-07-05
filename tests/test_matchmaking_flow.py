from __future__ import annotations

import os
import tempfile
import unittest

from fastapi import HTTPException
from pydantic import ValidationError

from app import mcp_tools, survey
from app.db import get_conn, init_db
from app.main import like as like_route
from app.models import ConnectRequest, SwipeRequest


class MatchmakingFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/test.db"
        survey._SESSIONS.clear()
        init_db()

    def tearDown(self) -> None:
        survey._SESSIONS.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.tmp.cleanup()

    def _profile(
        self,
        harness_id: str,
        *,
        skills: list[str],
        interests: list[str],
        looking_for: list[str],
        preferred_role: str,
        project_vibe: str = "ship fast",
    ) -> dict:
        return mcp_tools.update_profile(
            harness_id=harness_id,
            display_label=harness_id,
            skills=skills,
            interests=interests,
            preferred_role=preferred_role,
            project_vibe=project_vibe,
            looking_for=looking_for,
            availability="full sprint",
        )["profile"]

    def test_connect_starts_survey_and_creates_profile(self) -> None:
        result = survey.start_survey("harness_alice")

        self.assertEqual(result["status"], "survey_started")
        self.assertEqual(result["next"], "survey")
        self.assertEqual(result["profile"]["harness_id"], "harness_alice")
        self.assertEqual(result["profile"]["display_label"], "New builder")
        self.assertEqual(result["question"]["num"], 1)

        state = survey.survey_state("harness_alice")
        self.assertEqual(state["progress"], "0/8")
        self.assertFalse(state["done"])

    def test_survey_progress_persists_after_memory_cache_clear(self) -> None:
        survey.start_survey("harness_alice")
        answer = survey.answer_survey("harness_alice", "Yes, regularly I code")
        self.assertEqual(answer["next_question"]["num"], 2)

        survey._SESSIONS.clear()

        state = survey.survey_state("harness_alice")
        self.assertEqual(state["progress"], "1/8")
        self.assertEqual(state["question"]["num"], 2)
        self.assertFalse(state["done"])

        next_answer = survey.answer_survey("harness_alice", "Yes, in the last 6 months")
        self.assertEqual(next_answer["answered"], 2)
        self.assertEqual(next_answer["next_question"]["num"], 3)

    def test_start_survey_intentionally_restarts_progress(self) -> None:
        survey.start_survey("harness_alice")
        survey.answer_survey("harness_alice", "Yes, regularly I code")

        restarted = survey.start_survey("harness_alice")

        self.assertEqual(restarted["question"]["num"], 1)
        self.assertEqual(survey.survey_state("harness_alice")["progress"], "0/8")

    def test_cards_are_scored_sorted_and_exclude_swiped_profiles(self) -> None:
        self._profile(
            "harness_alice",
            skills=["frontend"],
            interests=["developer tools", "demos"],
            looking_for=["backend"],
            preferred_role="frontend",
        )
        self._profile(
            "harness_backend",
            skills=["backend"],
            interests=["developer tools"],
            looking_for=["frontend"],
            preferred_role="backend",
        )
        self._profile(
            "harness_design",
            skills=["design"],
            interests=["visual story"],
            looking_for=["frontend"],
            preferred_role="design",
            project_vibe="story first",
        )

        cards = mcp_tools.get_match_cards("harness_alice")["cards"]
        self.assertEqual([card["harness_id"] for card in cards], [
            "harness_backend",
            "harness_design",
        ])
        self.assertGreater(cards[0]["match_score"], cards[1]["match_score"])
        self.assertIn("developer tools", cards[0]["match_reason"].lower())

        mcp_tools.like_profile("harness_alice", "harness_backend")
        remaining = mcp_tools.get_match_cards("harness_alice")["cards"]
        self.assertEqual([card["harness_id"] for card in remaining], [
            "harness_design",
        ])

        mcp_tools.pass_profile("harness_alice", "harness_design")
        self.assertEqual(mcp_tools.get_match_cards("harness_alice")["cards"], [])

    def test_pass_does_not_create_match(self) -> None:
        self._profile(
            "harness_alice",
            skills=["frontend"],
            interests=["demos"],
            looking_for=["backend"],
            preferred_role="frontend",
        )
        self._profile(
            "harness_backend",
            skills=["backend"],
            interests=["demos"],
            looking_for=["frontend"],
            preferred_role="backend",
        )

        result = mcp_tools.pass_profile("harness_alice", "harness_backend")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(mcp_tools.get_matches("harness_alice")["matches"], [])
        self.assertEqual(mcp_tools.get_matches("harness_backend")["matches"], [])

    def test_invalid_harness_ids_fail_model_validation(self) -> None:
        with self.assertRaises(ValidationError):
            ConnectRequest(harness_id="")
        with self.assertRaises(ValidationError):
            ConnectRequest(harness_id="ab")
        with self.assertRaises(ValidationError):
            SwipeRequest(from_harness_id="harness alice", to_harness_id="harness_bob")

        request = ConnectRequest(harness_id="  harness_alice  ")
        self.assertEqual(request.harness_id, "harness_alice")

    def test_swipes_require_existing_profiles(self) -> None:
        self._profile(
            "harness_alice",
            skills=["frontend"],
            interests=["demos"],
            looking_for=["backend"],
            preferred_role="frontend",
        )

        with self.assertRaises(mcp_tools.ProfileNotFoundError):
            mcp_tools.like_profile("harness_alice", "harness_missing")
        with self.assertRaises(mcp_tools.ProfileNotFoundError):
            mcp_tools.pass_profile("harness_missing", "harness_alice")

    def test_like_route_returns_clear_errors(self) -> None:
        self._profile(
            "harness_alice",
            skills=["frontend"],
            interests=["demos"],
            looking_for=["backend"],
            preferred_role="frontend",
        )

        with self.assertRaises(HTTPException) as self_like:
            like_route(
                SwipeRequest(
                    from_harness_id="harness_alice",
                    to_harness_id="harness_alice",
                )
            )
        self.assertEqual(self_like.exception.status_code, 400)
        self.assertEqual(
            self_like.exception.detail,
            "A harness cannot like itself.",
        )

        with self.assertRaises(HTTPException) as missing_profile:
            like_route(
                SwipeRequest(
                    from_harness_id="harness_alice",
                    to_harness_id="harness_missing",
                )
            )
        self.assertEqual(missing_profile.exception.status_code, 404)
        self.assertIn("harness_missing", missing_profile.exception.detail)

    def test_duplicate_swipe_updates_existing_action(self) -> None:
        self._profile(
            "harness_alice",
            skills=["frontend"],
            interests=["demos"],
            looking_for=["backend"],
            preferred_role="frontend",
        )
        self._profile(
            "harness_backend",
            skills=["backend"],
            interests=["demos"],
            looking_for=["frontend"],
            preferred_role="backend",
        )

        mcp_tools.pass_profile("harness_alice", "harness_backend")
        mcp_tools.like_profile("harness_alice", "harness_backend")

        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT action FROM swipes
                WHERE from_harness_id = ? AND to_harness_id = ?
                """,
                ("harness_alice", "harness_backend"),
            ).fetchall()
        self.assertEqual([row["action"] for row in rows], ["like"])

    def test_mutual_like_creates_match_for_both_profiles(self) -> None:
        self._profile(
            "harness_alice",
            skills=["frontend"],
            interests=["developer tools"],
            looking_for=["backend"],
            preferred_role="frontend",
        )
        self._profile(
            "harness_backend",
            skills=["backend"],
            interests=["developer tools"],
            looking_for=["frontend"],
            preferred_role="backend",
        )

        first_like = mcp_tools.like_profile("harness_alice", "harness_backend")
        self.assertEqual(first_like["status"], "liked")
        self.assertFalse(first_like["mutual_match"])

        second_like = mcp_tools.like_profile("harness_backend", "harness_alice")
        self.assertEqual(second_like["status"], "matched")
        self.assertTrue(second_like["mutual_match"])
        self.assertEqual(second_like["harness_ids"], [
            "harness_alice",
            "harness_backend",
        ])

        alice_matches = mcp_tools.get_matches("harness_alice")["matches"]
        backend_matches = mcp_tools.get_matches("harness_backend")["matches"]
        self.assertEqual(len(alice_matches), 1)
        self.assertEqual(alice_matches, backend_matches)
        self.assertEqual(alice_matches[0]["match_id"], second_like["match_id"])

        self.assertEqual(mcp_tools.get_match_cards("harness_alice")["cards"], [])


if __name__ == "__main__":
    unittest.main()
