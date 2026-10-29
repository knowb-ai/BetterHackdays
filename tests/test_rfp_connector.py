"""Focused layered tests for the BetterHackdays RFP and contributor connector."""

from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any, Callable
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import mcp_server, mcp_tools, rfp_connector, survey
from app.db import init_db
from app.main import (
    app,
    contributor_request_list as contributor_request_list_route,
    contributor_request_preview as contributor_request_preview_route,
    contributor_request_submit as contributor_request_submit_route,
    design_resources_list as design_resources_list_route,
    design_resources_read as design_resources_read_route,
    design_resources_search as design_resources_search_route,
    ingest_event_text as ingest_event_text_route,
    planner_ideas as planner_ideas_route,
    rfps_compare as rfps_compare_route,
    rfps_list as rfps_list_route,
    rfps_read as rfps_read_route,
    rfps_search as rfps_search_route,
)
from app.models import (
    CompareRfpsRequest,
    ContributorRequestPreviewInput,
    ContributorRequestSubmitInput,
    DesignResourceReadRequest,
    EventIngestTextRequest,
    IdeaSuggestionsRequest,
    Profile,
)


REPRESENTATIVE_EVENT_TEXT = (
    "Event: Agent Sprint Hackathon\n"
    "Tracks: AI agents, developer tools\n"
    "Submission deadline: 2026-07-12 16:00\n"
    "Judging criteria: Technical execution, demo quality"
)

SAMPLE_PUBLIC_SHOWCASE: list[dict[str, Any]] = [
    {"title": "ShadowCaster", "tags": ["Platform Visibility", "Moderation Policy", "Event Amplification"]},
    {"title": "Underminer", "tags": ["Narrative Reconstruction", "Source Traceability", "Context Tracing"]},
    {"title": "X-Poser", "tags": ["Claim Checking", "Evidence Retrieval", "Smoke Test"]},
    {"title": "Precongnition", "tags": ["Conference Discovery", "Session Continuity", "Learning Graph"]},
    {"title": "MarkSweep", "tags": ["Inbox Triage", "Browser Extension", "User Rules"]},
    {"title": "Subtracktor", "tags": ["Subscription Escape", "Inbox Agents", "Financial Leakage"]},
    {"title": "BetterHackdays", "tags": ["Shared Hack Day", "Team Formation", "Project Continuity"]},
    {"title": "BetterLover", "tags": ["Care Planning", "Cycle-Aware Context", "Consent First"]},
    {"title": "Sepnu Pues", "tags": ["Daily Follow-Through", "Opt-In Accountability", "User Controlled Sharing"]},
]

SAMPLE_DESIGN_CONTENT: dict[str, str] = {
    "DESIGN_SYSTEM.md": (
        "# KnowB Visual Design System\n\n"
        "Autumn and Gold palettes, Internal/External/Artistic channels, six themes, "
        "five styles, and fixed typography."
    ),
    "ORGBRAND_GUIDELINES.md": (
        "# Autumn Implementation\n\n"
        "Autumn tokens, gradients, contrast, CRT, motion, and WCAG 2.2 AA rules."
    ),
    "content/org-book.md": "# KnowB AI Visual Design System\n\nPublic Org Book page.",
    "static/css/global.css": ":root { --autumn-fire: #FF4A1A; }",
    "static/css/concept-book.css": ".plate { color: #FCF6F3; }",
    "static/favicon.svg": "<svg><rect fill=\"#FF4A1A\" /></svg>",
    "design/pixel-icons/dictionary.txt": "dictionary: agent, room, plan",
}


def _patch_live_public_sources(testcase: unittest.TestCase) -> None:
    """Keep tests hermetic while production defaults stay live."""
    patches = [
        patch.object(
            rfp_connector,
            "fetch_public_org_repos",
            return_value=[dict(repo) for repo in rfp_connector.DEFAULT_PUBLIC_REPO_METADATA],
        ),
        patch.object(
            rfp_connector,
            "fetch_public_repo_readme",
            side_effect=lambda name, branch="main", **kwargs: rfp_connector.DEFAULT_PUBLIC_READMES.get(name),
        ),
        patch.object(
            rfp_connector,
            "fetch_public_showcase_entries",
            return_value=[dict(entry) for entry in SAMPLE_PUBLIC_SHOWCASE],
        ),
        patch.object(
            rfp_connector,
            "fetch_canonical_idea_catalogue_markdown",
            side_effect=lambda **kwargs: SAMPLE_CLOUD_BUILDER_STACK_CATALOGUE,
        ),
        patch.object(
            rfp_connector,
            "_fetch_cloud_builder_stack_policy_state",
            return_value={
                "codeowners_present": False,
                "codeowners_covers_catalogue": False,
                "branch_protection_enforced": False,
                "ruleset_review_enforced": False,
            },
        ),
        patch.object(
            rfp_connector,
            "fetch_design_resource_content",
            side_effect=lambda path, **kwargs: SAMPLE_DESIGN_CONTENT.get(path),
        ),
    ]
    for patcher in patches:
        patcher.start()
        testcase.addCleanup(patcher.stop)

REPRESENTATIVE_PROFILE = {
    "harness_id": "harness_wp1",
    "display_label": "Builder One",
    "skills": ["FastAPI", "Python", "AI agents"],
    "interests": ["developer tools"],
    "preferred_role": "backend",
    "project_vibe": "ship fast",
    "looking_for": ["design"],
    "availability": "full sprint",
}


class FakeFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: dict[str, dict[str, Any]] = {}

    def tool(
        self, *, name: str, description: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name] = {
                "description": description,
                "func": func,
            }
            return func

        return decorator


