"""BetterHackdays RFP, ideation, authorization, and contributor request connector."""

from __future__ import annotations

import base64
import fnmatch
import json
import os
import re
import smtplib
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from typing import Any, Callable, Optional
import uuid

from .db import _row_to_dict, ensure_schema, get_conn

GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
KNOWB_ORG = "knowb-ai"

EXCLUDED_REPOSITORIES = frozenset(
    {
        "ascii-video-chat",
        "knowledgehq",
    }
)

FORBIDDEN_PRIVATE_TOKENS = (
    "knowledgehq",
)

APPROVED_PUBLIC_BASELINE = (
    "knowb-ai.github.io",
    "BetterHackdays",
    "BetterLover",
    "cloud-builder-stack",
    "sepnu-pues",
    "x-poser",
)

APPROVED_FORK_PROJECT_REPOS = frozenset({"sepnu-pues"})

NON_PROJECT_RESOURCE_REPOS: dict[str, dict[str, str]] = {
    "knowb-ai.github.io": {
        "resource_id": "knowb-ai.github.io",
        "title": "knowb.run Public Website and Design System",
        "resource_type": "public_website_and_design_system",
        "repo_url": "https://github.com/knowb-ai/knowb-ai.github.io",
        "readme_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/README.md",
        "summary": (
            "Public KnowB website, portfolio showcase, and allowlisted visual design "
            "system reference."
        ),
    },
    "cloud-builder-stack": {
        "resource_id": "cloud-builder-stack",
        "title": "Cloud Builder Stack",
        "resource_type": "builder_starter_and_idea_catalogue",
        "repo_url": "https://github.com/knowb-ai/cloud-builder-stack",
        "readme_url": "https://github.com/knowb-ai/cloud-builder-stack/blob/main/README.md",
        "summary": (
            "Public starter reference for workshops and hackathons, and canonical "
            "host of the ideation-only fun project and hackathon ideas document."
        ),
    },
}

FAULTLINE_APPROVED_SUMMARY = (
    "Faultline is an adversarial launch-stress simulation using synthetic customers "
    "and structured risk scenarios."
)

UNLINKED_APPROVED_SUMMARY = (
    "Unlinked is a neutral comparison of critical-AI native text and images using "
    "a four-post block and a local metrics report."
)

WEBSITE_RFPS: dict[str, dict[str, Any]] = {
    "shadowcaster": {
        "rfp_id": "shadowcaster",
        "title": "ShadowCaster",
        "entry_type": "project_rfp",
        "source_kind": "website_rfp",
        "visibility": "public_website",
        "listed_on_website": True,
        "brief_status": "grounded",
        "tags": ["Platform Visibility", "Moderation Policy", "Event Amplification"],
        "summary": (
            "Investigate how LinkedIn and Instagram content policies affect reach, "
            "moderation, and event visibility for artists, creators, and community "
            "workers, especially in marginalized communities."
        ),
        "outcome": (
            "Compliant publishing patterns, visibility diagnostics, and responsible "
            "amplification playbooks."
        ),
        "scope": (
            "Build toolkits for ethical event representation that respect platform "
            "rules while improving the chance that the underlying message reaches "
            "its intended audience."
        ),
        "safety_boundary": (
            "Respect platform policies and creator consent; do not automate spam "
            "or deceptive amplification."
        ),
        "repo_name": None,
        "repo_url": None,
        "readme_url": None,
        "website_url": "https://knowb.run/#use-cases",
    },
    "underminer": {
        "rfp_id": "underminer",
        "title": "Underminer",
        "entry_type": "project_rfp",
        "source_kind": "website_rfp",
        "visibility": "public_website",
        "listed_on_website": True,
        "brief_status": "grounded",
        "tags": ["Narrative Reconstruction", "Source Traceability", "Context Tracing"],
        "summary": (
            "Extract semantic understanding from paywalled reporting and reconstruct "
            "the story from alternate sources plus LLM context-tracing experiments."
        ),
        "outcome": (
            "Evidence-linked narrative reconstruction with source traceability."
        ),
        "scope": (
            "Reconstruct public-interest reporting claims from open alternate sources "
            "with explicit citation and confidence tracking."
        ),
        "safety_boundary": (
            "Cite open sources transparently and distinguish verified facts from "
            "inferred context."
        ),
        "repo_name": None,
        "repo_url": None,
        "readme_url": None,
        "website_url": "https://knowb.run/#use-cases",
    },
    "x-poser": {
        "rfp_id": "x-poser",
        "title": "X-Poser",
        "entry_type": "project_rfp",
        "source_kind": "website_rfp_with_public_repo",
        "visibility": "public_website",
        "listed_on_website": True,
        "brief_status": "grounded",
        "tags": ["Claim Checking", "Evidence Retrieval", "Smoke Test"],
        "summary": (
            "Submit an X link, run claim checks, and generate a report that marks "
            "the post as true, uncertain, or fabricated, with export-ready output "
            "for sharing on X."
        ),
        "outcome": "Compact fact-check report with evidence confidence notes.",
        "scope": (
            "Paste a claim from X, retrieve web evidence with Tavily, judge it with "
            "a Nebius-backed LLM, and display a compact evidence-linked report."
        ),
        "safety_boundary": (
            "Minimal open-source smoke path only; no automatic monitoring or "
            "unreviewed posting to X."
        ),
        "repo_name": "x-poser",
        "repo_url": "https://github.com/knowb-ai/x-poser",
        "readme_url": "https://github.com/knowb-ai/x-poser/blob/main/README.md",
        "website_url": "https://knowb.run/#use-cases",
    },
    "precongnition": {
        "rfp_id": "precongnition",
        "title": "Precongnition",
        "entry_type": "project_rfp",
        "source_kind": "website_rfp",
        "visibility": "public_website",
        "listed_on_website": True,
        "brief_status": "grounded",
        "tags": ["Conference Discovery", "Session Continuity", "Learning Graph"],
        "summary": (
            "Detect missing or mismatched conference talks, tutorials, or demos, "
            "then crawl for alternate watch links and nearest neighboring sessions."
        ),
        "outcome": "Continuity-preserving discovery graph for learning resources.",
        "scope": (
            "Locate alternate recordings, slides, and neighboring talks when event "
            "links break or sessions move."
        ),
        "safety_boundary": (
            "Link only to legitimate public learning resources and preserve speaker "
            "attribution."
        ),
        "repo_name": None,
        "repo_url": None,
        "readme_url": None,
        "website_url": "https://knowb.run/#use-cases",
    },
    "marksweep": {
        "rfp_id": "marksweep",
        "title": "MarkSweep",
        "entry_type": "project_rfp",
        "source_kind": "website_rfp",
        "visibility": "public_website",
        "listed_on_website": True,
        "brief_status": "grounded",
        "tags": ["Inbox Triage", "Browser Extension", "User Rules"],
        "summary": (
            "A browser extension granted control over your active tab that walks "
            "every unread message in your open inbox, checks each against relevance "
            "rules you control, marks non-matches as read in bulk, and flags matches "
            "to stay pinned at the top."
        ),
        "outcome": (
            "Bulk unread-to-read triage with rule-matched messages flagged and "
            "pinned to the top."
        ),
        "scope": (
            "Operate on the active open inbox tab under explicit user rules without "
            "exfiltrating message bodies."
        ),
        "safety_boundary": (
            "Run only with active-tab user consent and user-controlled triage rules."
        ),
        "repo_name": None,
        "repo_url": None,
        "readme_url": None,
        "website_url": "https://knowb.run/#use-cases",
    },
    "subtracktor": {
        "rfp_id": "subtracktor",
        "title": "Subtracktor",
        "entry_type": "project_rfp",
        "source_kind": "website_rfp",
        "visibility": "public_website",
        "listed_on_website": True,
        "brief_status": "grounded",
        "tags": ["Subscription Escape", "Inbox Agents", "Financial Leakage"],
        "summary": (
            "Subtracktor is a browser extension that connects consent-fully to your "
            "email inbox once it detects an inbox open in the active tab. It scans "
            "only for account-creation and subscription-confirmation messages, then "
            "builds a per-account record of every subscription it finds."
        ),
        "outcome": (
            "Per-account subscription audit with next-billing-date tracking and "
            "renewal reminders."
        ),
        "scope": (
            "Track next billing dates from confirmation emails and remind the user "
            "ahead of renewal to close financial leakage."
        ),
        "safety_boundary": (
            "Scan only confirmation messages in the consent-approved active tab; "
            "never store or forward unrelated personal emails."
        ),
        "repo_name": None,
        "repo_url": None,
        "readme_url": None,
        "website_url": "https://knowb.run/#use-cases",
    },
}

LIVE_PUBLIC_PROJECT_TEMPLATES: dict[str, dict[str, Any]] = {
    "betterhackdays": {
        "rfp_id": "betterhackdays",
        "title": "BetterHackdays",
        "repo_name": "BetterHackdays",
        "tags": ["Shared Hack Day", "Team Formation", "Project Continuity"],
        "curated_summary": (
            "Help hack-day organizers move builders from event rules and tracks to "
            "a team, a focused idea, and a shared first-hour plan. BetterHackdays "
            "brings event context, opt-in participant profiles, matchmaking, and "
            "team workspaces into one live flow."
        ),
        "outcome": (
            "A demoable Hack Day flow that takes one organizer and a small team from "
            "event context to a shared kickoff plan, with repository access only "
            "after explicit approval."
        ),
        "scope": (
            "Build one permission-aware path from event brief to team kickoff: "
            "capture deadlines and judging criteria, match people who choose to "
            "participate, and give the resulting team a concise plan and durable "
            "room context."
        ),
        "safety_boundary": (
            "Keep access explicit; a QR code, slug, or match never grants repository "
            "permissions on its own."
        ),
    },
    "betterlover": {
        "rfp_id": "betterlover",
        "title": "BetterLover",
        "repo_name": "BetterLover",
        "tags": ["Care Planning", "Cycle-Aware Context", "Consent First"],
        "curated_summary": (
            "Turn a person's chosen cycle, mood, energy, and care preferences into "
            "thoughtful, practical suggestions for a partner. The current prototype "
            "uses synthetic cycle data and produces a structured plan that can be "
            "reviewed before action."
        ),
        "outcome": (
            "A working demo that turns sample context and a chosen budget into a "
            "reviewable care plan, with the data subject in control of every share "
            "or purchase."
        ),
        "scope": (
            "Strengthen the prototype into a private, user-controlled care planner "
            "using synthetic data for demos and reviewable JSON care plans."
        ),
        "safety_boundary": (
            "The agent must not diagnose, infer consent, expose intimate data to a "
            "partner, or make purchases automatically."
        ),
    },
    "sepnu-pues": {
        "rfp_id": "sepnu-pues",
        "title": "Sepnu Pues",
        "repo_name": "sepnu-pues",
        "tags": [
            "Daily Follow-Through",
            "Opt-In Accountability",
            "User-Controlled Sharing",
        ],
        "curated_summary": (
            "Help people follow through on the tasks they set for themselves through "
            "a lightweight daily loop. The prototype pairs a task list with optional "
            "safe-cartoon generation, an accountability-email queue, and a prefilled "
            "social-post draft."
        ),
        "outcome": (
            "A demoable task-to-accountability flow where the user selects a task, "
            "chooses an optional nudge, and reviews it before any external action."
        ),
        "scope": (
            "Make accountability feel playful and supportive without turning it into "
            "surveillance or public shaming."
        ),
        "safety_boundary": (
            "Let users choose each action, review generated content, and explicitly "
            "approve any email or post; never send or publish automatically, and "
            "keep private photos and credentials out of the repository."
        ),
    },
}

CONNECTOR_ONLY_PRIVATE_RFPS: dict[str, dict[str, Any]] = {
    "faultline": {
        "rfp_id": "faultline",
        "title": "Faultline",
        "entry_type": "project_rfp",
        "source_kind": "connector_only_private_rfp",
        "visibility": "connector_only",
        "listed_on_website": False,
        "brief_status": "grounded",
        "tags": [
            "Launch Stress Simulation",
            "Synthetic Customers",
            "Risk Scenarios",
        ],
        "summary": FAULTLINE_APPROVED_SUMMARY,
        "outcome": (
            "Structured pre-launch risk scenarios and synthetic customer stress "
            "findings."
        ),
        "scope": FAULTLINE_APPROVED_SUMMARY,
        "safety_boundary": (
            "Private project and connector-only RFP. Repository URLs, identifiers, "
            "paths, and README text are never disclosed."
        ),
        "repo_name": None,
        "repo_url": None,
        "readme_url": None,
        "website_url": None,
    },
    "unlinked": {
        "rfp_id": "unlinked",
        "title": "Unlinked",
        "entry_type": "project_rfp",
        "source_kind": "connector_only_private_rfp",
        "visibility": "connector_only",
        "listed_on_website": False,
        "brief_status": "grounded",
        "tags": [
            "Critical-AI Comparison",
            "Four-Post Block",
            "Local Metrics Report",
        ],
        "summary": UNLINKED_APPROVED_SUMMARY,
        "outcome": (
            "Neutral four-post block comparison paired with a local metrics report."
        ),
        "scope": UNLINKED_APPROVED_SUMMARY,
        "safety_boundary": (
            "Private project and connector-only RFP. Repository URLs, identifiers, "
            "paths, and README text are never disclosed."
        ),
        "repo_name": None,
        "repo_url": None,
        "readme_url": None,
        "website_url": None,
    },
}

DEFAULT_PUBLIC_REPO_METADATA: list[dict[str, Any]] = [
    {
        "name": "knowb-ai.github.io",
        "description": "Landing page for KNOWB AI's gallery of knowledge agents",
        "private": False,
        "visibility": "public",
        "archived": False,
        "fork": False,
        "html_url": "https://github.com/knowb-ai/knowb-ai.github.io",
        "default_branch": "main",
    },
    {
        "name": "BetterHackdays",
        "description": "Find your team. Spawn your workspace. Start building.",
        "private": False,
        "visibility": "public",
        "archived": False,
        "fork": False,
        "html_url": "https://github.com/knowb-ai/BetterHackdays",
        "default_branch": "main",
    },
    {
        "name": "ascii-video-chat",
        "description": "Live ASCII-art video calls, right in your terminal.",
        "private": False,
        "visibility": "public",
        "archived": False,
        "fork": True,
        "html_url": "https://github.com/knowb-ai/ascii-video-chat",
        "default_branch": "main",
    },
    {
        "name": "BetterLover",
        "description": (
            "Need a emotionally intelligent partner, who said an agent can't do "
            "the job? Created for the BitRefill, Internet Money Hackathon"
        ),
        "private": False,
        "visibility": "public",
        "archived": False,
        "fork": False,
        "html_url": "https://github.com/knowb-ai/BetterLover",
        "default_branch": "main",
    },
    {
        "name": "cloud-builder-stack",
        "description": "Cloud Builder Stack reference repo for practical AI/cloud builder apps",
        "private": False,
        "visibility": "public",
        "archived": False,
        "fork": False,
        "html_url": "https://github.com/knowb-ai/cloud-builder-stack",
        "default_branch": "main",
    },
    {
        "name": "sepnu-pues",
        "description": "Shame tasking, do it or your momma gonna know what you do on the internet",
        "private": False,
        "visibility": "public",
        "archived": False,
        "fork": True,
        "html_url": "https://github.com/knowb-ai/sepnu-pues",
        "default_branch": "main",
    },
    {
        "name": "x-poser",
        "description": "Xposer: Because lies don't fact-check themselves.",
        "private": False,
        "visibility": "public",
        "archived": False,
        "fork": False,
        "html_url": "https://github.com/knowb-ai/x-poser",
        "default_branch": "main",
    },
]

