"""MCP-friendly function abstraction layer.

These plain Python functions are the single integration point for any MCP
server we build later. They always return plain dicts/lists (no Pydantic
models, no FastAPI objects) so they can be wrapped by any tool protocol.

The FastAPI routes in `app/main.py` call these same functions, so the REST
and MCP surfaces never drift.

A future work package can register these as actual MCP tools by adding an
`mcp.server.fastmcp.FastMCP` wrapper that points at these functions.
"""

from __future__ import annotations

from typing import Any, Optional

from . import event_ingest, matchmaking, planner, rfp_connector, slug_resolution
from .db import _dumps, _loads, _row_to_dict, get_conn


class ProfileNotFoundError(ValueError):
    """Raised when an action requires an existing profile."""


def _profile_row_to_dict(row: Any) -> dict[str, Any]:
    data = _row_to_dict(row)
    data["skills"] = _loads(data.get("skills"))
    data["interests"] = _loads(data.get("interests"))
    data["looking_for"] = _loads(data.get("looking_for"))
    data["is_seeded"] = bool(data.get("is_seeded"))
    return data


def _require_profiles(*harness_ids: str) -> None:
    missing: list[str] = []
    with get_conn() as conn:
        for harness_id in harness_ids:
            row = conn.execute(
                "SELECT 1 FROM profiles WHERE harness_id = ?",
                (harness_id,),
            ).fetchone()
            if row is None:
                missing.append(harness_id)
    if missing:
        raise ProfileNotFoundError(
            "Unknown profile: " + ", ".join(sorted(set(missing)))
        )


def _get_or_create_profile(
    conn: Any,
    harness_id: str,
    create: bool = True,
) -> Optional[dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM profiles WHERE harness_id = ?",
        (harness_id,),
    ).fetchone()
    if row is not None:
        return _profile_row_to_dict(row)
    if not create:
        return None
    conn.execute(
        """
        INSERT INTO profiles (harness_id, display_label)
        VALUES (?, 'New builder')
        """,
        (harness_id,),
    )
    row = conn.execute(
        "SELECT * FROM profiles WHERE harness_id = ?",
        (harness_id,),
    ).fetchone()
    return _profile_row_to_dict(row)


def connect_harness(harness_id: str) -> dict[str, Any]:
    """Create or return the anonymous profile for a connecting harness.

    Returns a `next` action so the calling agent knows what to do first.
    """
    with get_conn() as conn:
        profile = _get_or_create_profile(conn, harness_id, create=True)
    assert profile is not None  # created above
    return {
        "status": "connected",
        "profile": profile,
        "next": "update_profile",
    }


def update_profile(
    harness_id: str,
    display_label: Optional[str] = None,
    skills: Optional[list[str]] = None,
    interests: Optional[list[str]] = None,
    preferred_role: Optional[str] = None,
    project_vibe: Optional[str] = None,
    looking_for: Optional[list[str]] = None,
    availability: Optional[str] = None,
) -> dict[str, Any]:
    """Upsert (create-then-update) the profile for a harness_id."""
    with get_conn() as conn:
        existing = _get_or_create_profile(conn, harness_id, create=True)
        assert existing is not None

        # Merge over existing values: any omitted field keeps its current value.
        merged = {
            "display_label": display_label or existing["display_label"],
            "skills": _dumps(skills if skills is not None else existing["skills"]),
            "interests": _dumps(
                interests if interests is not None else existing["interests"]
            ),
            "preferred_role": (
                preferred_role
                if preferred_role is not None
                else existing["preferred_role"]
            ),
            "project_vibe": (
                project_vibe
                if project_vibe is not None
                else existing["project_vibe"]
            ),
            "looking_for": _dumps(
                looking_for if looking_for is not None else existing["looking_for"]
            ),
            "availability": (
                availability if availability is not None else existing["availability"]
            ),
        }

        conn.execute(
            """
            UPDATE profiles SET
                display_label = ?,
                skills = ?,
                interests = ?,
                preferred_role = ?,
                project_vibe = ?,
                looking_for = ?,
                availability = ?,
                updated_at = datetime('now')
            WHERE harness_id = ?
            """,
            (
                merged["display_label"],
                merged["skills"],
                merged["interests"],
                merged["preferred_role"],
                merged["project_vibe"],
                merged["looking_for"],
                merged["availability"],
                harness_id,
            ),
        )
        profile = _profile_row_to_dict(
            conn.execute(
                "SELECT * FROM profiles WHERE harness_id = ?",
                (harness_id,),
            ).fetchone()
        )

    return {
        "status": "updated",
        "profile": profile,
        "next": "get_match_cards",
    }


