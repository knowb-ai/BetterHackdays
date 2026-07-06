from __future__ import annotations

import unittest

from app import mcp_tools


SAMPLE_HACK_DAYS = [
    {
        "hack_day_id": "hack_day_1",
        "code": "daytona",
        "name": "Daytona Hack Day",
        "status": "active",
        "participant_states": [
            {"participant_id": "alice", "state": "matchable"},
            {"participant_id": "bob", "state": "workspace_connected"},
        ],
        "team_rooms": [
            {
                "room_id": "room_1",
                "keyword": "pillow",
                "join_mode": "invite_only",
                "participant_ids": ["alice", "bob"],
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
                    "last_synced_planning_snapshot": "2026-07-06T10:00:00Z",
                },
            },
            {
                "room_id": "room_2",
                "keyword": "apex",
                "join_mode": "open",
                "participant_ids": [],
                "state": "room_created",
            },
        ],
    }
]


class SlugResolutionTest(unittest.TestCase):
    def test_resolves_hack_day_code_to_participant_next_action(self) -> None:
        result = mcp_tools.resolve_slug(
            " Daytona ",
            hack_days=SAMPLE_HACK_DAYS,
            caller_participant_id="alice",
        )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["target_type"], "hack_day")
        self.assertEqual(result["target_id"], "hack_day_1")
        self.assertEqual(result["participant_state"], "matchable")
        self.assertEqual(result["next"], "view_matchmaking")

    def test_resolves_namespaced_team_room_and_exposes_repo_when_authorized(self) -> None:
        result = mcp_tools.resolve_slug(
            "daytona pillow",
            hack_days=SAMPLE_HACK_DAYS,
            caller_participant_id="alice",
        )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["target_type"], "team_room")
        self.assertEqual(result["target_id"], "room_1")
        self.assertEqual(result["room_state"], "workspace_connected")
        self.assertEqual(result["next"], "open_workspace_repo")
        self.assertEqual(result["workspace_repo"]["owner"], "team-daytona")
        self.assertEqual(result["workspace_repo"]["repo"], "pillow")

    def test_hides_workspace_repo_when_caller_is_not_authorized(self) -> None:
        result = mcp_tools.resolve_slug(
            "daytona pillow",
            hack_days=SAMPLE_HACK_DAYS,
            caller_participant_id="charlie",
        )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["target_type"], "team_room")
        self.assertEqual(result["next"], "request_room_access")
        self.assertIsNone(result["workspace_repo"])
        self.assertEqual(result["required_authorization"], ["team_room_invite"])

    def test_resolves_standalone_slug_to_team_room(self) -> None:
        result = mcp_tools.resolve_slug(
            "pillow",
            hack_days=SAMPLE_HACK_DAYS,
            standalone_slugs=[
                {
                    "slug": "pillow",
                    "target_type": "team_room",
                    "target_id": "room_1",
                }
            ],
            caller_participant_id="bob",
        )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["target_type"], "team_room")
        self.assertEqual(result["target_id"], "room_1")
        self.assertEqual(result["workspace_repo"]["permission_status"], "connected")

    def test_ip_cluster_is_not_part_of_authorization(self) -> None:
        result = mcp_tools.resolve_slug(
            "daytona pillow",
            hack_days=SAMPLE_HACK_DAYS,
            caller_participant_id=None,
        )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["next"], "request_room_access")
        self.assertIsNone(result["workspace_repo"])

    def test_unknown_slug_returns_safe_not_found(self) -> None:
        result = mcp_tools.resolve_slug("daytona unknown", hack_days=SAMPLE_HACK_DAYS)

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["next"], "check_code_or_create_hack_day")


if __name__ == "__main__":
    unittest.main()