class TestWorkPackage1BaselineFlow(unittest.TestCase):
    """Work Package 1: Prove the smallest live source-to-result path and preserve REST/MCP contracts."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/wp1.db"
        survey._SESSIONS.clear()
        init_db()

    def tearDown(self) -> None:
        survey._SESSIONS.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.tmp.cleanup()

    def test_smallest_source_to_result_flow_matches_across_mcp_and_rest(self) -> None:
        server = mcp_server.create_server(FakeFastMCP)

        mcp_ingested = server.tools["ingest_event_text"]["func"](
            REPRESENTATIVE_EVENT_TEXT,
            source_label="WP1 representative source",
        )
        self.assertEqual(mcp_ingested["status"], "ingested")
        self.assertEqual(
            mcp_ingested["event"]["tracks"],
            ["AI agents", "developer tools"],
        )

        mcp_ranked = server.tools["rank_idea_suggestions"]["func"](
            mcp_ingested["event"],
            profile=REPRESENTATIVE_PROFILE,
            topics=["workspace automation"],
        )
        self.assertEqual(mcp_ranked["status"], "ranked")
        self.assertEqual(mcp_ranked["next"], "review_ideas")
        self.assertEqual(
            {idea["idea_type"] for idea in mcp_ranked["ideas"]},
            {"safe_default", "ambitious", "niche", "fast_fallback"},
        )
        self.assertEqual(
            mcp_ranked["ranking_signals"],
            [
                "event_tracks",
                "judging_criteria",
                "profile_or_team_skills",
                "chosen_topics",
            ],
        )

        rest_ingested = ingest_event_text_route(
            EventIngestTextRequest(
                text=REPRESENTATIVE_EVENT_TEXT,
                source_label="WP1 representative source",
            )
        )
        rest_ranked = planner_ideas_route(
            IdeaSuggestionsRequest(
                event=rest_ingested.event,
                profile=Profile(**REPRESENTATIVE_PROFILE),
                topics=["workspace automation"],
            )
        )
        self.assertEqual(rest_ranked.status, "ranked")
        self.assertEqual(rest_ranked.next, "review_ideas")
        self.assertEqual(
            [idea.summary for idea in rest_ranked.ideas],
            [idea["summary"] for idea in mcp_ranked["ideas"]],
        )
        self.assertEqual(
            [idea.score for idea in rest_ranked.ideas],
            [idea["score"] for idea in mcp_ranked["ideas"]],
        )


class TestWorkPackage2RfpCatalogue(unittest.TestCase):
    """Work Package 2: Public project RFP catalogue discovery, filtering, README grounding, and privacy."""

    def setUp(self) -> None:
        _patch_live_public_sources(self)

    def test_default_catalogue_preserves_website_rfps_live_projects_and_connector_only_briefs(
        self,
    ) -> None:
        catalogue = rfp_connector.build_project_rfp_catalogue()
        by_id = {item["rfp_id"]: item for item in catalogue["rfps"]}

        self.assertEqual(
            list(by_id.keys()),
            [
                "shadowcaster",
                "underminer",
                "x-poser",
                "precongnition",
                "marksweep",
                "subtracktor",
                "betterhackdays",
                "betterlover",
                "sepnu-pues",
                "faultline",
                "unlinked",
            ],
        )

        # Non-project baseline repos are listed as public resources, not invented RFPs
        resource_ids = {item["resource_id"] for item in catalogue["public_resources"]}
        self.assertEqual(resource_ids, {"knowb-ai.github.io", "cloud-builder-stack"})

        # Public project RFPs include source-linked READMEs
        for project_id, repo_name in (
            ("x-poser", "x-poser"),
            ("betterhackdays", "BetterHackdays"),
            ("betterlover", "BetterLover"),
            ("sepnu-pues", "sepnu-pues"),
        ):
            item = by_id[project_id]
            self.assertEqual(item["brief_status"], "grounded")
            self.assertEqual(
                item["repo_url"],
                f"https://github.com/knowb-ai/{repo_name}",
            )
            self.assertEqual(
                item["readme_url"],
                f"https://github.com/knowb-ai/{repo_name}/blob/main/README.md",
            )
            self.assertTrue(item["readme_excerpt"])

        # Faultline and Unlinked stay connector-only with exact owner-approved summaries
        faultline = by_id["faultline"]
        self.assertEqual(faultline["visibility"], "connector_only")
        self.assertFalse(faultline["listed_on_website"])
        self.assertIsNone(faultline["repo_url"])
        self.assertIsNone(faultline["readme_url"])
        self.assertIsNone(faultline["repo_name"])
        self.assertEqual(
            faultline["summary"],
            rfp_connector.FAULTLINE_APPROVED_SUMMARY,
        )

        unlinked = by_id["unlinked"]
        self.assertEqual(unlinked["visibility"], "connector_only")
        self.assertFalse(unlinked["listed_on_website"])
        self.assertIsNone(unlinked["repo_url"])
        self.assertIsNone(unlinked["readme_url"])
        self.assertIsNone(unlinked["repo_name"])
        self.assertEqual(
            unlinked["summary"],
            rfp_connector.UNLINKED_APPROVED_SUMMARY,
        )

        serialized = str(catalogue).lower()
        self.assertNotIn("knowledgehq", serialized)

    def test_default_catalogue_uses_live_public_sources_and_reports_fallback(
        self,
    ) -> None:
        live = rfp_connector.build_project_rfp_catalogue()
        self.assertEqual(live["metadata_source"], "live_public_org_repos")

        fallback = rfp_connector.build_project_rfp_catalogue(
            repo_metadata=None,
            readme_fetcher=lambda name, branch: rfp_connector.DEFAULT_PUBLIC_READMES.get(name),
        )
        self.assertEqual(fallback["metadata_source"], "live_public_org_repos")

        with patch.object(
            rfp_connector,
            "fetch_public_org_repos",
            side_effect=RuntimeError("upstream 503"),
        ):
            degraded = rfp_connector.build_project_rfp_catalogue()
        self.assertEqual(
            degraded["metadata_source"],
            "baseline_fallback_live_listing_unavailable",
        )
        self.assertTrue(degraded["rfps"])

    def test_filtering_excludes_private_archived_unapproved_forks_ascii_and_deduplicates(
        self,
    ) -> None:
        metadata = [
            *rfp_connector.DEFAULT_PUBLIC_REPO_METADATA,
            {
                "name": "x-poser",
                "private": False,
                "visibility": "public",
                "archived": False,
                "fork": False,
                "default_branch": "main",
            },
            {
                "name": "ArchivedExperiment",
                "private": False,
                "visibility": "public",
                "archived": True,
                "fork": False,
                "default_branch": "main",
            },
            {
                "name": "RandomForkedRepo",
                "private": False,
                "visibility": "public",
                "archived": False,
                "fork": True,
                "default_branch": "main",
            },
            {
                "name": "SecretPrivateRepo",
                "private": True,
                "visibility": "private",
                "archived": False,
                "fork": False,
                "default_branch": "main",
            },
            {
                "name": "knowledgeHQ",
                "private": False,
                "visibility": "public",
                "archived": False,
                "fork": False,
                "default_branch": "main",
            },
            {
                "name": "NewPublicAgent",
                "private": False,
                "visibility": "public",
                "archived": False,
                "fork": False,
                "default_branch": "main",
            },
        ]
        readmes = {
            **rfp_connector.DEFAULT_PUBLIC_READMES,
            "NewPublicAgent": (
                "# NewPublicAgent\n\n"
                "NewPublicAgent is a public KnowB prototype for testing live source-grounded "
                "agent workflows during short builder sessions."
            ),
        }
        catalogue = rfp_connector.build_project_rfp_catalogue(
            repo_metadata=metadata,
            readme_fetcher=lambda name, branch: readmes.get(name),
        )
        rfp_ids = [item["rfp_id"] for item in catalogue["rfps"]]
        self.assertEqual(rfp_ids.count("x-poser"), 1)
        self.assertNotIn("ascii-video-chat", rfp_ids)
        self.assertNotIn("archivedexperiment", rfp_ids)
        self.assertNotIn("randomforkedrepo", rfp_ids)
        self.assertNotIn("secretprivaterepo", rfp_ids)
        self.assertNotIn("knowledgehq", rfp_ids)
        self.assertIn("newpublicagent", rfp_ids)

        new_entry = next(
            item for item in catalogue["rfps"] if item["rfp_id"] == "newpublicagent"
        )
        self.assertEqual(new_entry["brief_status"], "grounded")
        self.assertEqual(
            new_entry["readme_url"],
            "https://github.com/knowb-ai/NewPublicAgent/blob/main/README.md",
        )

    def test_unavailable_or_insufficient_readme_marks_brief_pending(self) -> None:
        catalogue = rfp_connector.build_project_rfp_catalogue(
            readme_fetcher=lambda name, branch: "# Too short" if name == "BetterLover" else None,
        )
        by_id = {item["rfp_id"]: item for item in catalogue["rfps"]}

        for project_id in ("x-poser", "betterhackdays", "betterlover", "sepnu-pues"):
            self.assertEqual(by_id[project_id]["brief_status"], "pending")
            self.assertIn("pending", by_id[project_id]["summary"].lower())

    def test_website_rfp_slugs_never_duplicate_discovered_public_repos(self) -> None:
        metadata = [
            *rfp_connector.DEFAULT_PUBLIC_REPO_METADATA,
            {
                "name": "ShadowCaster",
                "private": False,
                "visibility": "public",
                "archived": False,
                "fork": False,
                "default_branch": "main",
            },
            {
                "name": "Precongnition",
                "private": False,
                "visibility": "public",
                "archived": False,
                "fork": False,
                "default_branch": "main",
            },
        ]
        catalogue = rfp_connector.build_project_rfp_catalogue(
            repo_metadata=metadata,
            readme_fetcher=lambda name, branch: rfp_connector.DEFAULT_PUBLIC_READMES.get(name),
        )
        rfp_ids = [item["rfp_id"] for item in catalogue["rfps"]]
        self.assertEqual(rfp_ids.count("shadowcaster"), 1)
        self.assertEqual(rfp_ids.count("precongnition"), 1)


SAMPLE_CLOUD_BUILDER_STACK_CATALOGUE = """# Fun Project and Hackathon Ideas

A broad idea catalogue for hackathons, workshops, and short builder sessions.

---

## 1. Serverless AI, Founder Tools, and Launch Simulation

### 1. FIBE Bench
A serverless evaluation harness for AI agents, RAG systems, and product workflows.

### 24. Faultline
The best name from the launch-combat cluster. It signals hidden structural weakness, pressure, risk, and pre-launch fracture detection.

## 10. Stronger Actual AI System Ideas

### 136. SignalCheck
A name for the creative asset regression system. Its thesis was that creative systems need tests.