def get_match_cards(harness_id: str) -> dict[str, Any]:
    """Return the scored, sorted, anonymized card deck for a harness."""
    return {"cards": matchmaking.get_match_cards(harness_id)}


def like_profile(from_harness_id: str, to_harness_id: str) -> dict[str, Any]:
    """Like a candidate and create a mutual match when reciprocated."""
    _require_profiles(from_harness_id, to_harness_id)
    return matchmaking.like_profile(from_harness_id, to_harness_id)


def pass_profile(from_harness_id: str, to_harness_id: str) -> dict[str, Any]:
    """Pass on a candidate. Passes never create matches."""
    _require_profiles(from_harness_id, to_harness_id)
    return matchmaking.pass_profile(from_harness_id, to_harness_id)


def get_matches(harness_id: str) -> dict[str, Any]:
    """Return all open matches involving a harness."""
    return {"matches": matchmaking.get_matches(harness_id)}


def start_survey(harness_id: str) -> dict[str, Any]:
    """Start or restart the onboarding survey for a harness."""
    from . import survey

    return survey.start_survey(harness_id)


def answer_survey(harness_id: str, answer: str) -> dict[str, Any]:
    """Record one survey answer and return the next survey state."""
    from . import survey

    return survey.answer_survey(harness_id, answer)


def get_survey_state(harness_id: str) -> dict[str, Any]:
    """Return current survey progress without advancing."""
    from . import survey

    return survey.survey_state(harness_id)


def ingest_event_text(
    text: str,
    source_label: str = "Pasted event text",
    source_url: str | None = None,
) -> dict[str, Any]:
    """Return normalized event context extracted from pasted event text."""
    return event_ingest.ingest_pasted_event_text(
        text,
        source_label=source_label,
        source_url=source_url,
    )


