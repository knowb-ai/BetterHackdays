"""Matchmaking engine: card generation, scoring, and match creation.

There are no embeddings and no LLM scoring here. The heuristic is deliberately
tiny and demo-friendly, matching the work-package spec:

    +2 for each shared interest
    +2 if candidate has a skill in the user's looking_for
    +2 if the user has a skill in the candidate's looking_for
    +1 if project_vibe overlaps or is similar
    -1 if both have exactly the same preferred_role and neither is looking
        for that role
"""

from __future__ import annotations

import secrets
import sqlite3
from typing import Any

from .db import _dumps, _loads, _row_to_dict, get_conn


# --- helpers -----------------------------------------------------------------


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _norm_list(values: list[Any] | None) -> set[str]:
    return {_norm(v) for v in (values or []) if _norm(v)}


def _tokenize(value: str | None) -> set[str]:
    """Split a free-text field into normalized tokens for fuzzy overlap."""
    text = _norm(value)
    if not text:
        return set()
    tokens: set[str] = set()
    for sep in ("/", "-", ",", "&", " and "):
        text = text.replace(sep, " ")
    return {t for t in text.split() if len(t) > 2}


def _profile_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    """Decode a profile row into a dict with parsed list columns."""
    if row is None:
        return {}
    data = _row_to_dict(row)
    data["skills"] = _loads(data.get("skills"))
    data["interests"] = _loads(data.get("interests"))
    data["looking_for"] = _loads(data.get("looking_for"))
    data["is_seeded"] = bool(data.get("is_seeded"))
    return data


# sqlite3 is imported only for the type hint above; import lazily so the
# module can still be introspected in environments that stub it out.
import sqlite3  # noqa: E402  (kept here to keep the type hint above meaningful)


# --- card generation ---------------------------------------------------------


def _candidate_ids_to_exclude(harness_id: str) -> set[str]:
    """harness_ids to hide from a builder's card deck.

    Excludes self, anyone already liked, anyone already passed, and anyone
    already in a mutual match with this harness.
    """
    excluded: set[str] = {harness_id}
    with get_conn() as conn:
        swiped = conn.execute(
            "SELECT to_harness_id FROM swipes WHERE from_harness_id = ?",
            (harness_id,),
        ).fetchall()
        for row in swiped:
            excluded.add(row["to_harness_id"])

        matches = conn.execute(
            "SELECT harness_ids FROM matches WHERE status != 'closed'"
        ).fetchall()
        for row in matches:
            ids = _loads(row["harness_ids"])
            if harness_id in ids:
                excluded.update(ids)
    return excluded


def _score_pair(user: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, str]:
    """Return (match_score, human-readable match_reason) for a candidate."""
    score = 0
    reasons: list[str] = []

    user_interests = _norm_list(user.get("interests"))
    cand_interests = _norm_list(candidate.get("interests"))
    shared_interests = user_interests & cand_interests
    if shared_interests:
        score += 2 * len(shared_interests)
        sample = sorted(shared_interests)[:2]
        reasons.append(
            f"Shared interest in {', '.join(sample)}"
            + (" and more" if len(shared_interests) > 2 else "")
        )

    user_looking = _norm_list(user.get("looking_for"))
    cand_skills = _norm_list(candidate.get("skills"))
    cand_satisfies = cand_skills & user_looking
    if cand_satisfies:
        score += 2
        sample = sorted(cand_satisfies)[:2]
        reasons.append(
            f"Strong complement: you need {', '.join(sample)}"
            + (" and more" if len(cand_satisfies) > 2 else "")
            + " and they offer it"
        )

    cand_looking = _norm_list(candidate.get("looking_for"))
    user_skills = _norm_list(user.get("skills"))
    user_satisfies = user_skills & cand_looking
    if user_satisfies:
        score += 2
        sample = sorted(user_satisfies)[:2]
        reasons.append(
            f"You offer {', '.join(sample)}"
            + (" and more" if len(user_satisfies) > 2 else "")
            + " which they're looking for"
        )

    user_vibe = _tokenize(user.get("project_vibe"))
    cand_vibe = _tokenize(candidate.get("project_vibe"))
    if user_vibe and cand_vibe and (user_vibe & cand_vibe):
        score += 1
        reasons.append("Similar project vibe")

    user_role = _norm(user.get("preferred_role"))
    cand_role = _norm(candidate.get("preferred_role"))
    same_role = user_role and cand_role and user_role == cand_role
    neither_looking = (
        user_role not in cand_looking and cand_role not in user_looking
    )
    if same_role and neither_looking:
        score -= 1
        reasons.append(f"Same role ({user_role}) on both sides")

    # Floor the score at 0 for display, but keep a neutral reason if nothing fired.
    display_score = max(score, 0)
    if not reasons:
        reasons.append("New candidate to evaluate")
    return display_score, ". ".join(reasons) + "."