### 137. EventSim
A name for event scenario simulation. It would model event risks, dependencies, and operational failures.
"""


class TestWorkPackage3IdeaQualificationAndCatalogue(unittest.TestCase):
    """Work Package 3: Canonical idea catalogue fetch, qualification, and Cloud Builder Stack PR gate."""

    def setUp(self) -> None:
        self.canonical_source = SAMPLE_CLOUD_BUILDER_STACK_CATALOGUE
        _patch_live_public_sources(self)

    def _source_fetcher(self) -> str:
        return self.canonical_source

    def test_fetch_idea_catalogue_returns_ideation_only_suggestions_separate_from_rfps(
        self,
    ) -> None:
        result = rfp_connector.fetch_idea_catalogue(source_fetcher=self._source_fetcher)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entry_type"], "idea_suggestion")
        self.assertTrue(result["ideation_only"])
        self.assertFalse(result["is_active_rfp_list"])
        self.assertFalse(result["is_product_roadmap"])
        self.assertFalse(result["is_commitment_to_build"])
        self.assertEqual(
            result["source_url"],
            "https://github.com/knowb-ai/cloud-builder-stack/blob/main/docs/fun-project-and-hackathon-ideas.md",
        )
        self.assertEqual(result["total_count"], 4)
        self.assertNotIn("rfps", result)
        for idea in result["ideas"]:
            self.assertEqual(idea["entry_type"], "idea_suggestion")
            self.assertTrue(idea["ideation_only"])
            self.assertFalse(idea["is_active_rfp"])

    def test_canonical_source_failure_returns_explicit_unavailable_error_without_stale_copy(
        self,
    ) -> None:
        def failing_fetcher() -> str:
            raise RuntimeError("upstream GitHub 503")

        catalogue_res = rfp_connector.fetch_idea_catalogue(
            source_fetcher=failing_fetcher
        )
        self.assertEqual(catalogue_res["status"], "source_unavailable")
        self.assertEqual(catalogue_res["error_code"], "canonical_source_unavailable")
        self.assertEqual(catalogue_res["ideas"], [])

        qualify_res = rfp_connector.qualify_idea(
            "Session Provenance Guard",
            "Verify agent memory handoff provenance across Hack Day rooms.",
            alignment_evidence="Aligns with KnowB context-aware agents and governance.",
            human_reviewed_rationale="Reviewed by maintainer as a distinct session provenance tool.",
            source_fetcher=failing_fetcher,
        )
        self.assertEqual(qualify_res["status"], "source_unavailable")
        self.assertFalse(qualify_res["eligible"])
        self.assertIn("canonical_source_unavailable", qualify_res["reasons"])

    def test_qualify_unique_aligned_candidate_requires_human_rationale_then_succeeds(
        self,
    ) -> None:
        before = self.canonical_source
        unreviewed = rfp_connector.qualify_idea(
            "Context Checkpoint Ledger",
            "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
            source_fetcher=self._source_fetcher,
        )
        self.assertEqual(unreviewed["status"], "needs_human_review")
        self.assertFalse(unreviewed["eligible"])
        self.assertIn("human_reviewed_rationale_required", unreviewed["reasons"])

        reviewed = rfp_connector.qualify_idea(
            "Context Checkpoint Ledger",
            "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
            human_reviewed_rationale="Reviewed for workshop scope: complements BetterHackdays rooms without duplicating existing catalogue or showcase items.",
            reviewed_by="valiantone",
            source_fetcher=self._source_fetcher,
        )
        self.assertEqual(reviewed["status"], "eligible")
        self.assertTrue(reviewed["eligible"])
        self.assertFalse(reviewed["overlap"]["is_duplicate"])
        self.assertTrue(reviewed["novelty"]["is_novel"])
        self.assertTrue(reviewed["alignment_evidence"]["is_aligned"])
        self.assertEqual(self.canonical_source, before)

    def test_qualify_rejects_duplicates_across_catalogue_public_projects_and_showcase(
        self,
    ) -> None:
        before = self.canonical_source
        for dup_title, dup_summary in (
            (
                "SignalCheck",
                "Creative asset regression testing system for visual identity specs.",
            ),
            (
                "BetterHackdays",
                "Operating system for live Hack Day matchmaking and team workspaces.",
            ),
            (
                "ShadowCaster",
                "Investigate how platform moderation policies affect event visibility.",
            ),
        ):
            res = rfp_connector.qualify_idea(
                dup_title,
                dup_summary,
                alignment_evidence="Matches KnowB agent and builder workflows.",
                human_reviewed_rationale="Human review notes.",
                source_fetcher=self._source_fetcher,
            )
            self.assertEqual(res["status"], "not_eligible")
            self.assertFalse(res["eligible"])
            self.assertTrue(res["overlap"]["is_duplicate"])
            self.assertIn("duplicate_or_overlapping_entry", res["reasons"])
        self.assertEqual(self.canonical_source, before)

    def test_qualify_rejects_unrelated_candidate_and_missing_evidence(self) -> None:
        before = self.canonical_source
        unrelated = rfp_connector.qualify_idea(
            "Arcade Lawn Mower Idle Clicker",
            "Tap the screen to mow virtual lawns and unlock pixelated lawn tractors.",
            alignment_evidence="Uses bright pixel colors on a mobile screen.",
            human_reviewed_rationale="Checked by reviewer.",
            source_fetcher=self._source_fetcher,
        )
        self.assertEqual(unrelated["status"], "not_eligible")
        self.assertFalse(unrelated["eligible"])
        self.assertIn("no_evidenced_alignment", unrelated["reasons"])

        missing_evidence = rfp_connector.qualify_idea(
            "Memory Boundary Inspector",
            "Inspect memory boundaries for agent workflows in team rooms.",
            alignment_evidence="",
            human_reviewed_rationale="Checked by reviewer.",
            source_fetcher=self._source_fetcher,
        )
        self.assertEqual(missing_evidence["status"], "not_eligible")
        self.assertFalse(missing_evidence["eligible"])
        self.assertIn("missing_or_empty_evidence", missing_evidence["reasons"])
        self.assertEqual(self.canonical_source, before)

    def test_alignment_keywords_do_not_match_inside_unrelated_words(self) -> None:
        substring_only = rfp_connector.qualify_idea(
            "Storage Statement Manager",
            "Manages storage statements and artifact streams for average prevent flows.",
            alignment_evidence="Handles storage artifacts, statements, and streams only.",
            human_reviewed_rationale="Checked by reviewer.",
            source_fetcher=self._source_fetcher,
        )
        self.assertEqual(substring_only["status"], "not_eligible")
        self.assertFalse(substring_only["eligible"])
        self.assertEqual(substring_only["alignment_evidence"]["matched_terms"], [])
        self.assertIn("no_evidenced_alignment", substring_only["reasons"])

    def test_ruleset_review_verification_requires_main_target_and_code_owner_rule(
        self,
    ) -> None:
        tag_only = {
            "enforcement": "active",
            "targets": [{"ref": "refs/tags/v*"}],
            "rules": [],
        }
        self.assertFalse(rfp_connector._ruleset_targets_default_branch(tag_only))
        self.assertFalse(rfp_connector._ruleset_requires_code_owner_review(tag_only))

        main_without_code_owner = {
            "enforcement": "active",
            "targets": [{"ref": "~DEFAULT_BRANCH"}],
            "rules": [
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 0,
                        "require_code_owner_review": False,
                    },
                }
            ],
        }
        self.assertTrue(rfp_connector._ruleset_targets_default_branch(main_without_code_owner))
        self.assertFalse(
            rfp_connector._ruleset_requires_code_owner_review(main_without_code_owner)
        )

        enforced = {
            "enforcement": "active",
            "targets": [{"ref": "~DEFAULT_BRANCH"}],
            "rules": [
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 1,
                        "require_code_owner_review": True,
                    },
                }
            ],
        }
        self.assertTrue(rfp_connector._ruleset_targets_default_branch(enforced))
        self.assertTrue(rfp_connector._ruleset_requires_code_owner_review(enforced))

    def test_codeowners_coverage_requires_a_rule_for_the_catalogue_path(self) -> None:
        path = rfp_connector.CANONICAL_IDEA_CATALOGUE_PATH
        owners = rfp_connector.APPROVED_CODEOWNER_OWNERS

        self.assertFalse(
            rfp_connector._codeowners_covers_path("# @valiantone reviews docs\n", path, owners)
        )
        self.assertFalse(
            rfp_connector._codeowners_covers_path("* @someone-else\n", path, owners)
        )
        self.assertFalse(
            rfp_connector._codeowners_covers_path(
                "/docs/other.md @valiantone\n/scripts/kenobi.sh @valiantone\n", path, owners
            )
        )
        self.assertTrue(
            rfp_connector._codeowners_covers_path("* @valiantone\n", path, owners)
        )
        self.assertTrue(
            rfp_connector._codeowners_covers_path(
                "/docs/fun-project-and-hackathon-ideas.md @valiantone\n", path, owners
            )
        )
        self.assertTrue(
            rfp_connector._codeowners_covers_path("docs/* @valiantone\n", path, owners)
        )

    def test_qualification_fails_closed_when_public_showcase_is_unavailable(self) -> None:
        def failing_showcase() -> list[dict[str, Any]]:
            raise RuntimeError("knowb.run source 503")

        result = rfp_connector.qualify_idea(
            "Context Checkpoint Ledger",
            "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents and workshop builder sessions.",
            human_reviewed_rationale="Reviewed by maintainer.",
            source_fetcher=self._source_fetcher,
            showcase_fetcher=failing_showcase,
        )
        self.assertEqual(result["status"], "showcase_unavailable")
        self.assertFalse(result["eligible"])
        self.assertIn("showcase_unavailable", result["reasons"])

        empty_result = rfp_connector.qualify_idea(
            "Context Checkpoint Ledger",
            "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents and workshop builder sessions.",
            human_reviewed_rationale="Reviewed by maintainer.",
            source_fetcher=self._source_fetcher,
            showcase_fetcher=lambda: [],
        )
        self.assertEqual(empty_result["status"], "showcase_unavailable")
        self.assertFalse(empty_result["eligible"])

    def test_proposal_requires_verified_reviewer_identity_and_maintainer_permission(
        self,
    ) -> None:
        base = dict(
            title="Context Checkpoint Ledger",
            summary="Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
            human_reviewed_rationale="Reviewed by maintainer as a distinct session provenance tool.",
            submit=True,
            source_fetcher=self._source_fetcher,
            policy_inspector=lambda: {
                "codeowners_present": True,
                "codeowners_covers_catalogue": True,
                "branch_protection_enforced": True,
                "ruleset_review_enforced": False,
            },
            pr_submitter=lambda preview: {"url": "https://example.test/pr/1", "number": 1},
        )

        missing_reviewer = rfp_connector.propose_idea_catalogue_addition(
            **{**base, "auth_context": self._admin_auth_context()},
        )
        self.assertEqual(missing_reviewer["status"], "reviewer_verification_failed")
        self.assertIn("reviewer_identity_required", missing_reviewer["reasons"])

        mismatched_reviewer = rfp_connector.propose_idea_catalogue_addition(
            **{
                **base,
                "reviewed_by": "someone_else",
                "auth_context": self._admin_auth_context(),
            },
        )
        self.assertEqual(mismatched_reviewer["status"], "reviewer_verification_failed")
        self.assertIn("reviewer_identity_mismatch", mismatched_reviewer["reasons"])

        writer_reviewer = rfp_connector.propose_idea_catalogue_addition(
            **{
                **base,
                "reviewed_by": "valiantone",
                "auth_context": self._admin_auth_context(permission="write"),
            },
        )
        self.assertEqual(writer_reviewer["status"], "reviewer_verification_failed")
        self.assertIn("maintainer_review_required", writer_reviewer["reasons"])

    def test_default_pr_transport_reports_unavailable_without_credentials(
        self,
    ) -> None:
        with patch.dict(
            os.environ, {"KENOBI_GITHUB_TOKEN": "", "GITHUB_TOKEN": ""}
        ):
            result = rfp_connector.propose_idea_catalogue_addition(
                "Context Checkpoint Ledger",
                "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
                alignment_evidence="Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
                human_reviewed_rationale="Reviewed by maintainer as a distinct session provenance tool.",
                reviewed_by="valiantone",
                submit=True,
                source_fetcher=self._source_fetcher,
                policy_inspector=lambda: {
                    "codeowners_present": True,
                    "codeowners_covers_catalogue": True,
                    "branch_protection_enforced": True,
                    "ruleset_review_enforced": False,
                },
                auth_context=self._admin_auth_context(),
            )
        self.assertEqual(result["status"], "submission_transport_unavailable")
        self.assertFalse(result["submitted"])
        self.assertIn("KENOBI_GITHUB_TOKEN", result["error"])

    def _admin_auth_context(self, permission: str = "admin") -> dict[str, Any]:
        return {
            "verified_user": {"login": "valiantone", "id": 4111568, "type": "User"},
            "repo_permissions": {
                "knowb-ai/cloud-builder-stack": permission,
            },
            "bot_installation": {
                "app_slug": "knowb-kenobi",
                "repository_selection": "all",
                "permissions": {
                    "contents": "write",
                    "pull_requests": "write",
                    "issues": "write",
                    "metadata": "read",
                },
            },
        }

    def test_proposal_fetches_catalogue_once_and_uses_highest_idea_number(self) -> None:
        fetch_count = {"count": 0}

        def counting_source() -> str:
            fetch_count["count"] += 1
            return self.canonical_source

        result = rfp_connector.propose_idea_catalogue_addition(
            "Context Checkpoint Ledger",
            "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
            human_reviewed_rationale="Reviewed by maintainer as a distinct session provenance tool.",
            reviewed_by="valiantone",
            source_fetcher=counting_source,
            policy_inspector=lambda: {
                "codeowners_present": True,
                "codeowners_covers_catalogue": True,
                "branch_protection_enforced": True,
                "ruleset_review_enforced": False,
            },
        )
        self.assertEqual(result["status"], "preview_ready")
        self.assertEqual(fetch_count["count"], 1)
        self.assertEqual(result["preview"]["proposed_idea_number"], 138)

    def test_maintainer_approval_gate_blocks_submission_until_enforced_and_updates_only_after_merge(
        self,
    ) -> None:
        before = self.canonical_source
        auth_context = {
            "verified_user": {"login": "valiantone", "id": 4111568, "type": "User"},
            "repo_permissions": {"knowb-ai/cloud-builder-stack": "admin"},
            "bot_installation": {
                "app_slug": "knowb-kenobi",
                "repository_selection": "all",
                "permissions": {
                    "contents": "write",
                    "pull_requests": "write",
                    "issues": "write",
                    "metadata": "read",
                },
            },
        }

        # 1. When effective review rules are not enforced (current state on cloud-builder-stack)
        blocked = rfp_connector.propose_idea_catalogue_addition(
            "Context Checkpoint Ledger",
            "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
            human_reviewed_rationale="Reviewed by maintainer as a distinct session provenance tool.",
            reviewed_by="valiantone",
            submit=True,
            source_fetcher=self._source_fetcher,
            policy_inspector=lambda: {
                "codeowners_present": False,
                "codeowners_covers_catalogue": False,
                "branch_protection_enforced": False,
                "ruleset_review_enforced": False,
            },
            auth_context=auth_context,
        )
        self.assertEqual(blocked["status"], "blocked_by_review_policy")
        self.assertFalse(blocked["submitted"])
        self.assertFalse(blocked["submission_enabled"])
        self.assertFalse(blocked["claims_maintainer_only_approval"])
        self.assertTrue(blocked["source_unchanged"])
        self.assertTrue(blocked["required_admin_settings"])
        self.assertEqual(
            blocked["policy_pr"]["target_repo"],
            "knowb-ai/cloud-builder-stack",
        )
        self.assertEqual(blocked["policy_pr"]["reviewer"], "valiantone")
        self.assertEqual(blocked["policy_pr"]["assignee"], "valiantone")
        self.assertFalse(blocked["policy_pr"]["kenobi_may_merge"])
        self.assertFalse(blocked["policy_pr"]["contains_closing_keywords"])
        self.assertEqual(self.canonical_source, before)

        # 2. When CODEOWNERS + branch protection review rules ARE enforced, PR is submitted (not merged)
        submitted_prs: list[dict[str, Any]] = []

        def fake_pr_submitter(preview: dict[str, Any]) -> dict[str, Any]:
            submitted_prs.append(preview)
            return {
                "url": "https://github.com/knowb-ai/cloud-builder-stack/pull/101",
                "number": 101,
                "state": "open",
            }

        submitted = rfp_connector.propose_idea_catalogue_addition(
            "Context Checkpoint Ledger",
            "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
            alignment_evidence="Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
            human_reviewed_rationale="Reviewed by maintainer as a distinct session provenance tool.",
            reviewed_by="valiantone",
            submit=True,
            source_fetcher=self._source_fetcher,
            policy_inspector=lambda: {
                "codeowners_present": True,
                "codeowners_covers_catalogue": True,
                "branch_protection_enforced": True,
                "ruleset_review_enforced": False,
            },
            auth_context=auth_context,
            pr_submitter=fake_pr_submitter,
        )
        self.assertEqual(submitted["status"], "pr_submitted")
        self.assertTrue(submitted["submitted"])
        self.assertTrue(submitted["source_unchanged"])
        self.assertEqual(submitted["pull_request"]["reviewer"], "valiantone")
        self.assertEqual(submitted["pull_request"]["assignee"], "valiantone")
        self.assertFalse(submitted["pull_request"]["kenobi_may_merge"])
        self.assertFalse(submitted["preview"]["contains_closing_keywords"])
        self.assertFalse(submitted["preview"]["direct_default_branch_write"])
        self.assertFalse(submitted["preview"]["copied_into_betterhackdays"])

        # Canonical source is STILL unchanged while PR is open and unmerged
        self.assertEqual(self.canonical_source, before)
        refetched_before_merge = rfp_connector.fetch_idea_catalogue(
            source_fetcher=self._source_fetcher
        )
        self.assertEqual(refetched_before_merge["total_count"], 4)

        # Simulate human maintainer merging the reviewed PR into Cloud Builder Stack main
        self.canonical_source = (
            self.canonical_source
            + "\n"
            + submitted_prs[0]["proposed_markdown_block"]
        )
        refetched_after_merge = rfp_connector.fetch_idea_catalogue(
            source_fetcher=self._source_fetcher
        )
        self.assertEqual(refetched_after_merge["total_count"], 5)
        self.assertEqual(
            refetched_after_merge["ideas"][-1]["title"],
            "Context Checkpoint Ledger",
        )


class TestWorkPackage4WriteAuthorization(unittest.TestCase):
    """Work Package 4: Caller identity, exact repository permission, bot scope, and owner-only grant checks."""

    def _bot_installation(self, **override_perms: str) -> dict[str, Any]:
        perms = {
            "contents": "write",
            "pull_requests": "write",
            "issues": "write",
            "metadata": "read",
        }
        perms.update(override_perms)
        return {
            "app_slug": "knowb-kenobi",
            "repository_selection": "all",
            "permissions": perms,
        }

    def test_allowed_write_maintain_and_admin_permissions_authorize_mutations(
        self,
    ) -> None:
        for role in ("write", "maintain", "admin"):
            mutations_called: list[str] = []
            res = rfp_connector.execute_authorized_github_mutation(
                operation="pr_edit",
                target_repo="knowb-ai/BetterHackdays",
                expected_target_repo="knowb-ai/BetterHackdays",
                auth_context={
                    "verified_user": {"login": "valiantone", "type": "User"},
                    "repo_permissions": {"knowb-ai/BetterHackdays": role},
                    "bot_installation": self._bot_installation(),
                },
                mutator=lambda auth: mutations_called.append(auth["verified_permission"])
                or {"ok": True},
            )
            self.assertTrue(res["authorized"])
            self.assertTrue(res["mutation_performed"])
            self.assertEqual(mutations_called, [role])

    def test_denied_read_triage_and_none_permissions_never_mutate_even_when_bot_has_write(
        self,
    ) -> None:
        for denied_role in ("read", "triage", "none", ""):
            mutations_called: list[str] = []
            res = rfp_connector.execute_authorized_github_mutation(
                operation="request_submit",
                target_repo="knowb-ai/BetterHackdays",
                asserted_role="admin",  # Caller asserts admin, actual repo permission is denied_role
                auth_context={
                    "verified_user": {"login": "contributor_user", "type": "User"},
                    "repo_permissions": {"knowb-ai/BetterHackdays": denied_role},
                    "bot_installation": self._bot_installation(),
                },
                mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
            )
            self.assertFalse(res["authorized"])
            self.assertFalse(res["mutation_performed"])
            self.assertEqual(res["reason"], "insufficient_repository_permission")
            self.assertEqual(mutations_called, [])

    def test_unknown_identity_and_bot_identity_fail_closed(self) -> None:
        mutations_called: list[str] = []
        for bad_context in (
            None,
            {},
            {"verified_user": {"login": "", "type": "User"}},
            {"verified_user": {"login": "knowb-kenobi[bot]", "type": "Bot", "is_bot": True}},
        ):
            res = rfp_connector.execute_authorized_github_mutation(
                operation="pr_create",
                target_repo="knowb-ai/BetterHackdays",
                auth_context=bad_context,
                mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
            )
            self.assertFalse(res["authorized"])
            self.assertFalse(res["mutation_performed"])
            self.assertEqual(res["reason"], "unknown_identity")
        self.assertEqual(mutations_called, [])

    def test_caller_supplied_identity_spoofing_fails_closed(self) -> None:
        mutations_called: list[str] = []
        spoof_attempt = rfp_connector.execute_authorized_github_mutation(
            operation="request_submit",
            target_repo="knowb-ai/BetterHackdays",
            caller_supplied_login="valiantone",
            auth_context={
                "verified_user": {"login": "actual_caller", "type": "User"},
                "repo_permissions": {"knowb-ai/BetterHackdays": "admin"},
                "bot_installation": self._bot_installation(),
            },
            mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
        )
        self.assertFalse(spoof_attempt["authorized"])
        self.assertFalse(spoof_attempt["mutation_performed"])
        self.assertEqual(spoof_attempt["reason"], "caller_identity_spoofing")
        self.assertEqual(mutations_called, [])

        mismatched_perm_record = rfp_connector.execute_authorized_github_mutation(
            operation="request_submit",
            target_repo="knowb-ai/BetterHackdays",
            auth_context={
                "verified_user": {"login": "actual_caller", "type": "User"},
                "repo_permissions": {
                    "knowb-ai/BetterHackdays": {
                        "login": "valiantone",
                        "permission": "admin",
                    }
                },
                "bot_installation": self._bot_installation(),
            },
            mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
        )
        self.assertFalse(mismatched_perm_record["authorized"])
        self.assertFalse(mismatched_perm_record["mutation_performed"])
        self.assertEqual(mismatched_perm_record["reason"], "caller_identity_spoofing")
        self.assertEqual(mutations_called, [])

    def test_stale_or_failed_identity_and_permission_lookups_fail_closed(self) -> None:
        mutations_called: list[str] = []
        for context, expected_reason in (
            (
                {"identity_lookup_failed": True},
                "stale_or_failed_identity_lookup",
            ),
            (
                {
                    "verified_user": {"login": "valiantone", "type": "User"},
                    "permission_lookup_failed": True,
                },
                "stale_or_failed_permission_lookup",
            ),
            (
                {
                    "verified_user": {"login": "valiantone", "type": "User"},
                    "repo_permissions": {
                        "knowb-ai/BetterHackdays": {
                            "login": "valiantone",
                            "permission": "admin",
                            "stale": True,
                        }
                    },
                    "bot_installation": self._bot_installation(),
                },
                "stale_or_failed_permission_lookup",
            ),
        ):
            res = rfp_connector.execute_authorized_github_mutation(
                operation="pr_edit",
                target_repo="knowb-ai/BetterHackdays",
                auth_context=context,
                mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
            )
            self.assertFalse(res["authorized"])
            self.assertFalse(res["mutation_performed"])
            self.assertEqual(res["reason"], expected_reason)
        self.assertEqual(mutations_called, [])

    def test_bot_installation_missing_scope_or_repo_coverage_fails_closed(self) -> None:
        mutations_called: list[str] = []
        # Missing pull_requests write scope
        res_scope = rfp_connector.execute_authorized_github_mutation(
            operation="catalogue_pr_create",
            target_repo="knowb-ai/cloud-builder-stack",
            auth_context={
                "verified_user": {"login": "valiantone", "type": "User"},
                "repo_permissions": {"knowb-ai/cloud-builder-stack": "admin"},
                "bot_installation": self._bot_installation(pull_requests="read"),
            },
            mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
        )
        self.assertFalse(res_scope["authorized"])
        self.assertFalse(res_scope["mutation_performed"])
        self.assertEqual(res_scope["reason"], "bot_installation_missing_scope")
        self.assertIn("pull_requests:write", res_scope["missing_bot_scopes"])

        # Selected repository list does not include target repo
        res_repo = rfp_connector.execute_authorized_github_mutation(
            operation="issue_create",
            target_repo="knowb-ai/BetterLover",
            auth_context={
                "verified_user": {"login": "valiantone", "type": "User"},
                "repo_permissions": {"knowb-ai/BetterLover": "admin"},
                "bot_installation": {
                    "app_slug": "knowb-kenobi",
                    "repository_selection": "selected",
                    "repositories": ["knowb-ai/BetterHackdays"],
                    "permissions": {"issues": "write"},
                },
            },
            mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
        )
        self.assertFalse(res_repo["authorized"])
        self.assertFalse(res_repo["mutation_performed"])
        self.assertEqual(res_repo["reason"], "bot_installation_missing_scope")
        self.assertEqual(mutations_called, [])

    def test_wrong_repository_mapping_fails_closed(self) -> None:
        mutations_called: list[str] = []
        # BetterHackdays request record must check knowb-ai/BetterHackdays, not another repo
        wrong_req_target = rfp_connector.execute_authorized_github_mutation(
            operation="request_submit",
            target_repo="knowb-ai/BetterLover",
            auth_context={
                "verified_user": {"login": "valiantone", "type": "User"},
                "repo_permissions": {"knowb-ai/BetterLover": "admin"},
                "bot_installation": self._bot_installation(),
            },
            mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
        )
        self.assertFalse(wrong_req_target["authorized"])
        self.assertEqual(wrong_req_target["reason"], "wrong_repository_mapping")

        # Permission verified on BetterHackdays cannot authorize a PR in cloud-builder-stack
        wrong_perm_repo = rfp_connector.execute_authorized_github_mutation(
            operation="catalogue_pr_create",
            target_repo="knowb-ai/cloud-builder-stack",
            auth_context={
                "verified_user": {"login": "valiantone", "type": "User"},
                "repo_permissions": {"knowb-ai/BetterHackdays": "admin"},
                "bot_installation": self._bot_installation(),
            },
            mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
        )
        self.assertFalse(wrong_perm_repo["authorized"])
        self.assertEqual(wrong_perm_repo["reason"], "wrong_repository_mapping")

        # Private/forbidden repo is never allowed
        forbidden_repo = rfp_connector.execute_authorized_github_mutation(
            operation="issue_create",
            target_repo="knowb-ai/knowledgeHQ",
            auth_context={
                "verified_user": {"login": "valiantone", "type": "User"},
                "repo_permissions": {"knowb-ai/knowledgeHQ": "admin"},
                "bot_installation": self._bot_installation(),
            },
            mutator=lambda auth: mutations_called.append("mutated") or {"ok": True},
        )
        self.assertFalse(forbidden_repo["authorized"])
        self.assertEqual(forbidden_repo["reason"], "wrong_repository_mapping")
        self.assertEqual(mutations_called, [])

    def test_owner_only_grant_path_and_denied_grant_cases_never_issue_invitations_in_tests(
        self,
    ) -> None:
        owner_context = {
            "verified_user": {"login": "valiantone", "type": "User"},
            "repo_permissions": {"knowb-ai/BetterHackdays": "admin"},
            "bot_installation": self._bot_installation(administration="write"),
        }

        # 1. Denied without explicit owner confirmation
        unconfirmed = rfp_connector.grant_repository_access(
            target_repo="knowb-ai/BetterHackdays",
            grantee_login="alice_builder",
            permission="write",
            confirmed=False,
            auth_context=owner_context,
        )
        self.assertFalse(unconfirmed["authorized"])
        self.assertEqual(
            unconfirmed["reason"], "explicit_owner_confirmation_required"
        )
        self.assertFalse(unconfirmed["invitation_sent"])

        # 2. Denied when requester tries to grant or elevate their own access
        self_grant = rfp_connector.grant_repository_access(
            target_repo="knowb-ai/BetterHackdays",
            grantee_login="valiantone",
            requester_login="valiantone",
            permission="write",
            confirmed=True,
            auth_context=owner_context,
        )
        self.assertFalse(self_grant["authorized"])
        self.assertEqual(self_grant["reason"], "self_elevation_forbidden")
        self.assertFalse(self_grant["invitation_sent"])

        # 3. Denied when non-owner with write/maintain attempts to grant access
        maintainer_grant = rfp_connector.grant_repository_access(
            target_repo="knowb-ai/BetterHackdays",
            grantee_login="alice_builder",
            permission="write",
            confirmed=True,
            auth_context={
                "verified_user": {"login": "maintainer_user", "type": "User"},
                "repo_permissions": {"knowb-ai/BetterHackdays": "maintain"},
                "bot_installation": self._bot_installation(administration="write"),
            },
        )
        self.assertFalse(maintainer_grant["authorized"])
        self.assertEqual(
            maintainer_grant["reason"], "owner_admin_permission_required"
        )
        self.assertFalse(maintainer_grant["invitation_sent"])

        # 4. Denied when attempting to grant admin role
        admin_grant = rfp_connector.grant_repository_access(
            target_repo="knowb-ai/BetterHackdays",
            grantee_login="alice_builder",
            permission="admin",
            confirmed=True,
            auth_context=owner_context,
        )
        self.assertFalse(admin_grant["authorized"])
        self.assertEqual(
            admin_grant["reason"], "invalid_or_forbidden_permission_level"
        )
        self.assertFalse(admin_grant["invitation_sent"])

        # 5. Allowed owner-only confirmed grant path (dry_run=True in tests so no invitation is issued)
        allowed = rfp_connector.grant_repository_access(
            target_repo="knowb-ai/BetterHackdays",
            grantee_login="alice_builder",
            requester_login="alice_builder",
            permission="write",
            confirmed=True,
            auth_context=owner_context,
            dry_run=True,
        )
        self.assertTrue(allowed["authorized"])
        self.assertEqual(allowed["status"], "approved_dry_run")
        self.assertEqual(allowed["grantee_login"], "alice_builder")
        self.assertEqual(allowed["granted_permission"], "write")
        self.assertFalse(allowed["invitation_sent"])


class TestWorkPackage5RequestsAndDesignResources(unittest.TestCase):
    """Work Package 5: List/read/search/compare RFPs, allowlisted design resources, and preview/submit contributor requests."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/wp5.db"
        survey._SESSIONS.clear()
        init_db()
        _patch_live_public_sources(self)

    def tearDown(self) -> None:
        survey._SESSIONS.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.tmp.cleanup()

    def _auth_context(self, login: str, permission: str) -> dict[str, Any]:
        return {
            "verified_user": {"login": login, "type": "User"},
            "repo_permissions": {"knowb-ai/BetterHackdays": permission},
            "bot_installation": {
                "app_slug": "knowb-kenobi",
                "repository_selection": "all",
                "permissions": {
                    "contents": "write",
                    "pull_requests": "write",
                    "issues": "write",
                    "metadata": "read",
                },
            },
        }

    def _list_requests(self, auth_context: Optional[dict[str, Any]]) -> dict[str, Any]:
        return contributor_request_list_route(auth_context=auth_context)

    def _submit_request(
        self,
        request_type: str,
        rfp_id: str,
        requested_scope: str,
        message: str,
        auth_context: Optional[dict[str, Any]],
        delivery_transport: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        return rfp_connector.submit_contributor_request(
            request_type,
            rfp_id,
            requested_scope,
            message,
            auth_context=auth_context,
            delivery_transport=delivery_transport,
        )

    def test_rfp_list_read_search_compare_across_mcp_and_rest(self) -> None:
        server = mcp_server.create_server(FakeFastMCP)

        listed_mcp = server.tools["list_project_rfps"]["func"]()
        listed_rest = rfps_list_route(visibility=None)
        self.assertEqual(
            [item["rfp_id"] for item in listed_mcp["rfps"]],
            [item["rfp_id"] for item in listed_rest["rfps"]],
        )

        read_mcp = server.tools["read_project_rfp"]["func"]("betterlover")
        read_rest = rfps_read_route("betterlover")
        self.assertEqual(read_mcp["status"], "ok")
        self.assertEqual(read_mcp["rfp"]["title"], "BetterLover")
        self.assertEqual(read_mcp, read_rest)

        # Excluded or private repo lookup fails cleanly
        denied_lookup = rfps_read_route("ascii-video-chat")
        self.assertEqual(denied_lookup["status"], "not_found")
        khq_lookup = rfps_read_route("knowledgeHQ")
        self.assertEqual(khq_lookup["status"], "not_found")

        searched = rfps_search_route(q="subscription", include_design_resources=False)
        self.assertEqual(searched["status"], "ok")
        self.assertEqual([item["rfp_id"] for item in searched["rfps"]], ["subtracktor"])

        compared = rfps_compare_route(
            CompareRfpsRequest(rfp_ids=["betterhackdays", "betterlover", "sepnu-pues"])
        )
        self.assertEqual(compared["status"], "ok")
        self.assertEqual(len(compared["compared"]), 3)

    def test_design_resources_resolve_only_allowlisted_public_website_paths(
        self,
    ) -> None:
        listed = design_resources_list_route()
        self.assertEqual(listed["status"], "ok")
        self.assertFalse(listed["generic_browsing_enabled"])

        allowed_doc = design_resources_read_route(
            DesignResourceReadRequest(path="DESIGN_SYSTEM.md")
        )
        self.assertEqual(allowed_doc["status"], "ok")
        self.assertEqual(
            allowed_doc["resource"]["repo"], "knowb-ai/knowb-ai.github.io"
        )
        self.assertEqual(
            allowed_doc["resource"]["content_source"], "live_repository_file"
        )
        self.assertTrue(allowed_doc["resource"]["content_available"])
        self.assertIn("Autumn", allowed_doc["resource"]["excerpt"])
        self.assertTrue(allowed_doc["resource"]["raw_url"].endswith("/DESIGN_SYSTEM.md"))

        allowed_asset = design_resources_read_route(
            DesignResourceReadRequest(
                path="static/design-system/knowb-autumn-palette.png"
            )
        )
        self.assertEqual(allowed_asset["status"], "ok")
        self.assertEqual(
            allowed_asset["resource"]["content_source"], "allowlisted_binary_asset"
        )
        self.assertEqual(allowed_asset["resource"]["content_type"], "image/png")

        searched = design_resources_search_route(q="WCAG")
        self.assertEqual(searched["status"], "ok")
        self.assertIn(
            "ORGBRAND_GUIDELINES.md",
            [item["path"] for item in searched["matches"]],
        )

        # Unauthorized / non-allowlisted paths and non-website repos are rejected
        for bad_path in (
            ".knowb/project.yml",
            ".claude/settings.json",
            "scripts/kenobi.sh",
            "../BetterHackdays/README.md",
            "templates/index.html",
        ):
            denied = design_resources_read_route(
                DesignResourceReadRequest(path=bad_path)
            )
            self.assertEqual(denied["status"], "denied")
            self.assertEqual(denied["reason"], "path_not_allowlisted")

        wrong_repo = design_resources_read_route(
            DesignResourceReadRequest(
                path="DESIGN_SYSTEM.md",
                repo="knowb-ai/knowledgeHQ",
            )
        )
        self.assertEqual(wrong_repo["status"], "denied")
        self.assertEqual(wrong_repo["reason"], "repository_not_allowlisted")

    def test_preview_versus_submit_for_all_four_request_types_and_privacy_of_stored_requests(
        self,
    ) -> None:
        for req_type in (
            "refinement_draft",
            "expression_of_interest",
            "contribution_access_request",
            "work_elevation_request",
        ):
            preview = contributor_request_preview_route(
                ContributorRequestPreviewInput(
                    request_type=req_type,
                    rfp_id="betterhackdays",
                    requested_scope=f"Pilot scope for {req_type}",
                    message=f"Proposing a concrete vertical slice for {req_type}.",
                )
            )
            self.assertEqual(preview["status"], "preview_ready")
            self.assertFalse(preview["submitted"])
            self.assertFalse(preview["sent"])
            self.assertFalse(preview["grants_repository_access"])
            self.assertEqual(
                preview["preview"]["project"]["rfp_id"], "betterhackdays"
            )
            self.assertEqual(preview["preview"]["recipient"], "ping@knowb.run")
            self.assertEqual(
                preview["preview"]["requested_scope"],
                f"Pilot scope for {req_type}",
            )

        # Preview did not persist any requests
        owner_list_before = self._list_requests(
            self._auth_context("valiantone", "admin")
        )
        self.assertEqual(owner_list_before["requests"], [])

        # Unauthorized submit (read permission) fails closed and stores nothing
        denied_submit = self._submit_request(
            "contribution_access_request",
            "betterhackdays",
            "Write access to branch for Hack Day connector tests",
            "Requesting project-scoped write access for BetterHackdays.",
            self._auth_context("reader_user", "read"),
        )
        self.assertEqual(denied_submit["status"], "unauthorized")
        self.assertFalse(denied_submit["submitted"])
        self.assertFalse(denied_submit["sent"])

        # Authorized submit (write permission on BetterHackdays) stores privately and returns unsent addressed draft when transport is unavailable
        submitted = self._submit_request(
            "work_elevation_request",
            "faultline",
            "Elevate adversarial launch-stress scenario runner",
            "Completed local prototype; requesting owner review to elevate scope.",
            self._auth_context("writer_alice", "write"),
        )
        self.assertEqual(submitted["status"], "submitted_draft_not_sent")
        self.assertTrue(submitted["submitted"])
        self.assertFalse(submitted["sent"])
        self.assertEqual(submitted["delivery_status"], "not_sent")
        self.assertIn("not sent", submitted["delivery_note"].lower())
        self.assertFalse(submitted["is_public"])
        self.assertFalse(submitted["grants_repository_access"])
        self.assertEqual(
            submitted["addressed_draft"]["recipient"], "ping@knowb.run"
        )
        self.assertEqual(
            submitted["addressed_draft"]["project"]["rfp_id"], "faultline"
        )

        # Privacy of stored requests:
        # 1. Unauthenticated caller cannot list requests
        unauth_list = self._list_requests(None)
        self.assertEqual(unauth_list["status"], "unauthorized")
        self.assertEqual(unauth_list["requests"], [])

        # 2. Another user cannot see writer_alice's request
        other_user_list = self._list_requests(
            self._auth_context("writer_bob", "write")
        )
        self.assertEqual(other_user_list["status"], "ok")
        self.assertEqual(other_user_list["requests"], [])

        # 3. writer_alice can see her own request
        alice_list = self._list_requests(
            self._auth_context("writer_alice", "write")
        )
        self.assertEqual(len(alice_list["requests"]), 1)
        self.assertEqual(
            alice_list["requests"][0]["request_id"], submitted["request_id"]
        )

        # 4. BetterHackdays admin (valiantone) can review stored requests
        admin_list = self._list_requests(self._auth_context("valiantone", "admin"))
        self.assertEqual(len(admin_list["requests"]), 1)

        # 5. Public RFP listing never leaks stored contributor requests
        public_rfps = rfps_list_route(visibility=None)
        self.assertNotIn("writer_alice", str(public_rfps))
        self.assertNotIn(submitted["request_id"], str(public_rfps))

        # 6. Configured delivery transport records the request as sent
        delivered = self._submit_request(
            "expression_of_interest",
            "betterhackdays",
            "Run the connector with live public sources",
            "Interested in piloting the connector against live public repositories.",
            self._auth_context("writer_alice", "write"),
            delivery_transport=lambda payload: {"sent": True},
        )
        self.assertEqual(delivered["status"], "submitted")
        self.assertTrue(delivered["sent"])
        self.assertEqual(delivered["delivery_status"], "sent")
        self.assertEqual(
            delivered["addressed_draft"]["recipient"], "ping@knowb.run"
        )

    def test_request_listing_rejects_stale_or_spoofed_auth_contexts(self) -> None:
        submitted = self._submit_request(
            "expression_of_interest",
            "betterlover",
            "Care planning pilot with synthetic cycle data",
            "Interested in the private care planning pilot.",
            self._auth_context("writer_alice", "write"),
        )
        self.assertEqual(submitted["status"], "submitted_draft_not_sent")

        a = self._auth_context("reader_user", "read")

        stale_identity = {**a, "identity_stale": True}
        res = self._list_requests(stale_identity)
        self.assertEqual(res["status"], "unauthorized")
        self.assertEqual(res["reason"], "stale_or_failed_identity_lookup")
        self.assertEqual(res["requests"], [])

        failed_permission = {**a, "permission_lookup_failed": True}
        res = self._list_requests(failed_permission)
        self.assertEqual(res["status"], "unauthorized")
        self.assertEqual(res["reason"], "stale_or_failed_permission_lookup")

        stale_permission_entry = {
            "verified_user": {"login": "reader_user", "type": "User"},
            "repo_permissions": {
                "knowb-ai/BetterHackdays": {
                    "login": "reader_user",
                    "permission": "admin",
                    "stale": True,
                }
            },
        }
        res = self._list_requests(stale_permission_entry)
        self.assertEqual(res["status"], "unauthorized")
        self.assertEqual(res["reason"], "stale_or_failed_permission_lookup")
        self.assertEqual(res["requests"], [])

        spoofed_owner = {
            "verified_user": {"login": "reader_user", "type": "User"},
            "repo_permissions": {
                "knowb-ai/BetterHackdays": {
                    "login": "valiantone",
                    "permission": "admin",
                }
            },
        }
        res = self._list_requests(spoofed_owner)
        self.assertEqual(res["status"], "unauthorized")
        self.assertEqual(res["reason"], "caller_identity_spoofing")
        self.assertEqual(res["requests"], [])

        bot_identity = {
            "verified_user": {"login": "knowb-kenobi[bot]", "type": "Bot", "is_bot": True},
            "repo_permissions": {"knowb-ai/BetterHackdays": "admin"},
        }
        res = self._list_requests(bot_identity)
        self.assertEqual(res["status"], "unauthorized")
        self.assertEqual(res["reason"], "unknown_identity")
        self.assertEqual(res["requests"], [])


class TestRequestTrustBoundary(unittest.TestCase):
    """HTTP callers cannot supply identity or permission claims in the request body."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/trust.db"
        survey._SESSIONS.clear()
        init_db()
        _patch_live_public_sources(self)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        survey._SESSIONS.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.tmp.cleanup()

    def _forged_admin_body(self) -> dict[str, Any]:
        return {
            "auth_context": {
                "verified_user": {"login": "valiantone", "type": "User"},
                "repo_permissions": {"knowb-ai/BetterHackdays": "admin"},
                "bot_installation": {
                    "app_slug": "knowb-kenobi",
                    "repository_selection": "all",
                    "permissions": {
                        "contents": "write",
                        "pull_requests": "write",
                        "issues": "write",
                    },
                },
            }
        }

    def test_bearer_token_parsing_rejects_other_schemes(self) -> None:
        self.assertEqual(
            rfp_connector._extract_bearer_token("Bearer ghp_example"), "ghp_example"
        )
        self.assertIsNone(rfp_connector._extract_bearer_token("Basic abc123"))
        self.assertIsNone(rfp_connector._extract_bearer_token(""))
        self.assertIsNone(rfp_connector._extract_bearer_token(None))

    def test_http_body_cannot_forge_identity_or_permission(self) -> None:
        submit_resp = self.client.post(
            "/contributor/requests/submit",
            json={
                "request_type": "expression_of_interest",
                "rfp_id": "betterhackdays",
                "requested_scope": "Pilot scope",
                "message": "Attempting to smuggle an admin identity.",
                **self._forged_admin_body(),
            },
        )
        self.assertEqual(submit_resp.status_code, 200)
        submitted = submit_resp.json()
        self.assertEqual(submitted["status"], "unauthorized")
        self.assertFalse(submitted["submitted"])
        self.assertEqual(
            submitted["authorization"]["reason"], "stale_or_failed_identity_lookup"
        )

        list_resp = self.client.post(
            "/contributor/requests/list", json=self._forged_admin_body()
        )
        self.assertEqual(list_resp.status_code, 200)
        listing = list_resp.json()
        self.assertEqual(listing["status"], "unauthorized")
        self.assertEqual(listing["requests"], [])

        propose_resp = self.client.post(
            "/ideas/propose",
            json={
                "title": "Context Checkpoint Ledger",
                "summary": "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
                "alignment_evidence": "Supports KnowB retrieval-backed agents.",
                "human_reviewed_rationale": "Reviewed by maintainer as distinct.",
                "reviewed_by": "valiantone",
                "submit": True,
                **self._forged_admin_body(),
            },
        )
        self.assertEqual(propose_resp.status_code, 200)
        self.assertEqual(propose_resp.json()["status"], "unauthorized")

    def test_http_routes_use_server_resolved_identity(self) -> None:
        import app.main as main_module

        context = {
            "verified_user": {"login": "writer_alice", "type": "User"},
            "repo_permissions": {"knowb-ai/BetterHackdays": "write"},
            "bot_installation": {
                "app_slug": "knowb-kenobi",
                "repository_selection": "all",
                "permissions": {
                    "contents": "write",
                    "pull_requests": "write",
                    "issues": "write",
                    "metadata": "read",
                },
            },
            "auth_source": "request_bearer_token",
        }
        app.dependency_overrides[main_module._request_auth_context_for_betterhackdays] = (
            lambda: context
        )
        try:
            submit_resp = self.client.post(
                "/contributor/requests/submit",
                json={
                    "request_type": "expression_of_interest",
                    "rfp_id": "betterhackdays",
                    "requested_scope": "Pilot scope for live sources",
                    "message": "Interested in piloting the connector.",
                },
            )
            self.assertEqual(submit_resp.status_code, 200)
            self.assertEqual(
                submit_resp.json()["status"], "submitted_draft_not_sent"
            )

            list_resp = self.client.post("/contributor/requests/list")
            self.assertEqual(list_resp.status_code, 200)
            listing = list_resp.json()
            self.assertEqual(listing["status"], "ok")
            self.assertEqual(len(listing["requests"]), 1)
            self.assertEqual(listing["viewer_login"], "writer_alice")
        finally:
            app.dependency_overrides.clear()


class TestWorkPackage6EndToEndMcpAndRestValidation(unittest.TestCase):
    """Work Package 6: End-to-end HTTP TestClient and MCP server integration validation."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/wp6.db"
        survey._SESSIONS.clear()
        init_db()
        _patch_live_public_sources(self)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        survey._SESSIONS.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.tmp.cleanup()

    def test_end_to_end_http_and_mcp_parity_and_privacy_boundaries(self) -> None:
        # 1. Existing REST planner/event contracts remain intact
        ingest_resp = self.client.post(
            "/event/ingest/text",
            json={
                "text": REPRESENTATIVE_EVENT_TEXT,
                "source_label": "WP6 HTTP test",
            },
        )
        self.assertEqual(ingest_resp.status_code, 200)
        ideas_resp = self.client.post(
            "/planner/ideas",
            json={
                "event": ingest_resp.json()["event"],
                "profile": REPRESENTATIVE_PROFILE,
                "topics": ["workspace automation"],
            },
        )
        self.assertEqual(ideas_resp.status_code, 200)
        self.assertEqual(ideas_resp.json()["status"], "ranked")

        # 2. HTTP /rfps and /design-resources
        rfps_resp = self.client.get("/rfps")
        self.assertEqual(rfps_resp.status_code, 200)
        rfps_json = rfps_resp.json()
        self.assertEqual(rfps_json["status"], "ok")
        self.assertNotIn("knowledgehq", str(rfps_json).lower())

        design_ok = self.client.post(
            "/design-resources/read",
            json={"path": "ORGBRAND_GUIDELINES.md"},
        )
        self.assertEqual(design_ok.status_code, 200)
        self.assertEqual(design_ok.json()["status"], "ok")

        design_denied = self.client.post(
            "/design-resources/read",
            json={"path": ".knowb/project.yml"},
        )
        self.assertEqual(design_denied.status_code, 200)
        self.assertEqual(design_denied.json()["status"], "denied")

        # 3. HTTP /ideas/catalogue and /ideas/qualify with mocked canonical source fetch
        with patch.object(
            rfp_connector,
            "fetch_canonical_idea_catalogue_markdown",
            return_value=SAMPLE_CLOUD_BUILDER_STACK_CATALOGUE,
        ):
            cat_resp = self.client.get("/ideas/catalogue")
            self.assertEqual(cat_resp.status_code, 200)
            self.assertEqual(cat_resp.json()["status"], "ok")
            self.assertEqual(cat_resp.json()["entry_type"], "idea_suggestion")

            qual_resp = self.client.post(
                "/ideas/qualify",
                json={
                    "title": "Context Checkpoint Ledger",
                    "summary": "Audit agent memory handoffs and retrieval citations across workshop team sessions.",
                    "alignment_evidence": "Supports KnowB retrieval-backed agents, durable memory checkpoints, and workshop builder sessions.",
                    "human_reviewed_rationale": "Reviewed for workshop scope.",
                    "reviewed_by": "valiantone",
                },
            )
            self.assertEqual(qual_resp.status_code, 200)
            self.assertTrue(qual_resp.json()["eligible"])


if __name__ == "__main__":
    unittest.main()