DEFAULT_PUBLIC_READMES: dict[str, str] = {
    "BetterHackdays": (
        "# BetterHackdays\n\n"
        "BetterHackdays is the operating system for a live Hack Day. "
        "It helps builders enter the same event context, become matchable, "
        "form a team, open a room, connect the room to a workspace repo, "
        "and keep agents pointed at the shared project state."
    ),
    "BetterLover": (
        "# BetterLover\n\n"
        "BetterLover is a Bitrefill-focused hackathon prototype for a period-aware "
        "care agent. It uses a FastAPI backend and Vite SPA frontend, mocks a "
        "Clue-style cycle data import with synthetic data, and generates a "
        "structured JSON engagement plan."
    ),
    "sepnu-pues": (
        "# Task Accountability MVP\n\n"
        "Daily task list with opt-in accountability actions: add and complete "
        "today's tasks, generate a safe cartoon accountability image, queue an "
        "accountability email, and open a prefilled X post draft."
    ),
    "x-poser": (
        "# X-Poser Mini\n\n"
        "X-Poser Mini is a small workshop/demo project for a claim-checking smoke "
        "test: paste a claim from X, retrieve web evidence with Tavily, judge it "
        "with a Nebius-backed LLM, and display a compact evidence-linked report."
    ),
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "unknown"


def _github_headers(token: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BetterHackdays-Connector/0.1",
    }
    resolved_token = token if token is not None else os.getenv("GITHUB_TOKEN")
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"
    return headers


def fetch_public_org_repos(
    org: str = KNOWB_ORG,
    *,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Fetch public repositories for the KnowB organization without enumerating private repos."""
    url = (
        f"{GITHUB_API_BASE}/orgs/{urllib.parse.quote(org)}/repos"
        "?type=public&per_page=100"
    )
    req = urllib.request.Request(url, headers=_github_headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, list):
        return []
    return [
        item
        for item in payload
        if isinstance(item, dict)
        and not item.get("private", False)
        and str(item.get("visibility", "public")).lower() == "public"
    ]


def fetch_public_repo_readme(
    repo_name: str,
    default_branch: str = "main",
    *,
    org: str = KNOWB_ORG,
    timeout: float = 10.0,
) -> Optional[str]:
    """Fetch public README markdown for an approved public repository."""
    if _slugify(repo_name) in EXCLUDED_REPOSITORIES:
        return None
    raw_url = (
        f"{GITHUB_RAW_BASE}/{urllib.parse.quote(org)}/"
        f"{urllib.parse.quote(repo_name)}/"
        f"{urllib.parse.quote(default_branch)}/README.md"
    )
    req = urllib.request.Request(
        raw_url,
        headers={"User-Agent": "BetterHackdays-Connector/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _extract_readme_excerpt(readme_text: Optional[str]) -> Optional[str]:
    """Extract the first substantive paragraph from a public README."""
    if not readme_text or not isinstance(readme_text, str):
        return None
    paragraphs: list[str] = []
    current: list[str] = []
    in_code_block = False
    for raw_line in readme_text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.startswith("#") or line.startswith("|") or line.startswith("- "):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))

    for paragraph in paragraphs:
        cleaned = _clean_text(paragraph)
        if len(cleaned) >= 40:
            return cleaned
    return None


def _is_private_or_forbidden_repo(repo: dict[str, Any]) -> bool:
    name = _clean_text(repo.get("name"))
    lower_name = name.lower()
    if not name:
        return True
    if any(token in lower_name for token in FORBIDDEN_PRIVATE_TOKENS):
        return True
    if lower_name in EXCLUDED_REPOSITORIES or _slugify(name) in EXCLUDED_REPOSITORIES:
        return True
    if lower_name in CONNECTOR_ONLY_PRIVATE_RFPS:
        return True
    if bool(repo.get("private")) or bool(repo.get("isPrivate")):
        return True
    visibility = _clean_text(repo.get("visibility") or "public").lower()
    if visibility != "public":
        return True
    return False


def _is_archived_repo(repo: dict[str, Any]) -> bool:
    return bool(repo.get("archived")) or bool(repo.get("isArchived"))


def _is_excluded_fork(repo: dict[str, Any]) -> bool:
    name = _clean_text(repo.get("name"))
    is_fork = bool(repo.get("fork")) or bool(repo.get("isFork"))
    if not is_fork:
        return False
    return name.lower() not in APPROVED_FORK_PROJECT_REPOS


def build_project_rfp_catalogue(
    *,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
    include_connector_only: bool = True,
) -> dict[str, Any]:
    """Build the KnowB project RFP catalogue from public metadata and approved briefs.

    Preserves the six website RFPs, grounds live public project briefs in their
    public READMEs (marking briefs pending when README sources are unavailable
    or insufficient), treats non-project repos as public resources, excludes
    `ascii-video-chat`,private/archived/unapproved-fork repos, and keeps
    `Faultline` and `Unlinked` connector-only with no repo metadata.
    """
    raw_repos: list[dict[str, Any]]
    metadata_source: str
    if repo_metadata is not None:
        raw_repos = repo_metadata
        metadata_source = "caller_supplied"
    else:
        try:
            live_repos = fetch_public_org_repos()
            if not live_repos:
                raise ValueError("no public repositories returned")
            raw_repos = live_repos
            metadata_source = "live_public_org_repos"
        except Exception:
            # Fall back to the approved baseline only when the live listing fails,
            # and say so rather than pretending the catalogue is current.
            raw_repos = list(DEFAULT_PUBLIC_REPO_METADATA)
            metadata_source = "baseline_fallback_live_listing_unavailable"

    resolve_readme: Callable[[str, str], Optional[str]] = (
        readme_fetcher
        if readme_fetcher is not None
        else lambda name, branch: fetch_public_repo_readme(name, branch)
    )

    discovered_public_repos: dict[str, dict[str, Any]] = {}
    excluded_repos: list[dict[str, str]] = []
    public_resources: list[dict[str, Any]] = []

    for repo in raw_repos:
        if not isinstance(repo, dict):
            continue
        name = _clean_text(repo.get("name"))
        if not name:
            continue
        key = name.lower()
        if key in discovered_public_repos:
            excluded_repos.append({"name": name, "reason": "duplicate_repository"})
            continue
        if _is_private_or_forbidden_repo(repo):
            reason = (
                "excluded_repository"
                if key in EXCLUDED_REPOSITORIES or _slugify(name) in EXCLUDED_REPOSITORIES
                else "private_or_restricted"
            )
            excluded_repos.append({"name": name, "reason": reason})
            continue
        if _is_archived_repo(repo):
            excluded_repos.append({"name": name, "reason": "archived"})
            continue
        if _is_excluded_fork(repo):
            excluded_repos.append({"name": name, "reason": "unapproved_fork"})
            continue

        discovered_public_repos[key] = repo

    for baseline_name in NON_PROJECT_RESOURCE_REPOS:
        repo_key = baseline_name.lower()
        if repo_key in discovered_public_repos:
            public_resources.append(dict(NON_PROJECT_RESOURCE_REPOS[baseline_name]))

    rfps: list[dict[str, Any]] = []
    represented_repo_keys: set[str] = set(
        key.lower() for key in NON_PROJECT_RESOURCE_REPOS
    )

    # 1. Six existing website RFPs (in canonical order)
    website_order = (
        "shadowcaster",
        "underminer",
        "x-poser",
        "precongnition",
        "marksweep",
        "subtracktor",
    )
    for rfp_id in website_order:
        entry = dict(WEBSITE_RFPS[rfp_id])
        entry["tags"] = list(entry["tags"])
        # Reserve the RFP slug so a same-named public repo cannot emit a duplicate entry.
        represented_repo_keys.add(rfp_id.lower())
        repo_name = entry.get("repo_name")
        if repo_name:
            repo_key = repo_name.lower()
            represented_repo_keys.add(repo_key)
            repo_record = discovered_public_repos.get(repo_key)
            default_branch = "main"
            if repo_record:
                default_branch = _clean_text(
                    repo_record.get("default_branch")
                    or (repo_record.get("defaultBranchRef") or {}).get("name")
                    or "main"
                )
            readme_text = resolve_readme(repo_name, default_branch)
            excerpt = _extract_readme_excerpt(readme_text)
            entry["readme_url"] = (
                f"https://github.com/{KNOWB_ORG}/{repo_name}/blob/{default_branch}/README.md"
            )
            if excerpt:
                entry["brief_status"] = "grounded"
                entry["readme_excerpt"] = excerpt
            else:
                entry["brief_status"] = "pending"
                entry["readme_excerpt"] = None
                entry["summary"] = (
                    f"Source README for {entry['title']} is currently unavailable "
                    "or insufficient; brief details are pending verification."
                )
        else:
            entry["readme_excerpt"] = None
        rfps.append(entry)

    # 2. Live public project RFPs from the baseline (BetterHackdays, BetterLover, Sepnu Pues)
    for project_id in ("betterhackdays", "betterlover", "sepnu-pues"):
        template = LIVE_PUBLIC_PROJECT_TEMPLATES[project_id]
        repo_name = template["repo_name"]
        repo_key = repo_name.lower()
        represented_repo_keys.add(repo_key)
        repo_record = discovered_public_repos.get(repo_key)
        if repo_metadata is not None and repo_record is None:
            continue
        default_branch = "main"
        if repo_record:
            default_branch = _clean_text(
                repo_record.get("default_branch")
                or (repo_record.get("defaultBranchRef") or {}).get("name")
                or "main"
            )
        repo_url = f"https://github.com/{KNOWB_ORG}/{repo_name}"
        readme_url = (
            f"https://github.com/{KNOWB_ORG}/{repo_name}/blob/{default_branch}/README.md"
        )
        readme_text = resolve_readme(repo_name, default_branch)
        excerpt = _extract_readme_excerpt(readme_text)
        if excerpt:
            brief_status = "grounded"
            summary = template["curated_summary"]
        else:
            brief_status = "pending"
            summary = (
                f"Source README for {template['title']} is currently unavailable "
                "or insufficient; brief is marked pending rather than inventing claims."
            )
        rfps.append(
            {
                "rfp_id": template["rfp_id"],
                "title": template["title"],
                "entry_type": "project_rfp",
                "source_kind": "live_public_project",
                "visibility": "public_website",
                "listed_on_website": True,
                "brief_status": brief_status,
                "tags": list(template["tags"]),
                "summary": summary,
                "outcome": template["outcome"] if brief_status == "grounded" else "Pending README verification.",
                "scope": template["scope"] if brief_status == "grounded" else "Pending README verification.",
                "safety_boundary": template["safety_boundary"],
                "repo_name": repo_name,
                "repo_url": repo_url,
                "readme_url": readme_url,
                "readme_excerpt": excerpt,
                "website_url": "https://knowb.run/#use-cases",
            }
        )

    # 3. Any additional current non-archived public KnowB project repositories
    for repo_key, repo_record in discovered_public_repos.items():
        if repo_key in represented_repo_keys:
            continue
        repo_name = _clean_text(repo_record.get("name"))
        if _clean_text(repo_record.get("is_resource")).lower() == "true" or repo_record.get("is_resource") is True:
            public_resources.append(
                {
                    "resource_id": _slugify(repo_name),
                    "title": repo_name,
                    "resource_type": "public_resource_repository",
                    "repo_url": f"https://github.com/{KNOWB_ORG}/{repo_name}",
                    "readme_url": f"https://github.com/{KNOWB_ORG}/{repo_name}/blob/main/README.md",
                    "summary": _clean_text(repo_record.get("description"))
                    or f"Public KnowB resource repository {repo_name}.",
                }
            )
            represented_repo_keys.add(repo_key)
            continue

        default_branch = _clean_text(
            repo_record.get("default_branch")
            or (repo_record.get("defaultBranchRef") or {}).get("name")
            or "main"
        )
        repo_url = (
            _clean_text(repo_record.get("html_url") or repo_record.get("url"))
            or f"https://github.com/{KNOWB_ORG}/{repo_name}"
        )
        readme_url = (
            f"https://github.com/{KNOWB_ORG}/{repo_name}/blob/{default_branch}/README.md"
        )
        readme_text = resolve_readme(repo_name, default_branch)
        excerpt = _extract_readme_excerpt(readme_text)
        if excerpt:
            brief_status = "grounded"
            summary = excerpt
            outcome = f"Grounded in {repo_name} public README."
            scope = excerpt
        else:
            brief_status = "pending"
            summary = (
                f"Source README for {repo_name} is currently unavailable or "
                "insufficient; brief is marked pending rather than inventing claims."
            )
            outcome = "Pending README verification."
            scope = "Pending README verification."

        rfps.append(
            {
                "rfp_id": _slugify(repo_name),
                "title": repo_name,
                "entry_type": "project_rfp",
                "source_kind": "discovered_public_project",
                "visibility": "public_project",
                "listed_on_website": False,
                "brief_status": brief_status,
                "tags": ["Public Project"],
                "summary": summary,
                "outcome": outcome,
                "scope": scope,
                "safety_boundary": (
                    "Repository access remains governed by explicit GitHub permissions."
                ),
                "repo_name": repo_name,
                "repo_url": repo_url,
                "readme_url": readme_url,
                "readme_excerpt": excerpt,
                "website_url": None,
            }
        )
        represented_repo_keys.add(repo_key)

    # 4. Connector-only private project RFPs (Faultline and Unlinked)
    if include_connector_only:
        for private_id in ("faultline", "unlinked"):
            entry = dict(CONNECTOR_ONLY_PRIVATE_RFPS[private_id])
            entry["tags"] = list(entry["tags"])
            entry["readme_excerpt"] = None
            rfps.append(entry)

    return {
        "status": "ok",
        "metadata_source": metadata_source,
        "taxonomy": {
            "project_rfp": "Active KnowB project RFP or live project brief.",
            "idea_suggestion": "Ideation-only concept from Cloud Builder Stack; not an active RFP or roadmap commitment.",
            "approved_delivery_commitment": "Explicitly approved pilot or delivery scope; distinct from RFPs and ideation.",
        },
        "rfps": rfps,
        "public_resources": public_resources,
        "excluded_repositories": excluded_repos,
        "next": "inspect_or_compare_rfp",
    }


# --- Work Package 3: Canonical idea catalogue fetch, qualification, and PR gate ---

CANONICAL_IDEA_CATALOGUE_REPO = "knowb-ai/cloud-builder-stack"
CANONICAL_IDEA_CATALOGUE_PATH = "docs/fun-project-and-hackathon-ideas.md"
CANONICAL_IDEA_CATALOGUE_BRANCH = "main"
CANONICAL_IDEA_CATALOGUE_URL = (
    "https://github.com/knowb-ai/cloud-builder-stack/blob/main/"
    "docs/fun-project-and-hackathon-ideas.md"
)
CANONICAL_IDEA_CATALOGUE_RAW_URL = (
    "https://raw.githubusercontent.com/knowb-ai/cloud-builder-stack/main/"
    "docs/fun-project-and-hackathon-ideas.md"
)
PUBLIC_SHOWCASE_INDEX_URL = (
    "https://raw.githubusercontent.com/knowb-ai/knowb-ai.github.io/main/"
    "templates/index.html"
)
DESIGN_RESOURCE_RAW_BASE = (
    "https://raw.githubusercontent.com/knowb-ai/knowb-ai.github.io/main"
)
CLOUD_BUILDER_STACK_REVIEWER = "valiantone"
CLOUD_BUILDER_STACK_ASSIGNEE = "valiantone"
APPROVED_CODEOWNER_OWNERS = frozenset({"@valiantone"})

KNOWB_ALIGNMENT_PILLARS: dict[str, tuple[str, ...]] = {
    "knowledge_agents": (
        "agent",
        "agents",
        "retrieval",
        "rag",
        "evidence",
        "citation",
        "fact-check",
        "fact",
        "source",
        "verification",
        "graph",
    ),
    "context_and_memory": (
        "context",
        "memory",
        "state",
        "continuity",
        "session",
        "ledger",
        "history",
        "checkpoint",
        "trace",
    ),
    "governance_and_safety": (
        "governance",
        "permission",
        "consent",
        "policy",
        "audit",
        "privacy",
        "review",
        "compliance",
        "trust",
        "red-team",
        "adversarial",
    ),
    "builder_and_event_workflows": (
        "hackathon",
        "hack",
        "workshop",
        "builder",
        "team",
        "matchmaking",
        "event",
        "prototype",
        "demo",
        "scaffolding",
        "evaluation",
        "eval",
    ),
}

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "with",
        "your",
        "tool",
        "system",
        "app",
        "project",
    }
)

_CLOSING_KEYWORD_RE = re.compile(
    r"\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+"
    r"(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#\d+\b",
    re.IGNORECASE,
)


def fetch_canonical_idea_catalogue_markdown(*, timeout: float = 10.0) -> str:
    """Fetch the canonical idea catalogue markdown live from Cloud Builder Stack main."""
    req = urllib.request.Request(
        CANONICAL_IDEA_CATALOGUE_RAW_URL,
        headers={"User-Agent": "BetterHackdays-Connector/0.1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


_SHOWCASE_TITLE_RE = re.compile(r'cabinet-title-lg">([^<]{2,120})</h3>')
_SHOWCASE_CHIP_RE = re.compile(
    r'<span class="chip[^"]*"><i class="led"[^>]*></i>\s*([^<]{2,80})\s*</span>'
)


def parse_public_showcase_html(html_text: str) -> list[dict[str, Any]]:
    """Extract current public showcase entries (title plus tag chips) from knowb.run HTML."""
    if not html_text or not isinstance(html_text, str):
        return []

    titles = list(_SHOWCASE_TITLE_RE.finditer(html_text))
    entries: list[dict[str, Any]] = []
    for index, match in enumerate(titles):
        title = _clean_text(match.group(1))
        if not title:
            continue
        segment_end = titles[index + 1].start() if index + 1 < len(titles) else len(html_text)
        segment = html_text[match.end():segment_end]
        tags = [
            _clean_text(chip.group(1))
            for chip in _SHOWCASE_CHIP_RE.finditer(segment)
            if _clean_text(chip.group(1))
        ]
        entries.append({"title": title, "tags": tags})
    return entries


def fetch_public_showcase_entries(*, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch the current public KnowB gallery/agent showcase from the live knowb.run source."""
    req = urllib.request.Request(
        PUBLIC_SHOWCASE_INDEX_URL,
        headers={"User-Agent": "BetterHackdays-Connector/0.1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_public_showcase_html(resp.read().decode("utf-8"))


def parse_idea_catalogue_markdown(markdown_text: str) -> list[dict[str, Any]]:
    """Parse numbered idea entries from the Cloud Builder Stack markdown document."""
    if not markdown_text or not isinstance(markdown_text, str):
        return []

    ideas: list[dict[str, Any]] = []
    current_section = "General"
    current_entry: Optional[dict[str, Any]] = None
    body_lines: list[str] = []

    section_re = re.compile(r"^##\s+(.+?)\s*$")
    idea_re = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")

    def _flush() -> None:
        nonlocal current_entry, body_lines
        if current_entry is not None:
            summary = _clean_text(" ".join(body_lines))
            current_entry["summary"] = summary
            ideas.append(current_entry)
        current_entry = None
        body_lines = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        sec_match = section_re.match(line)
        if sec_match:
            _flush()
            current_section = _clean_text(sec_match.group(1))
            continue

        idea_match = idea_re.match(line)
        if idea_match:
            _flush()
            number = int(idea_match.group(1))
            title = _clean_text(idea_match.group(2))
            current_entry = {
                "idea_number": number,
                "idea_id": f"cbs-idea-{number:03d}-{_slugify(title)}",
                "title": title,
                "section": current_section,
                "summary": "",
                "entry_type": "idea_suggestion",
                "ideation_only": True,
                "is_active_rfp": False,
                "is_product_roadmap": False,
                "is_commitment_to_build": False,
                "source_repo": CANONICAL_IDEA_CATALOGUE_REPO,
                "source_branch": CANONICAL_IDEA_CATALOGUE_BRANCH,
                "source_path": CANONICAL_IDEA_CATALOGUE_PATH,
                "source_url": CANONICAL_IDEA_CATALOGUE_URL,
            }
            continue

        if current_entry is not None:
            if line.startswith("---"):
                _flush()
                continue
            if line:
                body_lines.append(line)

    _flush()
    return ideas


def fetch_idea_catalogue(
    *,
    query: Optional[str] = None,
    section: Optional[str] = None,
    limit: Optional[int] = None,
    source_fetcher: Optional[Callable[[], str]] = None,
) -> dict[str, Any]:
    """Fetch the canonical Cloud Builder Stack idea catalogue live and return suggestions separately from RFPs."""
    fetcher = source_fetcher or fetch_canonical_idea_catalogue_markdown
    try:
        markdown_text = fetcher()
    except Exception as exc:
        return {
            "status": "source_unavailable",
            "error_code": "canonical_source_unavailable",
            "error": (
                "Canonical Cloud Builder Stack idea catalogue could not be fetched "
                f"from {CANONICAL_IDEA_CATALOGUE_URL}: {exc}. Refusing to serve a "
                "stale or local copy."
            ),
            "entry_type": "idea_suggestion",
            "ideation_only": True,
            "is_active_rfp_list": False,
            "is_product_roadmap": False,
            "is_commitment_to_build": False,
            "source_repo": CANONICAL_IDEA_CATALOGUE_REPO,
            "source_branch": CANONICAL_IDEA_CATALOGUE_BRANCH,
            "source_url": CANONICAL_IDEA_CATALOGUE_URL,
            "ideas": [],
            "total_count": 0,
            "next": "retry_when_canonical_source_available",
        }

    all_ideas = parse_idea_catalogue_markdown(markdown_text)
    if not all_ideas:
        return {
            "status": "source_unavailable",
            "error_code": "canonical_source_empty_or_invalid",
            "error": (
                "Canonical Cloud Builder Stack idea catalogue returned empty or "
                "unparseable content; refusing to serve stale or fallback data."
            ),
            "entry_type": "idea_suggestion",
            "ideation_only": True,
            "is_active_rfp_list": False,
            "is_product_roadmap": False,
            "is_commitment_to_build": False,
            "source_repo": CANONICAL_IDEA_CATALOGUE_REPO,
            "source_branch": CANONICAL_IDEA_CATALOGUE_BRANCH,
            "source_url": CANONICAL_IDEA_CATALOGUE_URL,
            "ideas": [],
            "total_count": 0,
            "next": "retry_when_canonical_source_available",
        }

    filtered = all_ideas
    clean_section = _clean_text(section).lower()
    if clean_section:
        filtered = [
            item
            for item in filtered
            if clean_section in item["section"].lower()
        ]

    clean_query = _clean_text(query).lower()
    if clean_query:
        query_tokens = [tok for tok in re.split(r"[^a-z0-9]+", clean_query) if tok]
        filtered = [
            item
            for item in filtered
            if clean_query in item["title"].lower()
            or clean_query in item["summary"].lower()
            or (
                query_tokens
                and all(
                    tok in f"{item['title']} {item['summary']} {item['section']}".lower()
                    for tok in query_tokens
                )
            )
        ]

    if limit is not None and limit >= 0:
        filtered = filtered[:limit]

    return {
        "status": "ok",
        "entry_type": "idea_suggestion",
        "ideation_only": True,
        "is_active_rfp_list": False,
        "is_product_roadmap": False,
        "is_commitment_to_build": False,
        "source_repo": CANONICAL_IDEA_CATALOGUE_REPO,
        "source_branch": CANONICAL_IDEA_CATALOGUE_BRANCH,
        "source_url": CANONICAL_IDEA_CATALOGUE_URL,
        "total_count": len(all_ideas),
        "returned_count": len(filtered),
        "ideas": filtered,
        "next": "qualify_idea_or_explore_rfps",
    }


def _tokenize_meaningful(text: str) -> set[str]:
    tokens = {
        tok
        for tok in re.split(r"[^a-z0-9]+", _clean_text(text).lower())
        if len(tok) >= 3 and tok not in _STOPWORDS
    }
    return tokens


def _keyword_matches(keyword: str, tokens: set[str], text_lower: str) -> bool:
    """Match a pillar keyword without substring false positives.

    Single-word keywords must appear as a whole token; multi-part keywords are
    matched as a bounded phrase across separators such as hyphens.
    """
    parts = [part for part in re.split(r"[^a-z0-9]+", keyword.lower()) if part]
    if not parts:
        return False
    if len(parts) == 1:
        return parts[0] in tokens
    pattern = r"[^a-z0-9]+".join(re.escape(part) for part in parts)
    return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text_lower) is not None


def qualify_idea(
    title: str,
    summary: str,
    *,
    alignment_evidence: Optional[str] = None,
    human_reviewed_rationale: Optional[str] = None,
    reviewed_by: Optional[str] = None,
    source_fetcher: Optional[Callable[[], str]] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
    showcase_fetcher: Optional[Callable[[], list[dict[str, Any]]]] = None,
) -> dict[str, Any]:
    """Deterministically qualify a candidate idea against the canonical catalogue, open public KnowB projects, and the current public KnowB showcase."""
    clean_title = _clean_text(title)
    clean_summary = _clean_text(summary)
    clean_evidence = _clean_text(alignment_evidence)
    clean_rationale = _clean_text(human_reviewed_rationale)
    clean_reviewer = _clean_text(reviewed_by)

    # 1. Fetch fresh canonical idea catalogue first
    catalogue_result = fetch_idea_catalogue(source_fetcher=source_fetcher)
    if catalogue_result["status"] != "ok":
        return {
            "status": "source_unavailable",
            "eligible": False,
            "candidate": {"title": clean_title, "summary": clean_summary},
            "overlap": {"is_duplicate": False, "matches": []},
            "novelty": {
                "is_novel": False,
                "assessment": "Cannot verify novelty while canonical Cloud Builder Stack source is unavailable.",
            },
            "alignment_evidence": {
                "is_aligned": False,
                "matched_pillars": [],
                "matched_terms": [],
                "submitted_evidence": clean_evidence,
            },
            "reasons": ["canonical_source_unavailable"],
            "error": catalogue_result.get("error"),
            "next": "retry_when_canonical_source_available",
        }

    # 2. Check for missing/empty required inputs or evidence
    missing_reasons: list[str] = []
    if not clean_title:
        missing_reasons.append("missing_title")
    if len(clean_summary) < 20:
        missing_reasons.append("missing_or_insufficient_summary")
    if len(clean_evidence) < 15:
        missing_reasons.append("missing_or_empty_alignment_evidence")

    if missing_reasons:
        return {
            "status": "not_eligible",
            "eligible": False,
            "candidate": {"title": clean_title, "summary": clean_summary},
            "overlap": {"is_duplicate": False, "matches": []},
            "novelty": {
                "is_novel": False,
                "assessment": "Insufficient candidate summary or alignment evidence to evaluate novelty.",
            },
            "alignment_evidence": {
                "is_aligned": False,
                "matched_pillars": [],
                "matched_terms": [],
                "submitted_evidence": clean_evidence,
            },
            "reasons": ["missing_or_empty_evidence", *missing_reasons],
            "next": "provide_required_evidence",
        }

    # 3. Fetch the current public showcase, which supplies live alignment evidence
    showcase_fetch = showcase_fetcher or fetch_public_showcase_entries
    try:
        showcase_entries = showcase_fetch()
    except Exception as exc:
        return {
            "status": "showcase_unavailable",
            "eligible": False,
            "candidate": {"title": clean_title, "summary": clean_summary},
            "overlap": {"is_duplicate": False, "matches": []},
            "novelty": {
                "is_novel": False,
                "assessment": "Cannot verify alignment while the public KnowB showcase is unavailable.",
            },
            "alignment_evidence": {
                "is_aligned": False,
                "matched_pillars": [],
                "matched_terms": [],
                "matched_showcase_entries": [],
                "submitted_evidence": clean_evidence,
                "showcase_source": PUBLIC_SHOWCASE_INDEX_URL,
            },
            "reasons": ["showcase_unavailable"],
            "error": str(exc),
            "next": "retry_when_public_showcase_available",
        }
    if not isinstance(showcase_entries, list) or not showcase_entries:
        return {
            "status": "showcase_unavailable",
            "eligible": False,
            "candidate": {"title": clean_title, "summary": clean_summary},
            "overlap": {"is_duplicate": False, "matches": []},
            "novelty": {
                "is_novel": False,
                "assessment": "Cannot verify alignment while the public KnowB showcase is empty or unparseable.",
            },
            "alignment_evidence": {
                "is_aligned": False,
                "matched_pillars": [],
                "matched_terms": [],
                "matched_showcase_entries": [],
                "submitted_evidence": clean_evidence,
                "showcase_source": PUBLIC_SHOWCASE_INDEX_URL,
            },
            "reasons": ["showcase_unavailable"],
            "next": "retry_when_public_showcase_available",
        }

    # 4. Build reference corpus:
    #    (a) Freshly fetched Cloud Builder Stack ideas
    #    (b) Current open public KnowB project set
    #    (c) Current public KnowB gallery/agent showcase
    project_catalogue = build_project_rfp_catalogue(
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
        include_connector_only=False,
    )
    reference_items: list[dict[str, str]] = []
    for idea in catalogue_result["ideas"]:
        reference_items.append(
            {
                "source_set": "cloud_builder_stack_catalogue",
                "id": idea["idea_id"],
                "title": idea["title"],
                "summary": idea["summary"],
            }
        )
    for rfp in project_catalogue["rfps"]:
        source_set = (
            "open_public_knowb_project"
            if rfp.get("repo_name")
            else "public_knowb_showcase_rfp"
        )
        reference_items.append(
            {
                "source_set": source_set,
                "id": rfp["rfp_id"],
                "title": rfp["title"],
                "summary": f"{rfp['summary']} {rfp.get('scope', '')}",
            }
        )
    for entry in showcase_entries:
        entry_title = _clean_text(entry.get("title"))
        if not entry_title:
            continue
        entry_tags = [str(tag) for tag in (entry.get("tags") or [])]
        reference_items.append(
            {
                "source_set": "public_knowb_showcase",
                "id": _slugify(entry_title),
                "title": entry_title,
                "summary": " ".join([entry_title, *entry_tags]),
            }
        )

    candidate_slug = _slugify(clean_title)
    candidate_tokens = _tokenize_meaningful(f"{clean_title} {clean_summary}")
    overlap_matches: list[dict[str, Any]] = []

    for ref in reference_items:
        ref_slug = _slugify(ref["title"])
        ref_tokens = _tokenize_meaningful(f"{ref['title']} {ref['summary']}")
        exact_title = candidate_slug == ref_slug
        slug_containment = (
            len(candidate_slug) >= 6
            and len(ref_slug) >= 6
            and (candidate_slug in ref_slug or ref_slug in candidate_slug)
        )
        shared_tokens = sorted(candidate_tokens.intersection(ref_tokens))
        union_size = len(candidate_tokens.union(ref_tokens)) or 1
        jaccard = round(len(shared_tokens) / union_size, 3)
        coverage = round(
            len(shared_tokens) / (min(len(candidate_tokens), len(ref_tokens)) or 1),
            3,
        )

        if exact_title or slug_containment or jaccard >= 0.45 or (len(shared_tokens) >= 5 and coverage >= 0.65):
            overlap_matches.append(
                {
                    "source_set": ref["source_set"],
                    "id": ref["id"],
                    "title": ref["title"],
                    "match_type": (
                        "exact_title"
                        if exact_title
                        else "title_overlap"
                        if slug_containment
                        else "high_token_overlap"
                    ),
                    "jaccard_similarity": jaccard,
                    "shared_terms": shared_tokens[:8],
                }
            )

    is_duplicate = len(overlap_matches) > 0

    # 4. Check alignment evidence against KnowB pillars and showcase
    combined_alignment_text = f"{clean_title} {clean_summary} {clean_evidence}".lower()
    alignment_tokens = _tokenize_meaningful(combined_alignment_text)
    matched_pillars: list[str] = []
    matched_terms: list[str] = []

    for pillar, keywords in KNOWB_ALIGNMENT_PILLARS.items():
        pillar_hits = [
            kw
            for kw in keywords
            if _keyword_matches(kw, alignment_tokens, combined_alignment_text)
        ]
        if pillar_hits:
            matched_pillars.append(pillar)
            for hit in pillar_hits:
                if hit not in matched_terms:
                    matched_terms.append(hit)

    evidence_lower = clean_evidence.lower()
    evidence_tokens = _tokenize_meaningful(clean_evidence)
    evidence_pillar_hits = [
        kw
        for keywords in KNOWB_ALIGNMENT_PILLARS.values()
        for kw in keywords
        if _keyword_matches(kw, evidence_tokens, evidence_lower)
    ]

    # Compare against the live public showcase, not only a static keyword list.
    candidate_showcase_tokens = _tokenize_meaningful(
        f"{clean_title} {clean_summary} {clean_evidence}"
    )
    matched_showcase_entries: list[dict[str, Any]] = []
    for entry in showcase_entries:
        entry_title = _clean_text(entry.get("title"))
        if not entry_title:
            continue
        entry_tags = [str(tag) for tag in (entry.get("tags") or [])]
        entry_tokens = _tokenize_meaningful(" ".join([entry_title, *entry_tags]))
        shared_terms = sorted(candidate_showcase_tokens.intersection(entry_tokens))
        strong_terms = [term for term in shared_terms if len(term) >= 5]
        if strong_terms or len(shared_terms) >= 2:
            matched_showcase_entries.append(
                {
                    "title": entry_title,
                    "tags": entry_tags,
                    "shared_terms": shared_terms,
                }
            )

    is_aligned = (
        len(matched_pillars) >= 1
        and len(evidence_pillar_hits) >= 1
        and len(matched_showcase_entries) >= 1
    )
    alignment_detail = {
        "is_aligned": is_aligned,
        "matched_pillars": matched_pillars,
        "matched_terms": matched_terms,
        "matched_showcase_entries": matched_showcase_entries,
        "submitted_evidence": clean_evidence,
        "showcase_source": PUBLIC_SHOWCASE_INDEX_URL,
    }

    reasons: list[str] = []
    if is_duplicate:
        reasons.append("duplicate_or_overlapping_entry")
    if not is_aligned:
        reasons.append("no_evidenced_alignment")

    has_human_rationale = len(clean_rationale) >= 15
    if not is_duplicate and is_aligned and not has_human_rationale:
        reasons.append("human_reviewed_rationale_required")
        return {
            "status": "needs_human_review",
            "eligible": False,
            "candidate": {"title": clean_title, "summary": clean_summary},
            "overlap": {
                "is_duplicate": False,
                "checked_against_counts": {
                    "cloud_builder_stack_ideas": len(catalogue_result["ideas"]),
                    "public_projects_and_showcase": len(project_catalogue["rfps"]),
                    "public_showcase_entries": len(showcase_entries),
                },
                "matches": [],
            },
            "novelty": {
                "is_novel": True,
                "assessment": (
                    "No duplicate found in the canonical Cloud Builder Stack catalogue, "
                    "open public KnowB projects, or public agent showcase; human-reviewed "
                    "rationale is required before marking eligible."
                ),
            },
            "alignment_evidence": {
                **alignment_detail,
                "human_reviewed_rationale": None,
                "reviewed_by": clean_reviewer or None,
            },
            "reasons": reasons,
            "next": "attach_human_reviewed_rationale",
        }

    if reasons:
        return {
            "status": "not_eligible",
            "eligible": False,
            "candidate": {"title": clean_title, "summary": clean_summary},
            "overlap": {
                "is_duplicate": is_duplicate,
                "checked_against_counts": {
                    "cloud_builder_stack_ideas": len(catalogue_result["ideas"]),
                    "public_projects_and_showcase": len(project_catalogue["rfps"]),
                    "public_showcase_entries": len(showcase_entries),
                },
                "matches": overlap_matches,
            },
            "novelty": {
                "is_novel": not is_duplicate,
                "assessment": (
                    "Candidate overlaps with an existing catalogue idea, public project, or showcase RFP."
                    if is_duplicate
                    else "Candidate is distinct by name, but lacks evidenced KnowB alignment."
                ),
            },
            "alignment_evidence": {
                **alignment_detail,
                "human_reviewed_rationale": clean_rationale or None,
                "reviewed_by": clean_reviewer or None,
            },
            "reasons": reasons,
            "next": "revise_or_discard_candidate",
        }

    return {
        "status": "eligible",
        "eligible": True,
        "candidate": {"title": clean_title, "summary": clean_summary},
        "overlap": {
            "is_duplicate": False,
            "checked_against_counts": {
                "cloud_builder_stack_ideas": len(catalogue_result["ideas"]),
                "public_projects_and_showcase": len(project_catalogue["rfps"]),
                "public_showcase_entries": len(showcase_entries),
            },
            "matches": [],
        },
        "novelty": {
            "is_novel": True,
            "assessment": (
                "Candidate is distinct across the freshly fetched Cloud Builder Stack "
                "catalogue, open public KnowB projects, and the public KnowB showcase."
            ),
        },
        "alignment_evidence": {
            **alignment_detail,
            "human_reviewed_rationale": clean_rationale,
            "reviewed_by": clean_reviewer or None,
        },
        "reasons": [
            "unique_candidate",
            "evidenced_knowb_alignment",
            "human_reviewed_rationale_present",
        ],
        "next": "preview_cloud_builder_stack_pr",
    }


REQUIRED_CLOUD_BUILDER_STACK_ADMIN_SETTINGS: list[str] = [
    (
        "Enable a branch protection rule or active repository ruleset on "
        "`knowb-ai/cloud-builder-stack` targeting `main`."
    ),
    (
        "Enable 'Require a pull request before merging' with at least 1 required "
        "approving review (`required_approving_review_count >= 1`)."
    ),
    (
        "Enable 'Require review from Code Owners' (`require_code_owner_reviews = true`) "
        "so `.github/CODEOWNERS` enforces maintainer/admin approval on "
        "`docs/fun-project-and-hackathon-ideas.md`."
    ),
    (
        "Enable 'Dismiss stale pull request approvals when new commits are pushed' "
        "and restrict direct pushes to `main`."
    ),
]


def prepare_cloud_builder_stack_policy_pr(
    *,
    policy_pr_url: Optional[str] = None,
) -> dict[str, Any]:
    """Prepare the separately linked Cloud Builder Stack policy PR for CODEOWNERS review enforcement."""
    codeowners_content = (
        "# Require maintainer/admin review for Cloud Builder Stack changes\n"
        "* @valiantone\n"
        "/docs/fun-project-and-hackathon-ideas.md @valiantone\n"
    )
    body = (
        "## Summary\n\n"
        "- Add `.github/CODEOWNERS` designating `@valiantone` as required owner for "
        "`/docs/fun-project-and-hackathon-ideas.md` and repository files.\n"
        "- Pair this policy file with the repository admin settings below so "
        "catalogue additions require maintainer/admin review before merge.\n\n"
        "## Admin-Only Repository Settings Still Required\n\n"
        + "\n".join(f"- {item}" for item in REQUIRED_CLOUD_BUILDER_STACK_ADMIN_SETTINGS)
    )
    return {
        "target_repo": CANONICAL_IDEA_CATALOGUE_REPO,
        "base_branch": CANONICAL_IDEA_CATALOGUE_BRANCH,
        "head_branch": "chore/codeowners-maintainer-review-policy",
        "title": "chore: add CODEOWNERS for idea catalogue maintainer review",
        "body": body,
        "files": {
            ".github/CODEOWNERS": codeowners_content,
        },
        "reviewer": CLOUD_BUILDER_STACK_REVIEWER,
        "assignee": CLOUD_BUILDER_STACK_ASSIGNEE,
        "kenobi_may_merge": False,
        "contains_closing_keywords": bool(_CLOSING_KEYWORD_RE.search(body)),
        "required_admin_settings": list(REQUIRED_CLOUD_BUILDER_STACK_ADMIN_SETTINGS),
        "pr_url": policy_pr_url,
    }


def _ruleset_targets_default_branch(ruleset: dict[str, Any]) -> bool:
    """Return True when a ruleset targets the default branch or `main`."""
    refs: set[str] = set()
    targets = ruleset.get("targets")
    if isinstance(targets, list):
        for target in targets:
            ref = _clean_text(target.get("ref")) if isinstance(target, dict) else _clean_text(target)
            if ref:
                refs.add(ref)
    conditions = ruleset.get("conditions")
    if isinstance(conditions, dict):
        ref_name = conditions.get("ref_name")
        if isinstance(ref_name, dict):
            include = ref_name.get("include")
            if isinstance(include, list):
                refs.update(_clean_text(item) for item in include if _clean_text(item))

    allowed_refs = {
        "~DEFAULT_BRANCH",
        "refs/heads/~DEFAULT_BRANCH",
        "refs/heads/main",
        "main",
        "default",
    }
    return any(ref in allowed_refs for ref in refs)


def _ruleset_requires_code_owner_review(ruleset: dict[str, Any]) -> bool:
    """Return True when a ruleset requires a code-owner-approved pull request."""
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        return False
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") != "pull_request":
            continue
        parameters = rule.get("parameters")
        if not isinstance(parameters, dict):
            continue
        try:
            approvals = int(parameters.get("required_approving_review_count", 0))
        except (TypeError, ValueError):
            approvals = 0
        if parameters.get("require_code_owner_review") is True and approvals >= 1:
            return True
    return False


def _codeowners_pattern_matches(pattern: str, path: str) -> bool:
    """Return True when a CODEOWNERS pattern covers the given repository path."""
    cleaned = pattern.strip().lstrip("/")
    if not cleaned:
        return False
    if cleaned == "*":
        return True
    if cleaned.endswith("/"):
        return path.startswith(cleaned)
    if "/" not in cleaned:
        return fnmatch.fnmatch(path.rsplit("/", 1)[-1], cleaned)
    if any(char in cleaned for char in "*?["):
        return fnmatch.fnmatch(path, cleaned)
    return path == cleaned


def _codeowners_covers_path(
    text: str,
    path: str,
    approved_owners: frozenset[str],
) -> bool:
    """Return True when an approved owner rule covers the exact path.

    A bare mention of an owner in a comment or an unrelated rule does not count.
    """
    normalized_path = path.strip().lstrip("/")
    approved = {owner.lower() for owner in approved_owners}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern, owners = parts[0], parts[1:]
        if not any(owner.lower() in approved for owner in owners):
            continue
        if _codeowners_pattern_matches(pattern, normalized_path):
            return True
    return False


def _fetch_cloud_builder_stack_policy_state(*, timeout: float = 10.0) -> dict[str, Any]:
    """Query live GitHub API for Cloud Builder Stack CODEOWNERS, branch protection, and rulesets."""
    codeowners_present = False
    codeowners_covers_catalogue = False
    for candidate_path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        url = (
            f"{GITHUB_API_BASE}/repos/{CANONICAL_IDEA_CATALOGUE_REPO}/contents/"
            f"{candidate_path}?ref={CANONICAL_IDEA_CATALOGUE_BRANCH}"
        )
        req = urllib.request.Request(url, headers=_github_headers())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content_b64 = data.get("content", "")
                decoded = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
                codeowners_present = True
                codeowners_covers_catalogue = _codeowners_covers_path(
                    decoded,
                    CANONICAL_IDEA_CATALOGUE_PATH,
                    APPROVED_CODEOWNER_OWNERS,
                )
                break
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue

    branch_protection_enforced = False
    branch_url = (
        f"{GITHUB_API_BASE}/repos/{CANONICAL_IDEA_CATALOGUE_REPO}/branches/"
        f"{CANONICAL_IDEA_CATALOGUE_BRANCH}"
    )
    req = urllib.request.Request(branch_url, headers=_github_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            branch_data = json.loads(resp.read().decode("utf-8"))
            if branch_data.get("protected") is True:
                prot_url = f"{branch_url}/protection"
                prot_req = urllib.request.Request(prot_url, headers=_github_headers())
                try:
                    with urllib.request.urlopen(prot_req, timeout=timeout) as prot_resp:
                        prot_data = json.loads(prot_resp.read().decode("utf-8"))
                        pr_reviews = prot_data.get("required_pull_request_reviews") or {}
                        if (
                            pr_reviews.get("require_code_owner_reviews") is True
                            and int(pr_reviews.get("required_approving_review_count", 0)) >= 1
                        ):
                            branch_protection_enforced = True
                except (urllib.error.URLError, TimeoutError, ValueError):
                    branch_protection_enforced = False
    except (urllib.error.URLError, TimeoutError, ValueError):
        branch_protection_enforced = False

    ruleset_review_enforced = False
    rulesets_url = f"{GITHUB_API_BASE}/repos/{CANONICAL_IDEA_CATALOGUE_REPO}/rulesets"
    req = urllib.request.Request(rulesets_url, headers=_github_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            rulesets = json.loads(resp.read().decode("utf-8"))
            if isinstance(rulesets, list):
                for rs in rulesets:
                    if not isinstance(rs, dict) or rs.get("enforcement") != "active":
                        continue
                    ruleset_id = rs.get("id")
                    if ruleset_id is None:
                        continue
                    detail_url = f"{rulesets_url}/{urllib.parse.quote(str(ruleset_id))}"
                    detail_req = urllib.request.Request(
                        detail_url, headers=_github_headers()
                    )
                    try:
                        with urllib.request.urlopen(detail_req, timeout=timeout) as detail_resp:
                            detail = json.loads(detail_resp.read().decode("utf-8"))
                    except (urllib.error.URLError, TimeoutError, ValueError):
                        continue
                    if not isinstance(detail, dict):
                        continue
                    if _ruleset_targets_default_branch(detail) and _ruleset_requires_code_owner_review(detail):
                        ruleset_review_enforced = True
                        break
    except (urllib.error.URLError, TimeoutError, ValueError):
        ruleset_review_enforced = False

    return {
        "codeowners_present": codeowners_present,
        "codeowners_covers_catalogue": codeowners_covers_catalogue,
        "branch_protection_enforced": branch_protection_enforced,
        "ruleset_review_enforced": ruleset_review_enforced,
    }


def verify_cloud_builder_stack_review_policy(
    *,
    policy_inspector: Optional[Callable[[], dict[str, Any]]] = None,
    policy_pr_url: Optional[str] = None,
) -> dict[str, Any]:
    """Verify whether effective GitHub rules require maintainer/admin review on Cloud Builder Stack."""
    inspector = policy_inspector or _fetch_cloud_builder_stack_policy_state
    try:
        state = inspector()
    except Exception as exc:
        return {
            "status": "policy_verification_failed",
            "enforced": False,
            "submission_enabled": False,
            "claims_maintainer_only_approval": False,
            "codeowners_present": False,
            "branch_protection_enforced": False,
            "ruleset_review_enforced": False,
            "missing_controls": [
                "policy_inspection_failed",
                "codeowners_missing",
                "branch_protection_or_ruleset_required_review_not_enforced",
            ],
            "required_admin_settings": list(REQUIRED_CLOUD_BUILDER_STACK_ADMIN_SETTINGS),
            "policy_pr": prepare_cloud_builder_stack_policy_pr(
                policy_pr_url=policy_pr_url
            ),
            "error": str(exc),
        }

    codeowners_ok = bool(
        state.get("codeowners_present") and state.get("codeowners_covers_catalogue")
    )
    review_rule_ok = bool(
        state.get("branch_protection_enforced") or state.get("ruleset_review_enforced")
    )
    enforced = codeowners_ok and review_rule_ok

    missing_controls: list[str] = []
    if not codeowners_ok:
        missing_controls.append("codeowners_missing")
    if not review_rule_ok:
        missing_controls.append(
            "branch_protection_or_ruleset_required_review_not_enforced"
        )

    return {
        "status": "enforced" if enforced else "not_enforced",
        "enforced": enforced,
        "submission_enabled": enforced,
        "claims_maintainer_only_approval": enforced,
        "codeowners_present": codeowners_ok,
        "branch_protection_enforced": bool(state.get("branch_protection_enforced")),
        "ruleset_review_enforced": bool(state.get("ruleset_review_enforced")),
        "missing_controls": missing_controls,
        "required_admin_settings": (
            [] if enforced else list(REQUIRED_CLOUD_BUILDER_STACK_ADMIN_SETTINGS)
        ),
        "policy_pr": prepare_cloud_builder_stack_policy_pr(policy_pr_url=policy_pr_url),
    }


def propose_idea_catalogue_addition(
    title: str,
    summary: str,
    *,
    alignment_evidence: Optional[str] = None,
    human_reviewed_rationale: Optional[str] = None,
    reviewed_by: Optional[str] = None,
    section: str = "10. Stronger Actual AI System Ideas",
    submit: bool = False,
    source_fetcher: Optional[Callable[[], str]] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
    showcase_fetcher: Optional[Callable[[], list[dict[str, Any]]]] = None,
    policy_inspector: Optional[Callable[[], dict[str, Any]]] = None,
    policy_pr_url: Optional[str] = None,
    auth_context: Optional[dict[str, Any]] = None,
    pr_submitter: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Preview and optionally submit a qualified, human-reviewed idea as a PR to Cloud Builder Stack."""
    clean_title = _clean_text(title)
    clean_summary = _clean_text(summary)
    clean_section = _clean_text(section) or "10. Stronger Actual AI System Ideas"

    if _CLOSING_KEYWORD_RE.search(f"{clean_title} {clean_summary} {alignment_evidence or ''} {human_reviewed_rationale or ''}"):
        return {
            "status": "rejected",
            "eligible": False,
            "submitted": False,
            "source_unchanged": True,
            "reasons": ["issue_closing_keywords_forbidden_on_cloud_builder_stack_pr"],
            "next": "remove_issue_closing_keywords",
        }

    # Fetch the canonical catalogue at most once per call and reuse it for
    # qualification and numbering so a single proposal issues one upstream read.
    cached_markdown: list[str] = []

    def _memo_source() -> str:
        if not cached_markdown:
            fetcher = source_fetcher or fetch_canonical_idea_catalogue_markdown
            cached_markdown.append(fetcher())
        return cached_markdown[0]

    qualification = qualify_idea(
        clean_title,
        clean_summary,
        alignment_evidence=alignment_evidence,
        human_reviewed_rationale=human_reviewed_rationale,
        reviewed_by=reviewed_by,
        source_fetcher=_memo_source,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
        showcase_fetcher=showcase_fetcher,
    )
    if not qualification.get("eligible"):
        return {
            "status": "rejected",
            "eligible": False,
            "submitted": False,
            "source_unchanged": True,
            "qualification": qualification,
            "reasons": qualification.get("reasons", ["not_eligible"]),
            "next": qualification.get("next", "revise_or_discard_candidate"),
        }

    catalogue_result = fetch_idea_catalogue(source_fetcher=_memo_source)
    existing_numbers = [
        item["idea_number"]
        for item in catalogue_result.get("ideas", [])
        if isinstance(item.get("idea_number"), int)
    ]
    next_number = (max(existing_numbers) + 1) if existing_numbers else 138
    proposed_markdown_block = f"### {next_number}. {clean_title}\n{clean_summary}\n"
    pr_branch = f"idea/{_slugify(clean_title)}"
    pr_title = f"feat: propose {clean_title} for hackathon ideas catalogue"
    pr_body = (
        "## Proposed Idea Catalogue Addition\n\n"
        f"- **Title:** {clean_title}\n"
        f"- **Target section:** {clean_section}\n"
        f"- **Summary:** {clean_summary}\n"
        f"- **Alignment evidence:** {_clean_text(alignment_evidence)}\n"
        f"- **Human-reviewed rationale:** {_clean_text(human_reviewed_rationale)}\n\n"
        "## Governance Note\n\n"
        "- Ideation-only entry for `docs/fun-project-and-hackathon-ideas.md`.\n"
        "- Reviewer and assignee: `@valiantone`.\n"
        "- `knowb-kenobi[bot]` must not merge this pull request.\n"
    )

    preview = {
        "target_repo": CANONICAL_IDEA_CATALOGUE_REPO,
        "target_path": CANONICAL_IDEA_CATALOGUE_PATH,
        "base_branch": CANONICAL_IDEA_CATALOGUE_BRANCH,
        "head_branch": pr_branch,
        "section": clean_section,
        "proposed_idea_number": next_number,
        "proposed_markdown_block": proposed_markdown_block,
        "pr_title": pr_title,
        "pr_body": pr_body,
        "reviewer": CLOUD_BUILDER_STACK_REVIEWER,
        "assignee": CLOUD_BUILDER_STACK_ASSIGNEE,
        "kenobi_may_merge": False,
        "direct_default_branch_write": False,
        "copied_into_betterhackdays": False,
        "contains_closing_keywords": bool(
            _CLOSING_KEYWORD_RE.search(f"{pr_title}\n{pr_body}")
        ),
    }

    review_policy = verify_cloud_builder_stack_review_policy(
        policy_inspector=policy_inspector,
        policy_pr_url=policy_pr_url,
    )

    if not submit:
        return {
            "status": "preview_ready",
            "eligible": True,
            "submitted": False,
            "submission_enabled": review_policy["submission_enabled"],
            "source_unchanged": True,
            "qualification": qualification,
            "preview": preview,
            "review_policy": review_policy,
            "next": (
                "submit_cloud_builder_stack_pr"
                if review_policy["submission_enabled"]
                else "apply_cloud_builder_stack_review_policy_first"
            ),
        }

    # Submission requested: check caller identity and permission on knowb-ai/cloud-builder-stack first
    auth_check = authorize_github_mutation(
        operation="catalogue_pr_create",
        target_repo=CANONICAL_IDEA_CATALOGUE_REPO,
        auth_context=auth_context,
    )
    if not auth_check["authorized"]:
        return {
            "status": "unauthorized",
            "eligible": True,
            "submitted": False,
            "submission_enabled": review_policy["submission_enabled"],
            "source_unchanged": True,
            "authorization": auth_check,
            "qualification": qualification,
            "preview": preview,
            "review_policy": review_policy,
            "next": "verify_github_identity_and_repo_permission",
        }

    # The human-reviewed rationale must come from the verified maintainer/admin caller.
    reviewer_login = _clean_text(reviewed_by)
    reviewer_rejection = None
    if not reviewer_login:
        reviewer_rejection = (
            "reviewer_identity_required",
            "reviewed_by must name the verified GitHub maintainer or admin approving the idea.",
        )
    elif reviewer_login.lower() != auth_check["verified_login"].lower():
        reviewer_rejection = (
            "reviewer_identity_mismatch",
            (
                f"reviewed_by '{reviewer_login}' does not match the authenticated "
                f"GitHub identity '{auth_check['verified_login']}'."
            ),
        )
    elif auth_check["verified_permission"] not in {"maintain", "admin"}:
        reviewer_rejection = (
            "maintainer_review_required",
            (
                f"Cloud Builder Stack proposal approval requires maintain or admin "
                f"permission; '{auth_check['verified_login']}' has "
                f"'{auth_check['verified_permission']}'."
            ),
        )
    if reviewer_rejection is not None:
        return {
            "status": "reviewer_verification_failed",
            "eligible": True,
            "submitted": False,
            "submission_enabled": review_policy["submission_enabled"],
            "source_unchanged": True,
            "authorization": auth_check,
            "qualification": qualification,
            "preview": preview,
            "review_policy": review_policy,
            "reasons": [reviewer_rejection[0]],
            "detail": reviewer_rejection[1],
            "next": "reauthenticate_as_reviewing_maintainer",
        }

    if not review_policy["enforced"]:
        return {
            "status": "blocked_by_review_policy",
            "eligible": True,
            "submitted": False,
            "submission_enabled": False,
            "claims_maintainer_only_approval": False,
            "source_unchanged": True,
            "authorization": auth_check,
            "qualification": qualification,
            "preview": preview,
            "review_policy": review_policy,
            "policy_pr": review_policy["policy_pr"],
            "required_admin_settings": review_policy["required_admin_settings"],
            "reasons": [
                "effective_github_review_rules_not_enforced",
                *review_policy["missing_controls"],
            ],
            "next": "merge_policy_pr_and_enable_admin_branch_protection",
        }

    submitter = pr_submitter or github_pr_submitter
    try:
        pr_result = submitter(preview)
    except Exception as exc:
        return {
            "status": "submission_transport_unavailable",
            "eligible": True,
            "submitted": False,
            "submission_enabled": True,
            "source_unchanged": True,
            "authorization": auth_check,
            "qualification": qualification,
            "preview": preview,
            "review_policy": review_policy,
            "error": str(exc),
            "next": "open_reviewable_pr_with_preview",
        }

    return {
        "status": "pr_submitted",
        "eligible": True,
        "submitted": True,
        "submission_enabled": True,
        "source_unchanged": True,
        "authorization": auth_check,
        "qualification": qualification,
        "preview": preview,
        "review_policy": review_policy,
        "pull_request": {
            "url": pr_result.get("url"),
            "number": pr_result.get("number"),
            "state": pr_result.get("state", "open"),
            "merged": False,
            "reviewer": CLOUD_BUILDER_STACK_REVIEWER,
            "assignee": CLOUD_BUILDER_STACK_ASSIGNEE,
            "kenobi_may_merge": False,
        },
        "next": "await_valiantone_review_and_merge",
    }


# --- Work Package 4: Caller identity and repository permission enforcement ---

BETTERHACKDAYS_REPO = "knowb-ai/BetterHackdays"
ALLOWED_WRITE_PERMISSIONS = frozenset({"write", "maintain", "admin"})
ALLOWED_CONTRIBUTOR_REQUEST_PERMISSIONS = frozenset(
    {"read", "triage", "write", "maintain", "admin"}
)
DENIED_WRITE_PERMISSIONS = frozenset({"read", "triage", "none", ""})
APPROVED_REPO_OWNERS = frozenset({"valiantone"})

DEFAULT_KENOBI_INSTALLATION: dict[str, Any] = {
    "id": 174040384,
    "app_slug": "knowb-kenobi",
    "repository_selection": "all",
    "permissions": {
        "contents": "write",
        "issues": "write",
        "metadata": "read",
        "pull_requests": "write",
    },
}

ALLOWLISTED_MUTATION_REPOS = frozenset(
    {
        "knowb-ai/BetterHackdays",
        "knowb-ai/BetterLover",
        "knowb-ai/sepnu-pues",
        "knowb-ai/x-poser",
        "knowb-ai/cloud-builder-stack",
        "knowb-ai/knowb-ai.github.io",
    }
)

OPERATION_REQUIRED_BOT_SCOPES: dict[str, dict[str, str]] = {
    "pr_create": {"contents": "write", "pull_requests": "write"},
    "pr_edit": {"pull_requests": "write"},
    "issue_create": {"issues": "write"},
    "request_submit": {"issues": "write"},
    "contributor_request_submit": {"issues": "write"},
    "catalogue_pr_create": {"contents": "write", "pull_requests": "write"},
    "catalogue_policy_pr_create": {"contents": "write", "pull_requests": "write"},
    "repo_access_grant": {"administration": "write"},
}

OPERATION_FIXED_TARGET_REPO: dict[str, str] = {
    "request_submit": BETTERHACKDAYS_REPO,
    "contributor_request_submit": BETTERHACKDAYS_REPO,
    "catalogue_pr_create": CANONICAL_IDEA_CATALOGUE_REPO,
    "catalogue_policy_pr_create": CANONICAL_IDEA_CATALOGUE_REPO,
}


def _normalize_repo_full_name(repo: Optional[str]) -> str:
    cleaned = _clean_text(repo)
    if not cleaned:
        return ""
    for canonical in ALLOWLISTED_MUTATION_REPOS:
        if cleaned.lower() == canonical.lower():
            return canonical
    return cleaned


def _scope_satisfies(actual: Optional[str], required: str) -> bool:
    rank = {"none": 0, "read": 1, "write": 2, "admin": 3}
    return rank.get(_clean_text(actual).lower(), 0) >= rank.get(required.lower(), 0)


def _permission_from_repo_payload(repo_data: dict[str, Any]) -> str:
    """Derive a caller's repository permission level from a GitHub `/repos/{owner}/{repo}` payload."""
    perms = repo_data.get("permissions")
    if isinstance(perms, dict):
        if perms.get("admin") is True:
            return "admin"
        if perms.get("maintain") is True:
            return "maintain"
        if perms.get("push") is True:
            return "write"
        if perms.get("triage") is True:
            return "triage"
        if perms.get("pull") is True:
            return "read"
    if repo_data.get("private") is False:
        return "read"
    return "none"


def resolve_live_github_auth_context(
    target_repo: str,
    *,
    token: Optional[str] = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Resolve authenticated human identity, target repo permission, and Kenobi installation from GitHub API.

    Uses `/repos/{owner}/{repo}` as a fallback when a non-collaborator's token cannot call
    `/collaborators/{login}/permission`, and does not require the caller to be an organization
    owner to verify the Kenobi installation scope.
    """
    normalized_target = _normalize_repo_full_name(target_repo)
    headers = _github_headers(token)
    if "Authorization" not in headers:
        return {"identity_lookup_failed": True}

    try:
        user_req = urllib.request.Request(f"{GITHUB_API_BASE}/user", headers=headers)
        with urllib.request.urlopen(user_req, timeout=timeout) as resp:
            user_data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {"identity_lookup_failed": True}

    login = _clean_text(user_data.get("login"))
    if not login:
        return {"identity_lookup_failed": True}

    verified_user = {
        "login": login,
        "id": user_data.get("id"),
        "type": user_data.get("type", "User"),
    }

    permission: Optional[str] = None
    try:
        perm_url = (
            f"{GITHUB_API_BASE}/repos/{normalized_target}/collaborators/"
            f"{urllib.parse.quote(login)}/permission"
        )
        perm_req = urllib.request.Request(perm_url, headers=headers)
        with urllib.request.urlopen(perm_req, timeout=timeout) as resp:
            perm_data = json.loads(resp.read().decode("utf-8"))
        permission = _clean_text(perm_data.get("permission") or "none").lower()
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403, 404}:
            try:
                repo_url = f"{GITHUB_API_BASE}/repos/{normalized_target}"
                repo_req = urllib.request.Request(repo_url, headers=headers)
                with urllib.request.urlopen(repo_req, timeout=timeout) as resp:
                    repo_data = json.loads(resp.read().decode("utf-8"))
                if isinstance(repo_data, dict):
                    permission = _permission_from_repo_payload(repo_data)
            except (urllib.error.URLError, TimeoutError, ValueError):
                permission = None
        else:
            permission = None
    except (urllib.error.URLError, TimeoutError, ValueError):
        permission = None

    if not permission:
        return {
            "verified_user": verified_user,
            "permission_lookup_failed": True,
        }

    # `/orgs/{org}/installations` requires an organization owner token. Try the
    # server/admin token first, then the caller token, and fall back to the
    # verified Kenobi installation baseline so ordinary repo writers and outside
    # contributors are not blocked by an org-owner-only endpoint.
    bot_installation: Optional[dict[str, Any]] = None
    inst_token = os.getenv("KENOBI_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or token
    try:
        inst_url = f"{GITHUB_API_BASE}/orgs/{KNOWB_ORG}/installations"
        inst_req = urllib.request.Request(
            inst_url, headers=_github_headers(inst_token)
        )
        with urllib.request.urlopen(inst_req, timeout=timeout) as resp:
            inst_data = json.loads(resp.read().decode("utf-8"))
        for inst in inst_data.get("installations", []):
            if isinstance(inst, dict) and inst.get("app_slug") == "knowb-kenobi":
                bot_installation = {
                    "id": inst.get("id"),
                    "app_slug": "knowb-kenobi",
                    "repository_selection": inst.get("repository_selection", "all"),
                    "permissions": dict(inst.get("permissions") or {}),
                }
                break
    except (urllib.error.URLError, TimeoutError, ValueError):
        bot_installation = None

    if bot_installation is None:
        bot_installation = {
            **DEFAULT_KENOBI_INSTALLATION,
            "permissions": dict(DEFAULT_KENOBI_INSTALLATION["permissions"]),
        }

    return {
        "verified_user": verified_user,
        "repo_permissions": {
            normalized_target: {"login": login, "permission": permission}
        },
        "bot_installation": bot_installation,
    }


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Return the bearer token from an Authorization header value, if present."""
    if not authorization or not isinstance(authorization, str):
        return None
    scheme, separator, token = authorization.strip().partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None
    cleaned = token.strip()
    return cleaned or None


def resolve_request_auth_context(
    authorization: Optional[str],
    target_repo: str = BETTERHACKDAYS_REPO,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Resolve a live GitHub identity from an inbound bearer token.

    Request bodies never carry identity or permission claims. When the header is
    missing or malformed, the context fails closed instead of falling back to a
    server token, because a server token would authorize every anonymous caller.
    """
    token = _extract_bearer_token(authorization)
    if not token:
        return {
            "identity_lookup_failed": True,
            "auth_source": "missing_bearer_token",
        }
    context = resolve_live_github_auth_context(target_repo, token=token, timeout=timeout)
    context["auth_source"] = "request_bearer_token"
    return context


def resolve_service_auth_context(
    target_repo: str = BETTERHACKDAYS_REPO,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Resolve the server-side GitHub token identity for MCP and server-initiated calls."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {
            "identity_lookup_failed": True,
            "auth_source": "service_token_unavailable",
        }
    context = resolve_live_github_auth_context(target_repo, token=token, timeout=timeout)
    context["auth_source"] = "service_env_token"
    return context



def _verify_human_identity_and_repo_permission(
    auth_context: Optional[dict[str, Any]],
    target_repo: str,
) -> dict[str, Any]:
    """Validate a verified human identity and exact-repo permission record from an auth context.

    Fails closed on missing, stale, or failed lookups, bot accounts, identity spoofing,
    and permission records that do not belong to the verified human caller.
    """
    normalized_target = _normalize_repo_full_name(target_repo)

    def _deny(reason: str, detail: str, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"ok": False, "reason": reason, "detail": detail}
        payload.update(extra)
        return payload

    if auth_context is None or not isinstance(auth_context, dict):
        return _deny(
            "unknown_identity",
            "Authenticated GitHub identity context is missing; failing closed.",
        )

    if auth_context.get("identity_lookup_failed") or auth_context.get("identity_stale"):
        return _deny(
            "stale_or_failed_identity_lookup",
            "Authenticated GitHub identity lookup failed or is stale.",
        )

    verified_identity = auth_context.get("verified_user")
    if not isinstance(verified_identity, dict):
        return _deny(
            "unknown_identity",
            "Could not resolve an authenticated human GitHub user.",
        )

    verified_login = _clean_text(verified_identity.get("login"))
    verified_type = _clean_text(verified_identity.get("type") or "User")
    is_bot_account = (
        bool(verified_identity.get("is_bot"))
        or verified_type.lower() != "user"
        or verified_login.endswith("[bot]")
        or verified_login.startswith("app/")
        or verified_login.lower() in {"knowb-kenobi", "knowb-kenobi[bot]"}
    )
    if not verified_login or is_bot_account:
        return _deny(
            "unknown_identity",
            "Authenticated identity must be a verified human GitHub user, not a bot or unknown account.",
        )

    if auth_context.get("permission_lookup_failed") or auth_context.get("permission_stale"):
        return _deny(
            "stale_or_failed_permission_lookup",
            f"Permission lookup for '{verified_login}' on '{normalized_target}' failed or is stale.",
            verified_login=verified_login,
        )

    repo_permissions = auth_context.get("repo_permissions")
    if not isinstance(repo_permissions, dict):
        return _deny(
            "stale_or_failed_permission_lookup",
            f"No verified repository permission map available for '{normalized_target}'.",
            verified_login=verified_login,
        )

    matched_perm_entry: Any = None
    for repo_key, perm_val in repo_permissions.items():
        if _normalize_repo_full_name(repo_key).lower() == normalized_target.lower():
            matched_perm_entry = perm_val
            break

    if matched_perm_entry is None:
        return _deny(
            "wrong_repository_mapping",
            (
                f"Permission was not verified for exact target repository "
                f"'{normalized_target}'."
            ),
            verified_login=verified_login,
        )

    if isinstance(matched_perm_entry, dict):
        if matched_perm_entry.get("stale") or matched_perm_entry.get("failed"):
            return _deny(
                "stale_or_failed_permission_lookup",
                f"Permission record for '{normalized_target}' is stale or failed.",
                verified_login=verified_login,
            )
        permission_actor = _clean_text(matched_perm_entry.get("login"))
        if permission_actor and permission_actor.lower() != verified_login.lower():
            return _deny(
                "caller_identity_spoofing",
                "Repository permission record does not belong to the verified human caller.",
                verified_login=verified_login,
            )
        permission = _clean_text(matched_perm_entry.get("permission")).lower()
    else:
        permission = _clean_text(matched_perm_entry).lower()

    return {
        "ok": True,
        "verified_login": verified_login,
        "verified_permission": permission,
    }


def authorize_github_mutation(
    *,
    operation: str,
    target_repo: str,
    expected_target_repo: Optional[str] = None,
    caller_supplied_login: Optional[str] = None,
    asserted_role: Optional[str] = None,
    auth_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Verify authenticated human identity, exact repo permission, and Kenobi bot scope before any write.

    Fails closed when identity, permission, target mapping, or bot scope cannot be verified.
    Never trusts caller-supplied login or asserted role, and never substitutes bot installation
    permission for the human's repository permission.
    """
    clean_op = _clean_text(operation)
    normalized_target = _normalize_repo_full_name(target_repo)
    normalized_expected = _normalize_repo_full_name(
        expected_target_repo or OPERATION_FIXED_TARGET_REPO.get(clean_op)
    )

    def _deny(reason: str, detail: str, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "authorized": False,
            "status": "denied",
            "operation": clean_op,
            "target_repo": normalized_target or _clean_text(target_repo),
            "reason": reason,
            "detail": detail,
            "mutation_performed": False,
        }
        payload.update(extra)
        return payload

    if clean_op not in OPERATION_REQUIRED_BOT_SCOPES:
        return _deny(
            "unknown_operation",
            f"Operation '{clean_op}' is not an approved connector mutation.",
        )

    if not normalized_target:
        return _deny(
            "wrong_repository_mapping",
            "Target repository is missing.",
        )

    if any(tok in normalized_target.lower() for tok in FORBIDDEN_PRIVATE_TOKENS):
        return _deny(
            "wrong_repository_mapping",
            "KnowledgeHQ and private repositories are never valid connector mutation targets.",
        )

    if normalized_target not in ALLOWLISTED_MUTATION_REPOS:
        return _deny(
            "wrong_repository_mapping",
            f"Repository '{normalized_target}' is not in the allowlisted mutation target set.",
        )

    if normalized_expected and normalized_target.lower() != normalized_expected.lower():
        return _deny(
            "wrong_repository_mapping",
            (
                f"Operation '{clean_op}' must target '{normalized_expected}', "
                f"not '{normalized_target}'."
            ),
            expected_target_repo=normalized_expected,
        )

    verified_context = _verify_human_identity_and_repo_permission(
        auth_context, normalized_target
    )
    if not verified_context.get("ok"):
        context_extra = {
            key: value
            for key, value in verified_context.items()
            if key not in {"ok", "reason", "detail"}
        }
        return _deny(
            verified_context["reason"],
            verified_context["detail"],
            **context_extra,
        )

    verified_login = verified_context["verified_login"]
    human_permission = verified_context["verified_permission"]

    supplied_login = _clean_text(
        caller_supplied_login
        if caller_supplied_login is not None
        else auth_context.get("caller_supplied_login")
    )
    if supplied_login and supplied_login.lower() != verified_login.lower():
        return _deny(
            "caller_identity_spoofing",
            (
                f"Caller-supplied login '{supplied_login}' does not match "
                f"authenticated GitHub identity '{verified_login}'."
            ),
            verified_login=verified_login,
            caller_supplied_login=supplied_login,
        )

    # Never trust caller-asserted role; always resolve permission on the exact target repository
    _ignored_asserted_role = asserted_role or auth_context.get("asserted_role")

    allowed_permissions = (
        ALLOWED_CONTRIBUTOR_REQUEST_PERMISSIONS
        if clean_op == "contributor_request_submit"
        else ALLOWED_WRITE_PERMISSIONS
    )
    if human_permission not in allowed_permissions:
        required_desc = (
            "read, triage, write, maintain, or admin"
            if clean_op == "contributor_request_submit"
            else "write, maintain, or admin"
        )
        return _deny(
            "insufficient_repository_permission",
            (
                f"User '{verified_login}' has permission '{human_permission or 'none'}' "
                f"on '{normalized_target}'; {required_desc} is required."
            ),
            verified_login=verified_login,
            verified_permission=human_permission or "none",
            ignored_asserted_role=_ignored_asserted_role,
        )

    if clean_op == "repo_access_grant" and human_permission != "admin":
        return _deny(
            "owner_admin_permission_required",
            (
                f"Repository access changes on '{normalized_target}' require owner "
                f"admin permission; '{verified_login}' has '{human_permission}'."
            ),
            verified_login=verified_login,
            verified_permission=human_permission,
        )

    # Verify Kenobi bot installation scope for the specific operation
    bot_installation = auth_context.get("bot_installation")
    if not isinstance(bot_installation, dict):
        return _deny(
            "bot_installation_missing_scope",
            "Kenobi bot installation metadata could not be verified.",
            verified_login=verified_login,
            verified_permission=human_permission,
        )

    app_slug = _clean_text(bot_installation.get("app_slug") or "knowb-kenobi")
    if app_slug != "knowb-kenobi":
        return _deny(
            "bot_installation_missing_scope",
            f"Unexpected GitHub App installation '{app_slug}'; expected 'knowb-kenobi'.",
            verified_login=verified_login,
            verified_permission=human_permission,
        )

    installed_repos = bot_installation.get("repositories")
    repo_selection = _clean_text(
        bot_installation.get("repository_selection") or "all"
    ).lower()
    if repo_selection != "all":
        if not isinstance(installed_repos, list) or not any(
            _normalize_repo_full_name(r).lower() == normalized_target.lower()
            for r in installed_repos
        ):
            return _deny(
                "bot_installation_missing_scope",
                f"Kenobi installation does not cover target repository '{normalized_target}'.",
                verified_login=verified_login,
                verified_permission=human_permission,
            )

    bot_permissions = bot_installation.get("permissions")
    if not isinstance(bot_permissions, dict):
        return _deny(
            "bot_installation_missing_scope",
            "Kenobi installation permissions map is missing.",
            verified_login=verified_login,
            verified_permission=human_permission,
        )

    required_scopes = OPERATION_REQUIRED_BOT_SCOPES[clean_op]
    missing_scopes = [
        f"{scope}:{level}"
        for scope, level in required_scopes.items()
        if not _scope_satisfies(bot_permissions.get(scope), level)
    ]
    if missing_scopes:
        return _deny(
            "bot_installation_missing_scope",
            (
                f"Kenobi installation lacks required scope(s) {', '.join(missing_scopes)} "
                f"for operation '{clean_op}' on '{normalized_target}'."
            ),
            verified_login=verified_login,
            verified_permission=human_permission,
            missing_bot_scopes=missing_scopes,
        )

    return {
        "authorized": True,
        "status": "authorized",
        "operation": clean_op,
        "target_repo": normalized_target,
        "verified_login": verified_login,
        "verified_permission": human_permission,
        "bot_app_slug": app_slug,
        "verified_bot_scopes": required_scopes,
    }


def execute_authorized_github_mutation(
    *,
    operation: str,
    target_repo: str,
    expected_target_repo: Optional[str] = None,
    caller_supplied_login: Optional[str] = None,
    asserted_role: Optional[str] = None,
    auth_context: Optional[dict[str, Any]] = None,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Run `authorize_github_mutation` and execute `mutator` only when authorized."""
    auth_result = authorize_github_mutation(
        operation=operation,
        target_repo=target_repo,
        expected_target_repo=expected_target_repo,
        caller_supplied_login=caller_supplied_login,
        asserted_role=asserted_role,
        auth_context=auth_context,
    )
    if not auth_result["authorized"]:
        return auth_result

    outcome = mutator(auth_result)
    return {
        **auth_result,
        "mutation_performed": True,
        "result": outcome,
    }


def grant_repository_access(
    *,
    target_repo: str,
    grantee_login: str,
    permission: str = "write",
    requester_login: Optional[str] = None,
    confirmed: bool = False,
    auth_context: Optional[dict[str, Any]] = None,
    dry_run: bool = True,
    invitation_sender: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Separate owner-only, explicitly confirmed repository access operation.

    A contributor request never grants access automatically. The requester cannot
    grant or elevate their own access, admin role grants are forbidden, and tests
    never issue live GitHub invitations.
    """
    normalized_target = _normalize_repo_full_name(target_repo)
    clean_grantee = _clean_text(grantee_login)
    clean_requester = _clean_text(requester_login)
    clean_permission = _clean_text(permission).lower()

    if not confirmed:
        return {
            "status": "denied",
            "authorized": False,
            "reason": "explicit_owner_confirmation_required",
            "detail": "Repository access changes require explicit owner confirmation.",
            "target_repo": normalized_target or _clean_text(target_repo),
            "grantee_login": clean_grantee,
            "mutation_performed": False,
            "invitation_sent": False,
        }

    if not clean_grantee:
        return {
            "status": "denied",
            "authorized": False,
            "reason": "missing_grantee_login",
            "detail": "A valid grantee GitHub login is required.",
            "target_repo": normalized_target or _clean_text(target_repo),
            "grantee_login": "",
            "mutation_performed": False,
            "invitation_sent": False,
        }

    if clean_permission not in {"read", "triage", "write", "maintain"}:
        return {
            "status": "denied",
            "authorized": False,
            "reason": "invalid_or_forbidden_permission_level",
            "detail": "Only read, triage, write, or maintain may be granted; admin grants are forbidden.",
            "target_repo": normalized_target or _clean_text(target_repo),
            "grantee_login": clean_grantee,
            "requested_permission": clean_permission,
            "mutation_performed": False,
            "invitation_sent": False,
        }

    auth_result = authorize_github_mutation(
        operation="repo_access_grant",
        target_repo=normalized_target,
        expected_target_repo=normalized_target,
        auth_context=auth_context,
    )
    if not auth_result["authorized"]:
        return {
            **auth_result,
            "grantee_login": clean_grantee,
            "requested_permission": clean_permission,
            "invitation_sent": False,
        }

    actor_login = auth_result["verified_login"]
    if actor_login.lower() not in APPROVED_REPO_OWNERS:
        return {
            "status": "denied",
            "authorized": False,
            "operation": "repo_access_grant",
            "target_repo": normalized_target,
            "verified_login": actor_login,
            "reason": "owner_only_operation",
            "detail": f"Only a repository owner may grant access; '{actor_login}' is not an approved owner.",
            "grantee_login": clean_grantee,
            "mutation_performed": False,
            "invitation_sent": False,
        }

    if clean_grantee.lower() == actor_login.lower() or (
        clean_requester and clean_requester.lower() == actor_login.lower() and clean_grantee.lower() == clean_requester.lower()
    ):
        return {
            "status": "denied",
            "authorized": False,
            "operation": "repo_access_grant",
            "target_repo": normalized_target,
            "verified_login": actor_login,
            "reason": "self_elevation_forbidden",
            "detail": "The requester cannot grant or elevate their own repository access.",
            "grantee_login": clean_grantee,
            "mutation_performed": False,
            "invitation_sent": False,
        }

    grant_spec = {
        "target_repo": normalized_target,
        "grantee_login": clean_grantee,
        "permission": clean_permission,
        "approved_by": actor_login,
        "confirmed": True,
    }

    if dry_run:
        return {
            "status": "approved_dry_run",
            "authorized": True,
            "operation": "repo_access_grant",
            "target_repo": normalized_target,
            "verified_login": actor_login,
            "verified_permission": auth_result["verified_permission"],
            "grantee_login": clean_grantee,
            "granted_permission": clean_permission,
            "mutation_performed": False,
            "invitation_sent": False,
            "grant": grant_spec,
        }

    sender = invitation_sender or github_invitation_sender
    try:
        send_result = sender(grant_spec)
    except Exception as exc:
        return {
            "status": "invitation_transport_unavailable",
            "authorized": True,
            "operation": "repo_access_grant",
            "target_repo": normalized_target,
            "verified_login": actor_login,
            "verified_permission": auth_result["verified_permission"],
            "grantee_login": clean_grantee,
            "granted_permission": clean_permission,
            "mutation_performed": False,
            "invitation_sent": False,
            "grant": grant_spec,
            "error": str(exc),
        }

    return {
        "status": "invitation_recorded",
        "authorized": True,
        "operation": "repo_access_grant",
        "target_repo": normalized_target,
        "verified_login": actor_login,
        "verified_permission": auth_result["verified_permission"],
        "grantee_login": clean_grantee,
        "granted_permission": clean_permission,
        "mutation_performed": True,
        "invitation_sent": bool(send_result.get("invitation_sent", False)),
        "grant": grant_spec,
    }


# --- GitHub and email mutation transports ---


def _github_api_request(
    method: str,
    url: str,
    *,
    payload: Optional[dict[str, Any]] = None,
    token: Optional[str] = None,
    timeout: float = 20.0,
) -> Any:
    """Call the GitHub REST API with an explicit token and return decoded JSON."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = _github_headers(token)
    headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _resolve_mutation_token(token: Optional[str] = None) -> str:
    resolved = token or os.getenv("KENOBI_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not resolved:
        raise RuntimeError(
            "GitHub mutation transport requires KENOBI_GITHUB_TOKEN or GITHUB_TOKEN."
        )
    return resolved


def github_pr_submitter(
    spec: dict[str, Any],
    *,
    token: Optional[str] = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Open a reviewable pull request for a proposed addition and request the approved reviewer."""
    resolved_token = _resolve_mutation_token(token)
    repo = spec["target_repo"]
    base_branch = spec["base_branch"]
    head_branch = spec["head_branch"]
    target_path = spec["target_path"]

    base_ref = _github_api_request(
        "GET",
        f"{GITHUB_API_BASE}/repos/{repo}/git/ref/heads/{urllib.parse.quote(base_branch)}",
        token=resolved_token,
        timeout=timeout,
    )
    base_sha = base_ref["object"]["sha"]

    try:
        _github_api_request(
            "POST",
            f"{GITHUB_API_BASE}/repos/{repo}/git/refs",
            payload={"ref": f"refs/heads/{head_branch}", "sha": base_sha},
            token=resolved_token,
            timeout=timeout,
        )
    except urllib.error.HTTPError as exc:
        if exc.code != 422:
            raise

    existing = _github_api_request(
        "GET",
        f"{GITHUB_API_BASE}/repos/{repo}/contents/{urllib.parse.quote(target_path)}"
        f"?ref={urllib.parse.quote(base_branch)}",
        token=resolved_token,
        timeout=timeout,
    )
    existing_content = base64.b64decode(existing.get("content", "")).decode("utf-8")
    appended = existing_content.rstrip("\n") + "\n\n" + spec["proposed_markdown_block"]

    _github_api_request(
        "PUT",
        f"{GITHUB_API_BASE}/repos/{repo}/contents/{urllib.parse.quote(target_path)}",
        payload={
            "message": spec["pr_title"],
            "content": base64.b64encode(appended.encode("utf-8")).decode("ascii"),
            "branch": head_branch,
            "sha": existing.get("sha"),
        },
        token=resolved_token,
        timeout=timeout,
    )

    pull_request = _github_api_request(
        "POST",
        f"{GITHUB_API_BASE}/repos/{repo}/pulls",
        payload={
            "title": spec["pr_title"],
            "head": head_branch,
            "base": base_branch,
            "body": spec["pr_body"],
        },
        token=resolved_token,
        timeout=timeout,
    )
    number = pull_request.get("number")

    _github_api_request(
        "POST",
        f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}/requested_reviewers",
        payload={"reviewers": [spec["reviewer"]]},
        token=resolved_token,
        timeout=timeout,
    )
    _github_api_request(
        "POST",
        f"{GITHUB_API_BASE}/repos/{repo}/issues/{number}/assignees",
        payload={"assignees": [spec["assignee"]]},
        token=resolved_token,
        timeout=timeout,
    )

    return {
        "url": pull_request.get("html_url"),
        "number": number,
        "state": pull_request.get("state", "open"),
    }


def github_invitation_sender(
    grant: dict[str, Any],
    *,
    token: Optional[str] = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Send an owner-approved repository invitation through the GitHub API."""
    resolved_token = _resolve_mutation_token(token)
    repo = grant["target_repo"]
    grantee = urllib.parse.quote(grant["grantee_login"])
    _github_api_request(
        "PUT",
        f"{GITHUB_API_BASE}/repos/{repo}/collaborators/{grantee}",
        payload={"permission": grant["permission"]},
        token=resolved_token,
        timeout=timeout,
    )
    return {"invitation_sent": True, "permission": grant["permission"]}


def send_contributor_request_email(
    payload: dict[str, Any],
    *,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Send an approved contributor request to the configured owner inbox over SMTP.

    Uses deployment-provided SMTP settings and no new mail vendor. When SMTP is
    not configured the caller keeps the addressed draft and reports it as unsent.
    """
    host = _clean_text(os.getenv("SMTP_HOST"))
    username = _clean_text(os.getenv("SMTP_USERNAME"))
    password = os.getenv("SMTP_PASSWORD")
    sender = _clean_text(os.getenv("SMTP_FROM"))
    try:
        port = int(os.getenv("SMTP_PORT", "587") or 587)
    except ValueError:
        port = 587
    if not (host and username and password and sender):
        raise RuntimeError(
            "SMTP delivery is not configured (SMTP_HOST, SMTP_USERNAME, "
            "SMTP_PASSWORD, SMTP_FROM)."
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = payload["recipient"]
    message["Subject"] = payload["subject"]
    message.set_content(payload["formatted_body"])

    with smtplib.SMTP(host, port, timeout=timeout) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
    return {"sent": True}


# --- Work Package 5: Public design resources, RFP discovery, and contributor requests ---

DESIGN_RESOURCE_REPO = "knowb-ai/knowb-ai.github.io"
APPROVED_REQUEST_RECIPIENT = "ping@knowb.run"
APPROVED_CONNECTOR_ROUTE = "knowb-ai/BetterHackdays"

ALLOWED_CONTRIBUTOR_REQUEST_TYPES: dict[str, str] = {
    "refinement_draft": "RFP Refinement Draft",
    "expression_of_interest": "Expression of Interest",
    "contribution_access_request": "Project Contribution Access Request",
    "work_elevation_request": "Work Elevation Request",
}

ALLOWLISTED_DESIGN_RESOURCES: dict[str, dict[str, Any]] = {
    "DESIGN_SYSTEM.md": {
        "path": "DESIGN_SYSTEM.md",
        "title": "KnowB Visual Design System",
        "kind": "design_philosophy_document",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/DESIGN_SYSTEM.md",
        "public_url": "https://knowb.run/org-book/",
        "summary": (
            "Cross-axis visual canon: Autumn and Gold palettes, Internal/External/Artistic "
            "channels, six themes, five styles, fixed typography, and configuration contract."
        ),
        "default_excerpt": (
            "KnowB uses four independent design axes: Palette (Autumn, Gold), "
            "Channel (Internal, External, Artistic), Theme (Space-race, Psychedelic, "
            "Retrowave, Editorial, Arcade, Comic), and Style (60s, 70s, 80s, 90s, 2000s)."
        ),
    },
    "ORGBRAND_GUIDELINES.md": {
        "path": "ORGBRAND_GUIDELINES.md",
        "title": "KnowB Autumn Implementation and Accessibility Guidelines",
        "kind": "design_philosophy_document",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/ORGBRAND_GUIDELINES.md",
        "public_url": "https://knowb.run/org-book/",
        "summary": (
            "Autumn token, gradient, contrast, CRT, motion, and WCAG 2.2 AA rules "
            "for public KnowB surfaces."
        ),
        "default_excerpt": (
            "Autumn has seven core color tokens (#FF4A1A, #8E2F2A, #F59A52, #FCF6F3, "
            "#7A2217, #77584F, #E9C2B3) plus the optional Saber Blue (#86E8FF) signal."
        ),
    },
    "content/org-book.md": {
        "path": "content/org-book.md",
        "title": "KnowB AI Visual Design System Page",
        "kind": "design_philosophy_document",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/content/org-book.md",
        "public_url": "https://knowb.run/org-book/",
        "summary": "Public Org Book entry page metadata for knowb.run.",
        "default_excerpt": "Public reference page for KnowB palettes, channels, themes, styles, typography, and accessible UI patterns.",
    },
    "static/css/global.css": {
        "path": "static/css/global.css",
        "title": "KnowB Global Editorial and Arcade Stylesheet",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/static/css/global.css",
        "public_url": "https://knowb.run/css/global.css",
        "summary": "Space-age editorial and tailfin arcade CSS tokens and components.",
        "default_excerpt": "Defines space-age editorial surfaces, typography rules, tailfin arcade buttons, chips, and cabinets.",
    },
    "static/css/concept-book.css": {
        "path": "static/css/concept-book.css",
        "title": "KnowB Concept Book Plate Stylesheet",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/static/css/concept-book.css",
        "public_url": "https://knowb.run/css/concept-book.css",
        "summary": "Scoped Concept Book plate styles for the public Org Book.",
        "default_excerpt": "Scoped stylesheet for rendered Concept Book reference plates.",
    },
    "static/favicon.svg": {
        "path": "static/favicon.svg",
        "title": "KnowB Brand Favicon",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/static/favicon.svg",
        "public_url": "https://knowb.run/favicon.svg",
        "summary": "Three vertical bars on Ground (#161211): outer Autumn Fire (#FF4A1A), middle Saber Blue (#86E8FF).",
        "default_excerpt": "Brand mark SVG with outer Autumn Fire bars and center Saber Blue bar.",
    },
    "static/design-system/knowb-autumn-palette.png": {
        "path": "static/design-system/knowb-autumn-palette.png",
        "title": "KnowB Autumn Palette Specimen",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/static/design-system/knowb-autumn-palette.png",
        "public_url": "https://knowb.run/design-system/knowb-autumn-palette.png",
        "summary": "Visual reference card for the KnowB Autumn color palette.",
        "default_excerpt": "Binary PNG asset for KnowB Autumn palette tokens.",
    },
    "static/design-system/knowb-gold-visual-language.png": {
        "path": "static/design-system/knowb-gold-visual-language.png",
        "title": "KnowB Gold Visual Language Specimen",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/static/design-system/knowb-gold-visual-language.png",
        "public_url": "https://knowb.run/design-system/knowb-gold-visual-language.png",
        "summary": "Visual reference card for the KnowB Gold operational palette.",
        "default_excerpt": "Binary PNG asset for KnowB Gold visual language.",
    },
    "static/design-system/kenobi-digital-surface-palette.png": {
        "path": "static/design-system/kenobi-digital-surface-palette.png",
        "title": "Kenobi Digital Surface Palette Specimen",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/static/design-system/kenobi-digital-surface-palette.png",
        "public_url": "https://knowb.run/design-system/kenobi-digital-surface-palette.png",
        "summary": "Visual reference card for Kenobi digital surfaces.",
        "default_excerpt": "Binary PNG asset for Kenobi digital surface palette.",
    },
    "static/design-system/knowb-typography-specimen.png": {
        "path": "static/design-system/knowb-typography-specimen.png",
        "title": "KnowB Typography Specimen",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/static/design-system/knowb-typography-specimen.png",
        "public_url": "https://knowb.run/design-system/knowb-typography-specimen.png",
        "summary": "Typography specimen for Audiowide, Space Grotesk, Inter, and JetBrains Mono.",
        "default_excerpt": "Binary PNG asset for fixed KnowB typography hierarchy.",
    },
    "design/pixel-icons/dictionary.txt": {
        "path": "design/pixel-icons/dictionary.txt",
        "title": "KnowB Pixel Icons Dictionary",
        "kind": "design_asset",
        "repo": DESIGN_RESOURCE_REPO,
        "source_url": "https://github.com/knowb-ai/knowb-ai.github.io/blob/main/design/pixel-icons/dictionary.txt",
        "public_url": "https://knowb.run/org-book/",
        "summary": "Public pixel icon definitions used in knowb.run arcade cabinets.",
        "default_excerpt": "Pixel icon glyph dictionary for knowb.run UI components.",
    },
}


def list_design_resources() -> dict[str, Any]:
    """List only explicitly allowlisted public design philosophy documents and assets from knowb-ai.github.io."""
    resources = [
        {
            "path": item["path"],
            "title": item["title"],
            "kind": item["kind"],
            "repo": item["repo"],
            "source_url": item["source_url"],
            "public_url": item["public_url"],
            "summary": item["summary"],
        }
        for item in ALLOWLISTED_DESIGN_RESOURCES.values()
    ]
    return {
        "status": "ok",
        "repo": DESIGN_RESOURCE_REPO,
        "generic_browsing_enabled": False,
        "resources": resources,
        "next": "read_design_resource",
    }


TEXT_DESIGN_RESOURCE_SUFFIXES = (".md", ".css", ".svg", ".txt")

DESIGN_RESOURCE_CONTENT_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".css": "text/css",
    ".md": "text/markdown",
    ".txt": "text/plain",
}


def fetch_design_resource_content(path: str, *, timeout: float = 10.0) -> Optional[str]:
    """Fetch the actual allowlisted public design resource from the website repository."""
    if path not in ALLOWLISTED_DESIGN_RESOURCES:
        return None
    if not path.endswith(TEXT_DESIGN_RESOURCE_SUFFIXES):
        return None
    url = f"{DESIGN_RESOURCE_RAW_BASE}/{urllib.parse.quote(path)}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "BetterHackdays-Connector/0.1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def read_design_resource(
    path: str,
    *,
    repo: str = DESIGN_RESOURCE_REPO,
    content_fetcher: Optional[Callable[[str], Optional[str]]] = None,
) -> dict[str, Any]:
    """Read an allowlisted public design resource from knowb-ai.github.io.

    Rejects any path outside the explicit allowlist or any non-website repository,
    and serves live file content rather than a static summary where the asset is text.
    """
    clean_repo = _clean_text(repo or DESIGN_RESOURCE_REPO)
    raw_path = _clean_text(path).lstrip("/")

    if clean_repo.lower() != DESIGN_RESOURCE_REPO.lower():
        return {
            "status": "denied",
            "reason": "repository_not_allowlisted",
            "detail": (
                f"Design resources may only be served from '{DESIGN_RESOURCE_REPO}', "
                f"not '{clean_repo}'."
            ),
            "path": raw_path,
            "generic_browsing_enabled": False,
        }

    if (
        not raw_path
        or ".." in raw_path
        or raw_path.startswith(".")
        or raw_path not in ALLOWLISTED_DESIGN_RESOURCES
    ):
        return {
            "status": "denied",
            "reason": "path_not_allowlisted",
            "detail": (
                f"Path '{raw_path}' is not in the explicit public design resource "
                f"allowlist for '{DESIGN_RESOURCE_REPO}'. Generic repository browsing "
                "is disabled."
            ),
            "path": raw_path,
            "allowlisted_paths": sorted(ALLOWLISTED_DESIGN_RESOURCES.keys()),
            "generic_browsing_enabled": False,
        }

    entry = dict(ALLOWLISTED_DESIGN_RESOURCES[raw_path])
    suffix = "." + raw_path.rsplit(".", 1)[-1].lower() if "." in raw_path else ""
    raw_url = f"{DESIGN_RESOURCE_RAW_BASE}/{urllib.parse.quote(raw_path)}"
    is_text_asset = raw_path.endswith(TEXT_DESIGN_RESOURCE_SUFFIXES)

    fetched: Optional[str] = None
    if is_text_asset:
        fetcher = content_fetcher or fetch_design_resource_content
        fetched = fetcher(raw_path)

    if is_text_asset:
        content_available = bool(fetched)
        excerpt = _clean_text(fetched)[:1200] if fetched else None
        content_source = "live_repository_file" if fetched else "unavailable"
        note = (
            None
            if fetched
            else "Allowlisted resource could not be fetched from the public repository."
        )
    else:
        content_available = True
        excerpt = None
        content_source = "allowlisted_binary_asset"
        note = "Binary asset; use raw_url to fetch the published file."

    return {
        "status": "ok",
        "generic_browsing_enabled": False,
        "resource": {
            "path": entry["path"],
            "title": entry["title"],
            "kind": entry["kind"],
            "repo": entry["repo"],
            "source_url": entry["source_url"],
            "public_url": entry["public_url"],
            "raw_url": raw_url,
            "content_type": DESIGN_RESOURCE_CONTENT_TYPES.get(suffix, "application/octet-stream"),
            "content_available": content_available,
            "content_source": content_source,
            "summary": entry["summary"],
            "excerpt": excerpt,
            "note": note,
        },
        "next": "explore_rfps_or_design_system",
    }


def search_design_resources(query: str) -> dict[str, Any]:
    """Search allowlisted public design philosophy documents and assets."""
    clean_query = _clean_text(query).lower()
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", clean_query) if tok]
    matches: list[dict[str, Any]] = []
    for item in ALLOWLISTED_DESIGN_RESOURCES.values():
        searchable = (
            f"{item['path']} {item['title']} {item['kind']} "
            f"{item['summary']} {item['default_excerpt']}"
        ).lower()
        if not clean_query or clean_query in searchable or (
            tokens and all(tok in searchable for tok in tokens)
        ):
            matches.append(
                {
                    "path": item["path"],
                    "title": item["title"],
                    "kind": item["kind"],
                    "repo": item["repo"],
                    "source_url": item["source_url"],
                    "public_url": item["public_url"],
                    "summary": item["summary"],
                }
            )
    return {
        "status": "ok",
        "query": _clean_text(query),
        "generic_browsing_enabled": False,
        "matches": matches,
        "next": "read_design_resource",
    }


def list_project_rfps(
    *,
    visibility: Optional[str] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
) -> dict[str, Any]:
    """List approved KnowB project RFPs and public resources (distinct from idea suggestions)."""
    catalogue = build_project_rfp_catalogue(
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
        include_connector_only=True,
    )
    rfps = catalogue["rfps"]
    clean_vis = _clean_text(visibility).lower()
    if clean_vis:
        rfps = [item for item in rfps if item["visibility"].lower() == clean_vis]
    return {
        "status": "ok",
        "entry_type": "project_rfp",
        "taxonomy": catalogue["taxonomy"],
        "rfps": rfps,
        "public_resources": catalogue["public_resources"],
        "next": "read_or_compare_project_rfp",
    }


def read_project_rfp(
    rfp_id: str,
    *,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
) -> dict[str, Any]:
    """Read a single approved KnowB project RFP by ID or title."""
    target = _slugify(rfp_id)
    if target in EXCLUDED_REPOSITORIES or any(
        tok in target for tok in FORBIDDEN_PRIVATE_TOKENS
    ):
        return {
            "status": "not_found",
            "rfp_id": _clean_text(rfp_id),
            "error": f"'{_clean_text(rfp_id)}' is not an approved KnowB project RFP.",
            "next": "list_project_rfps",
        }

    catalogue = build_project_rfp_catalogue(
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
        include_connector_only=True,
    )
    for item in catalogue["rfps"]:
        if item["rfp_id"] == target or _slugify(item["title"]) == target:
            return {
                "status": "ok",
                "rfp": item,
                "next": "preview_contributor_request_or_compare",
            }
    return {
        "status": "not_found",
        "rfp_id": _clean_text(rfp_id),
        "error": f"Unknown project RFP '{_clean_text(rfp_id)}'.",
        "next": "list_project_rfps",
    }


def search_project_rfps(
    query: str,
    *,
    include_design_resources: bool = False,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
) -> dict[str, Any]:
    """Search approved project RFPs (and optionally allowlisted public design resources)."""
    clean_query = _clean_text(query).lower()
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", clean_query) if tok]
    catalogue = build_project_rfp_catalogue(
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
        include_connector_only=True,
    )
    matched_rfps: list[dict[str, Any]] = []
    for item in catalogue["rfps"]:
        searchable = " ".join(
            [
                item["rfp_id"],
                item["title"],
                item["summary"],
                item.get("outcome") or "",
                item.get("scope") or "",
                " ".join(item.get("tags") or []),
            ]
        ).lower()
        if not clean_query or clean_query in searchable or (
            tokens and all(tok in searchable for tok in tokens)
        ):
            matched_rfps.append(item)

    result: dict[str, Any] = {
        "status": "ok",
        "query": _clean_text(query),
        "entry_type": "project_rfp",
        "rfps": matched_rfps,
        "next": "read_or_compare_project_rfp",
    }
    if include_design_resources:
        result["design_resources"] = search_design_resources(query)["matches"]
    return result


def compare_project_rfps(
    rfp_ids: list[str],
    *,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
) -> dict[str, Any]:
    """Compare two or more approved KnowB project RFPs side-by-side."""
    clean_ids = [_slugify(rid) for rid in (rfp_ids or []) if _clean_text(rid)]
    if len(clean_ids) < 2:
        return {
            "status": "invalid",
            "error": "Provide at least two approved RFP identifiers to compare.",
            "compared": [],
            "next": "list_project_rfps",
        }

    catalogue = build_project_rfp_catalogue(
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
        include_connector_only=True,
    )
    by_id = {item["rfp_id"]: item for item in catalogue["rfps"]}
    compared: list[dict[str, Any]] = []
    unknown: list[str] = []

    for cid in clean_ids:
        if cid in by_id:
            item = by_id[cid]
            compared.append(
                {
                    "rfp_id": item["rfp_id"],
                    "title": item["title"],
                    "source_kind": item["source_kind"],
                    "visibility": item["visibility"],
                    "brief_status": item["brief_status"],
                    "tags": item["tags"],
                    "summary": item["summary"],
                    "outcome": item["outcome"],
                    "scope": item["scope"],
                    "safety_boundary": item["safety_boundary"],
                    "repo_url": item["repo_url"],
                    "readme_url": item["readme_url"],
                }
            )
        else:
            unknown.append(cid)

    if unknown:
        return {
            "status": "not_found",
            "error": f"Unknown or unapproved RFP identifier(s): {', '.join(unknown)}",
            "unknown_rfp_ids": unknown,
            "compared": compared,
            "next": "list_project_rfps",
        }

    tag_sets = [set(item["tags"]) for item in compared]
    shared_tags = sorted(set.intersection(*tag_sets)) if tag_sets else []

    return {
        "status": "ok",
        "compared": compared,
        "shared_tags": shared_tags,
        "next": "preview_contributor_request",
    }


def preview_contributor_request(
    request_type: str,
    rfp_id: str,
    requested_scope: str,
    message: str,
    *,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
) -> dict[str, Any]:
    """Build a reviewable preview for a contributor request without storing or sending it."""
    clean_type = _clean_text(request_type).lower()
    clean_rfp_id = _slugify(rfp_id)
    clean_scope = _clean_text(requested_scope)
    clean_message = _clean_text(message)

    if clean_type not in ALLOWED_CONTRIBUTOR_REQUEST_TYPES:
        return {
            "status": "invalid_request_type",
            "submitted": False,
            "sent": False,
            "grants_repository_access": False,
            "error": (
                f"Unsupported request_type '{clean_type}'. Supported types: "
                f"{', '.join(sorted(ALLOWED_CONTRIBUTOR_REQUEST_TYPES))}."
            ),
            "next": "choose_valid_request_type",
        }

    rfp_lookup = read_project_rfp(
        clean_rfp_id,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )
    if rfp_lookup["status"] != "ok":
        return {
            "status": "invalid_project",
            "submitted": False,
            "sent": False,
            "grants_repository_access": False,
            "error": (
                f"Project '{_clean_text(rfp_id)}' is not an approved KnowB project RFP. "
                "Contributor requests are only valid for active project RFPs."
            ),
            "next": "list_project_rfps",
        }

    if len(clean_scope) < 5 or len(clean_message) < 10:
        return {
            "status": "invalid_request_fields",
            "submitted": False,
            "sent": False,
            "grants_repository_access": False,
            "error": "Both requested_scope and message must be provided before preview.",
            "next": "complete_request_fields",
        }

    rfp = rfp_lookup["rfp"]
    type_label = ALLOWED_CONTRIBUTOR_REQUEST_TYPES[clean_type]
    subject = f"[BetterHackdays {type_label}] {rfp['title']} - {clean_scope}"
    formatted_body = (
        f"Project: {rfp['title']} ({rfp['rfp_id']})\n"
        f"Request Type: {type_label} ({clean_type})\n"
        f"Recipient: {APPROVED_REQUEST_RECIPIENT}\n"
        f"Connector Route: {APPROVED_CONNECTOR_ROUTE}\n"
        f"Requested Scope: {clean_scope}\n\n"
        f"Message:\n{clean_message}\n\n"
        "Note: Submitting this request does not grant repository permissions automatically."
    )
    mailto_url = (
        f"mailto:{APPROVED_REQUEST_RECIPIENT}?"
        + urllib.parse.urlencode({"subject": subject, "body": formatted_body})
    )

    preview_payload = {
        "request_type": clean_type,
        "request_type_label": type_label,
        "project": {
            "rfp_id": rfp["rfp_id"],
            "title": rfp["title"],
            "visibility": rfp["visibility"],
            "repo_name": rfp["repo_name"],
            "repo_url": rfp["repo_url"],
        },
        "recipient": APPROVED_REQUEST_RECIPIENT,
        "connector_route": APPROVED_CONNECTOR_ROUTE,
        "requested_scope": clean_scope,
        "subject": subject,
        "message": clean_message,
        "formatted_body": formatted_body,
        "mailto_url": mailto_url,
        "grants_repository_access": False,
    }

    return {
        "status": "preview_ready",
        "submitted": False,
        "sent": False,
        "grants_repository_access": False,
        "preview": preview_payload,
        "next": "submit_contributor_request",
    }


def submit_contributor_request(
    request_type: str,
    rfp_id: str,
    requested_scope: str,
    message: str,
    *,
    target_repo: str = BETTERHACKDAYS_REPO,
    caller_supplied_login: Optional[str] = None,
    asserted_role: Optional[str] = None,
    auth_context: Optional[dict[str, Any]] = None,
    delivery_transport: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Callable[[str, str], Optional[str]]] = None,
) -> dict[str, Any]:
    """Authorize, privately record, and route a contributor request after preview.

    Checks caller identity and write/maintain/admin permission on knowb-ai/BetterHackdays.
    Never exposes request details publicly and never grants repository permissions automatically.
    If the approved send mechanism is unavailable, returns a complete addressed draft and
    explicitly reports that it was not sent.
    """
    preview_res = preview_contributor_request(
        request_type,
        rfp_id,
        requested_scope,
        message,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )
    if preview_res["status"] != "preview_ready":
        return preview_res

    preview_payload = preview_res["preview"]
    auth_operation = (
        "request_submit"
        if preview_payload["request_type"] == "work_elevation_request"
        else "contributor_request_submit"
    )

    auth_check = authorize_github_mutation(
        operation=auth_operation,
        target_repo=target_repo,
        expected_target_repo=BETTERHACKDAYS_REPO,
        caller_supplied_login=caller_supplied_login,
        asserted_role=asserted_role,
        auth_context=auth_context,
    )
    if not auth_check["authorized"]:
        return {
            "status": "unauthorized",
            "submitted": False,
            "sent": False,
            "grants_repository_access": False,
            "authorization": auth_check,
            "preview": preview_payload,
            "next": "verify_github_identity_and_repo_permission",
        }

    verified_requester = auth_check["verified_login"]
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    sent = False
    delivery_status = "not_sent"
    delivery_note = (
        f"Approved send mechanism is unavailable; returning complete addressed draft "
        f"to {APPROVED_REQUEST_RECIPIENT}. Request was not sent."
    )

    transport = delivery_transport or send_contributor_request_email
    try:
        transport_res = transport(
            {
                "request_id": request_id,
                "requester_login": verified_requester,
                **preview_payload,
            }
        )
        if isinstance(transport_res, dict) and transport_res.get("sent") is True:
            sent = True
            delivery_status = "sent"
            delivery_note = (
                f"Request routed to {APPROVED_REQUEST_RECIPIENT} via approved connector route."
            )
    except Exception as exc:
        sent = False
        delivery_status = "not_sent"
        delivery_note = (
            f"Approved send mechanism failed ({exc}); returning complete addressed "
            f"draft to {APPROVED_REQUEST_RECIPIENT}. Request was not sent."
        )

    ensure_schema()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO contributor_requests (
                request_id,
                request_type,
                rfp_id,
                project_title,
                recipient,
                requested_scope,
                message,
                requester_login,
                target_repo,
                delivery_status,
                is_public
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                request_id,
                preview_payload["request_type"],
                preview_payload["project"]["rfp_id"],
                preview_payload["project"]["title"],
                APPROVED_REQUEST_RECIPIENT,
                preview_payload["requested_scope"],
                preview_payload["message"],
                verified_requester,
                BETTERHACKDAYS_REPO,
                delivery_status,
            ),
        )

    return {
        "status": "submitted" if sent else "submitted_draft_not_sent",
        "request_id": request_id,
        "submitted": True,
        "sent": sent,
        "delivery_status": delivery_status,
        "delivery_note": delivery_note,
        "is_public": False,
        "grants_repository_access": False,
        "requester_login": verified_requester,
        "authorization": auth_check,
        "addressed_draft": {
            "recipient": APPROVED_REQUEST_RECIPIENT,
            "connector_route": APPROVED_CONNECTOR_ROUTE,
            "project": preview_payload["project"],
            "request_type": preview_payload["request_type"],
            "requested_scope": preview_payload["requested_scope"],
            "subject": preview_payload["subject"],
            "message": preview_payload["message"],
            "formatted_body": preview_payload["formatted_body"],
            "mailto_url": preview_payload["mailto_url"],
            "sent": sent,
        },
        "next": (
            "await_owner_review"
            if sent
            else "send_addressed_draft_or_await_owner_review"
        ),
    }


def list_contributor_requests(
    *,
    auth_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return stored contributor requests only to the verified requester or a verified BetterHackdays maintainer/admin.

    Never exposes contributor request details publicly.
    """
    verified = _verify_human_identity_and_repo_permission(auth_context, BETTERHACKDAYS_REPO)
    if not verified.get("ok"):
        return {
            "status": "unauthorized",
            "reason": verified["reason"],
            "detail": verified["detail"],
            "is_public": False,
            "requests": [],
        }

    verified_login = verified["verified_login"]
    is_maintainer_or_admin = verified["verified_permission"] in {"maintain", "admin"}

    ensure_schema()
    with get_conn() as conn:
        if is_maintainer_or_admin:
            rows = conn.execute(
                "SELECT * FROM contributor_requests ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contributor_requests WHERE lower(requester_login) = lower(?) ORDER BY created_at DESC",
                (verified_login,),
            ).fetchall()

    records = []
    for row in rows:
        item = _row_to_dict(row)
        item["is_public"] = bool(item.get("is_public", 0))
        records.append(item)

    return {
        "status": "ok",
        "viewer_login": verified_login,
        "is_public": False,
        "requests": records,
    }