def get_match_cards(harness_id: str) -> list[dict[str, Any]]:
    """Build the anonymized, scored, sorted card deck for a harness."""
    with get_conn() as conn:
        user_row = conn.execute(
            "SELECT * FROM profiles WHERE harness_id = ?",
            (harness_id,),
        ).fetchone()
        if user_row is None:
            return []
        user = _profile_dict(user_row)

        excluded = _candidate_ids_to_exclude(harness_id)
        rows = conn.execute(
            "SELECT * FROM profiles WHERE harness_id != ? ORDER BY created_at ASC",
            (harness_id,),
        ).fetchall()

    cards: list[dict[str, Any]] = []
    for row in rows:
        candidate = _profile_dict(row)
        if candidate["harness_id"] in excluded:
            continue
        # Auto-skip seeded builders that are looking for the user's role if the
        # user has not provided profile data yet (keeps blank profiles out of
        # noisy decks); still allow once the user has set interests/skills.
        score, reason = _score_pair(user, candidate)
        cards.append(
            {
                "harness_id": candidate["harness_id"],
                "display_label": candidate["display_label"],
                "skills": candidate["skills"],
                "interests": candidate["interests"],
                "preferred_role": candidate.get("preferred_role"),
                "project_vibe": candidate.get("project_vibe"),
                "looking_for": candidate["looking_for"],
                "match_score": score,
                "match_reason": reason,
            }
        )

    cards.sort(key=lambda c: c["match_score"], reverse=True)
    return cards


# --- likes, passes, and matches ----------------------------------------------


def _find_match(conn: sqlite3.Connection, a: str, b: str) -> dict[str, Any] | None:
    """Return the match record for a pair, regardless of order."""
    rows = conn.execute(
        "SELECT * FROM matches WHERE harness_ids LIKE ?",
        (f'%"{a}"%',),
    ).fetchall()
    for row in rows:
        ids = _loads(row["harness_ids"])
        if a in ids and b in ids:
            data = _row_to_dict(row)
            data["harness_ids"] = ids
            return data
    return None


def _new_match_id() -> str:
    return "match_" + secrets.token_hex(6)


def like_profile(from_harness_id: str, to_harness_id: str) -> dict[str, Any]:
    """Record a like and create a mutual match when the like is reciprocated."""
    with get_conn() as conn:
        existing_match = _find_match(conn, from_harness_id, to_harness_id)
        if existing_match:
            return {
                "status": "matched",
                "mutual_match": True,
                "match_id": existing_match["match_id"],
                "harness_ids": sorted(existing_match["harness_ids"]),
                "next": "proceed_or_find_more",
            }

        # Upsert the swipe as a like (a prior pass is upgraded to a like).
        conn.execute(
            """
            INSERT INTO swipes (from_harness_id, to_harness_id, action)
            VALUES (?, ?, 'like')
            ON CONFLICT(from_harness_id, to_harness_id) DO UPDATE SET action = 'like'
            """,
            (from_harness_id, to_harness_id),
        )

        reverse = conn.execute(
            "SELECT 1 FROM swipes WHERE from_harness_id = ? AND to_harness_id = ? AND action = 'like'",
            (to_harness_id, from_harness_id),
        ).fetchone()

        if reverse:
            match_id = _new_match_id()
            harness_ids = sorted([from_harness_id, to_harness_id])
            conn.execute(
                """
                INSERT INTO matches (match_id, harness_ids, status)
                VALUES (?, ?, 'matched')
                """,
                (match_id, _dumps(harness_ids)),
            )
            return {
                "status": "matched",
                "mutual_match": True,
                "match_id": match_id,
                "harness_ids": harness_ids,
                "next": "proceed_or_find_more",
            }

        return {
            "status": "liked",
            "mutual_match": False,
            "next": "keep_matching",
        }


def pass_profile(from_harness_id: str, to_harness_id: str) -> dict[str, Any]:
    """Record a pass. Passes never create matches."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO swipes (from_harness_id, to_harness_id, action)
            VALUES (?, ?, 'pass')
            ON CONFLICT(from_harness_id, to_harness_id) DO UPDATE SET action = 'pass'
            """,
            (from_harness_id, to_harness_id),
        )
    return {"status": "passed", "next": "keep_matching"}


def get_matches(harness_id: str) -> list[dict[str, Any]]:
    """Return all open matches involving a harness, newest first."""
    out: list[dict[str, Any]] = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM matches WHERE harness_ids LIKE ? ORDER BY created_at DESC",
            (f'%"{harness_id}"%',),
        ).fetchall()
        for row in rows:
            ids = _loads(row["harness_ids"])
            if harness_id not in ids:
                continue
            out.append(
                {
                    "match_id": row["match_id"],
                    "harness_ids": ids,
                    "status": row["status"],
                    "next": "proceed_or_find_more",
                }
            )
    return out