def rank_idea_suggestions(
    event: Any,
    profile: Any = None,
    team: Optional[list[Any]] = None,
    topics: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Return concise ranked hackathon ideas from event and team signals."""
    return planner.rank_idea_suggestions(
        event,
        profile=profile,
        team=team,
        topics=topics,
    )


def generate_process_timeline(
    event: Any,
    profile: Any = None,
    team: Optional[list[Any]] = None,
    hack_day: Any = None,
    team_room: Any = None,
    workspace_repo: Any = None,
) -> dict[str, Any]:
    """Return a concise deadline-aware Hack Day execution timeline."""
    return planner.generate_process_timeline(
        event,
        profile=profile,
        team=team,
        hack_day=hack_day,
        team_room=team_room,
        workspace_repo=workspace_repo,
    )


def generate_prep_checklist(
    event: Any,
    profile: Any = None,
    team: Optional[list[Any]] = None,
    hack_day: Any = None,
    team_room: Any = None,
    workspace_repo: Any = None,
) -> dict[str, Any]:
    """Return a concise actionable Hack Day prep checklist."""
    return planner.generate_prep_checklist(
        event,
        profile=profile,
        team=team,
        hack_day=hack_day,
        team_room=team_room,
        workspace_repo=workspace_repo,
    )


def resolve_slug(
    raw_input: str,
    hack_days: list[dict[str, Any]],
    standalone_slugs: Optional[list[dict[str, Any]]] = None,
    caller_participant_id: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve a Hack Day code, standalone slug, or namespaced room keyword."""
    return slug_resolution.resolve_slug(
        raw_input,
        hack_days=hack_days,
        standalone_slugs=standalone_slugs,
        caller_participant_id=caller_participant_id,
    )


def list_project_rfps(
    visibility: Optional[str] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """List approved KnowB project RFPs and public resources separately from idea suggestions."""
    return rfp_connector.list_project_rfps(
        visibility=visibility,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )


def read_project_rfp(
    rfp_id: str,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Read a single approved KnowB project RFP brief by ID or title."""
    return rfp_connector.read_project_rfp(
        rfp_id,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )


def search_project_rfps(
    query: str,
    include_design_resources: bool = False,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Search approved project RFPs and optionally allowlisted public design resources."""
    return rfp_connector.search_project_rfps(
        query,
        include_design_resources=include_design_resources,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )


def compare_project_rfps(
    rfp_ids: list[str],
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Compare two or more approved KnowB project RFPs side-by-side."""
    return rfp_connector.compare_project_rfps(
        rfp_ids,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )


def list_design_resources() -> dict[str, Any]:
    """List explicitly allowlisted public design philosophy documents and assets from knowb-ai.github.io."""
    return rfp_connector.list_design_resources()


def read_design_resource(
    path: str,
    repo: str = rfp_connector.DESIGN_RESOURCE_REPO,
    content_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Read an allowlisted public design philosophy document or asset from knowb-ai.github.io."""
    return rfp_connector.read_design_resource(
        path,
        repo=repo,
        content_fetcher=content_fetcher,
    )


def search_design_resources(query: str) -> dict[str, Any]:
    """Search allowlisted public design philosophy documents and assets."""
    return rfp_connector.search_design_resources(query)


def fetch_idea_catalogue(
    query: Optional[str] = None,
    section: Optional[str] = None,
    limit: Optional[int] = None,
    source_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Fetch the canonical Cloud Builder Stack idea catalogue live and return suggestions separately from RFPs."""
    return rfp_connector.fetch_idea_catalogue(
        query=query,
        section=section,
        limit=limit,
        source_fetcher=source_fetcher,
    )


def qualify_idea(
    title: str,
    summary: str,
    alignment_evidence: Optional[str] = None,
    human_reviewed_rationale: Optional[str] = None,
    reviewed_by: Optional[str] = None,
    source_fetcher: Optional[Any] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Deterministically qualify a candidate idea against the canonical catalogue, open public projects, and showcase."""
    return rfp_connector.qualify_idea(
        title,
        summary,
        alignment_evidence=alignment_evidence,
        human_reviewed_rationale=human_reviewed_rationale,
        reviewed_by=reviewed_by,
        source_fetcher=source_fetcher,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )


def propose_idea_catalogue_addition(
    title: str,
    summary: str,
    alignment_evidence: Optional[str] = None,
    human_reviewed_rationale: Optional[str] = None,
    reviewed_by: Optional[str] = None,
    section: str = "10. Stronger Actual AI System Ideas",
    submit: bool = False,
    source_fetcher: Optional[Any] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
    policy_inspector: Optional[Any] = None,
    policy_pr_url: Optional[str] = None,
    auth_context: Optional[dict[str, Any]] = None,
    pr_submitter: Optional[Any] = None,
) -> dict[str, Any]:
    """Preview and optionally submit a qualified, human-reviewed idea as a PR to Cloud Builder Stack."""
    return rfp_connector.propose_idea_catalogue_addition(
        title,
        summary,
        alignment_evidence=alignment_evidence,
        human_reviewed_rationale=human_reviewed_rationale,
        reviewed_by=reviewed_by,
        section=section,
        submit=submit,
        source_fetcher=source_fetcher,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
        policy_inspector=policy_inspector,
        policy_pr_url=policy_pr_url,
        auth_context=auth_context,
        pr_submitter=pr_submitter,
    )


def preview_contributor_request(
    request_type: str,
    rfp_id: str,
    requested_scope: str,
    message: str,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Preview a refinement draft, expression of interest, contribution-access request, or work-elevation request."""
    return rfp_connector.preview_contributor_request(
        request_type,
        rfp_id,
        requested_scope,
        message,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )


def submit_contributor_request(
    request_type: str,
    rfp_id: str,
    requested_scope: str,
    message: str,
    target_repo: str = rfp_connector.BETTERHACKDAYS_REPO,
    caller_supplied_login: Optional[str] = None,
    asserted_role: Optional[str] = None,
    auth_context: Optional[dict[str, Any]] = None,
    delivery_transport: Optional[Any] = None,
    repo_metadata: Optional[list[dict[str, Any]]] = None,
    readme_fetcher: Optional[Any] = None,
) -> dict[str, Any]:
    """Submit a contributor request after verifying caller identity and write/maintain/admin permission on BetterHackdays."""
    return rfp_connector.submit_contributor_request(
        request_type,
        rfp_id,
        requested_scope,
        message,
        target_repo=target_repo,
        caller_supplied_login=caller_supplied_login,
        asserted_role=asserted_role,
        auth_context=auth_context,
        delivery_transport=delivery_transport,
        repo_metadata=repo_metadata,
        readme_fetcher=readme_fetcher,
    )


def list_contributor_requests(
    auth_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """List private contributor requests for the verified requester or a verified BetterHackdays maintainer/admin."""
    return rfp_connector.list_contributor_requests(auth_context=auth_context)


def authorize_github_mutation(
    operation: str,
    target_repo: str,
    expected_target_repo: Optional[str] = None,
    caller_supplied_login: Optional[str] = None,
    asserted_role: Optional[str] = None,
    auth_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Verify caller GitHub identity, target repository permission, and Kenobi installation scope before a mutation."""
    return rfp_connector.authorize_github_mutation(
        operation=operation,
        target_repo=target_repo,
        expected_target_repo=expected_target_repo,
        caller_supplied_login=caller_supplied_login,
        asserted_role=asserted_role,
        auth_context=auth_context,
    )


def grant_repository_access(
    target_repo: str,
    grantee_login: str,
    permission: str = "write",
    requester_login: Optional[str] = None,
    confirmed: bool = False,
    auth_context: Optional[dict[str, Any]] = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Separate owner-only, explicitly confirmed repository access grant scoped to an allowlisted repository."""
    return rfp_connector.grant_repository_access(
        target_repo=target_repo,
        grantee_login=grantee_login,
        permission=permission,
        requester_login=requester_login,
        confirmed=confirmed,
        auth_context=auth_context,
        dry_run=dry_run,
    )


# Registry for a future MCP server to enumerate and register these as tools.
MCP_TOOLS = {
    "connect_harness": connect_harness,
    "update_profile": update_profile,
    "get_match_cards": get_match_cards,
    "like_profile": like_profile,
    "pass_profile": pass_profile,
    "get_matches": get_matches,
    "start_survey": start_survey,
    "answer_survey": answer_survey,
    "get_survey_state": get_survey_state,
    "ingest_event_text": ingest_event_text,
    "rank_idea_suggestions": rank_idea_suggestions,
    "generate_process_timeline": generate_process_timeline,
    "generate_prep_checklist": generate_prep_checklist,
    "resolve_slug": resolve_slug,
    "list_project_rfps": list_project_rfps,
    "read_project_rfp": read_project_rfp,
    "search_project_rfps": search_project_rfps,
    "compare_project_rfps": compare_project_rfps,
    "list_design_resources": list_design_resources,
    "read_design_resource": read_design_resource,
    "search_design_resources": search_design_resources,
    "fetch_idea_catalogue": fetch_idea_catalogue,
    "qualify_idea": qualify_idea,
    "propose_idea_catalogue_addition": propose_idea_catalogue_addition,
    "preview_contributor_request": preview_contributor_request,
    "submit_contributor_request": submit_contributor_request,
    "list_contributor_requests": list_contributor_requests,
    "authorize_github_mutation": authorize_github_mutation,
    "grant_repository_access": grant_repository_access,
}
