from __future__ import annotations

import unittest

from pydantic import ValidationError

from app import mcp_tools
from app.main import ingest_event_text as ingest_event_text_route
from app.models import EventIngestTextRequest


SAMPLE_EVENT_TEXT = """
Event: Agent Sprint Hackathon
Location: Berlin
Timezone: Europe/Berlin
Start: 2026-07-10 09:00
End: 2026-07-12 18:00
Tracks: AI agents, developer tools
Team size: 1-4
Submission deadline: 2026-07-12 16:00 via https://example.com/submit
Judging criteria: Technical execution, demo quality, product clarity
Rules: Use allowed APIs only.
Submission requirements: Repository URL, demo video, project summary
Sponsor: Daytona
Allowed tools: Python, FastAPI
Recommended tools: Daytona
"""


class EventIngestTest(unittest.TestCase):
    def test_pasted_text_ingest_extracts_obvious_event_context(self) -> None:
        result = mcp_tools.ingest_event_text(
            SAMPLE_EVENT_TEXT,
            source_label="Hackathon page paste",
            source_url="https://example.com/event",
        )

        event = result["event"]
        self.assertEqual(result["status"], "ingested")
        self.assertEqual(event["event_name"], "Agent Sprint Hackathon")
        self.assertEqual(event["location"], "Berlin")
        self.assertEqual(event["timezone"], "Europe/Berlin")
        self.assertEqual(event["starts_at"], "2026-07-10 09:00")
        self.assertEqual(event["ends_at"], "2026-07-12 18:00")
        self.assertEqual(event["tracks"], ["AI agents", "developer tools"])
        self.assertEqual(event["team_size"], {"min": 1, "max": 4})
        self.assertEqual(len(event["deadlines"]), 1)
        self.assertEqual(event["submission"]["url"], "https://example.com/submit")
        self.assertIn("Repository URL", event["submission"]["requirements"])
        self.assertEqual(event["allowed_tools"], ["Python", "FastAPI"])
        self.assertNotIn("Allowed tools: Python, FastAPI", event["rules"])
        self.assertEqual(event["confidence"], "high")
        self.assertEqual(event["sources"][0]["source_label"], "Hackathon page paste")
        self.assertEqual(event["sources"][0]["source_url"], "https://example.com/event")
        noted_fields = {note["field"] for note in event["source_notes"]}
        self.assertIn("event_name", noted_fields)
        self.assertIn("submission", noted_fields)
        self.assertNotIn("event_name", result["missing_fields"])

    def test_missing_fields_are_explicit(self) -> None:
        result = mcp_tools.ingest_event_text(
            "Tiny Hackathon\nBring a laptop and build something useful.",
        )

        event = result["event"]
        self.assertEqual(event["event_name"], "Tiny Hackathon")
        self.assertEqual(event["confidence"], "low")
        self.assertIn("starts_at", result["missing_fields"])
        self.assertIn("judging_criteria", result["missing_fields"])
        self.assertIn("Missing or unclear: starts at", event["open_questions"])

    def test_route_returns_typed_response_shape(self) -> None:
        response = ingest_event_text_route(
            EventIngestTextRequest(
                text=SAMPLE_EVENT_TEXT,
                source_label="Route test paste",
            )
        )

        self.assertEqual(response.status, "ingested")
        self.assertEqual(response.event.event_name, "Agent Sprint Hackathon")
        self.assertEqual(response.event.sources[0].source_label, "Route test paste")
        self.assertEqual(response.event.source_notes[0].confidence, "high")

    def test_request_rejects_tiny_pasted_text(self) -> None:
        with self.assertRaises(ValidationError):
            EventIngestTextRequest(text="too short")


if __name__ == "__main__":
    unittest.main()
