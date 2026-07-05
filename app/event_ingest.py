"""Deterministic event ingest helpers for pasted hackathon text.

This M2 prototype intentionally favors obvious extraction over cleverness.
Every missing important field is surfaced as an open question so downstream
planning can stay honest about incomplete event context.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


KEY_FIELDS = (
    "event_name",
    "starts_at",
    "ends_at",
    "deadlines",
    "judging_criteria",
    "submission",
)

SOURCE_NOTE_FIELDS = (
    "event_name",
    "starts_at",
    "ends_at",
    "tracks",
    "team_size",
    "deadlines",
    "judging_criteria",
    "submission",
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:\t")


def _nonempty_lines(text: str) -> list[str]:
    return [_clean(line) for line in text.splitlines() if _clean(line)]


def _split_values(value: str) -> list[str]:
    value = re.sub(r"\band\b", ",", value, flags=re.IGNORECASE)
    parts = re.split(r"[,;|/]+", value)
    return [_clean(part) for part in parts if _clean(part)]


def _label_value(lines: list[str], *labels: str) -> str | None:
    pattern = re.compile(
        r"^(?:" + "|".join(re.escape(label) for label in labels) + r")\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    )
    for line in lines:
        match = pattern.match(line)
        if match:
            return _clean(match.group(1))
    return None


def _collect_labeled_values(lines: list[str], *labels: str) -> list[str]:
    value = _label_value(lines, *labels)
    return _split_values(value) if value else []


def _guess_event_name(lines: list[str]) -> str | None:
    explicit = _label_value(lines, "event", "event name", "name", "hackathon")
    if explicit:
        return explicit
    for line in lines[:5]:
        if re.search(r"\b(hackathon|hack day|builder day|buildathon)\b", line, re.I):
            return line
    return lines[0] if lines else None


def _guess_description(lines: list[str], event_name: str | None) -> str | None:
    for line in lines:
        if line == event_name:
            continue
        if re.match(r"^[A-Za-z ]{2,30}\s*[:\-]", line):
            continue
        if len(line) >= 40:
            return line
    return None


def _guess_format(text: str) -> str | None:
    low = text.lower()
    if any(token in low for token in ("hybrid", "online and in-person", "online & in-person")):
        return "hybrid"
    if any(token in low for token in ("online", "virtual", "remote")):
        return "online"
    if any(token in low for token in ("in person", "in-person", "venue", "campus")):
        return "in_person"
    return None


def _guess_team_size(text: str) -> dict[str, int | None] | None:
    patterns = (
        r"team size\s*[:\-]?\s*(\d+)\s*(?:-|to)\s*(\d+)",
        r"teams?\s+of\s+(?:up to\s+)?(\d+)",
        r"max(?:imum)?\s+team\s+size\s*[:\-]?\s*(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        if len(match.groups()) == 2 and match.group(2):
            return {"min": int(match.group(1)), "max": int(match.group(2))}
        return {"min": None, "max": int(match.group(1))}
    return None


def _extract_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s)>\]]+", text)
    return match.group(0).rstrip(".,") if match else None


def _extract_time_value(line: str) -> str | None:
    match = re.search(
        r"(\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2})?|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?(?:\s+\d{1,2}:\d{2})?|"
        r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?(?:\s+\d{4})?(?:\s+\d{1,2}:\d{2})?)",
        line,
        re.IGNORECASE,
    )
    return _clean(match.group(1)) if match else None


def _extract_labeled_time(lines: list[str], *labels: str) -> str | None:
    value = _label_value(lines, *labels)
    if value:
        return _extract_time_value(value) or value
    for line in lines:
        if any(label.lower() in line.lower() for label in labels):
            value = _extract_time_value(line)
            if value:
                return value
    return None


def _extract_deadlines(lines: list[str]) -> list[dict[str, str | None]]:
    out: list[dict[str, str | None]] = []
    for line in lines:
        if not re.search(r"\b(deadline|due|submit|submission|final)\b", line, re.I):
            continue
        if re.search(r"\b(requirement|requirements)\b", line, re.I):
            continue
        due_at = _extract_time_value(line)
        name = "Deadline"
        if re.search(r"\b(final|submit|submission)\b", line, re.I):
            name = "Final submission"
        out.append({"name": name, "due_at": due_at, "description": line})
    return out


def _extract_judging(lines: list[str]) -> list[dict[str, str | None]]:
    values = _collect_labeled_values(lines, "judging", "judging criteria", "criteria")
    if not values:
        values = [
            line for line in lines
            if re.search(r"\bjudg(e|ing)|criteria|scored on\b", line, re.I)
        ]
    return [{"name": value, "description": value} for value in values]


def _extract_prefixed_lines(lines: list[str], *prefixes: str) -> list[str]:
    out: list[str] = []
    for line in lines:
        if any(re.search(rf"\b{re.escape(prefix)}\b", line, re.I) for prefix in prefixes):
            out.append(line)
    return out


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return any(_has_value(v) for v in value.values())
    return bool(value)


def _source_notes(context: dict[str, Any], source_label: str) -> list[dict[str, str]]:
    return [
        {
            "field": field,
            "source_label": source_label,
            "confidence": "high",
            "note": "Extracted from pasted text.",
        }
        for field in SOURCE_NOTE_FIELDS
        if _has_value(context.get(field))
    ]


def ingest_pasted_event_text(
    text: str,
    *,
    source_label: str = "Pasted event text",
    source_url: str | None = None,
) -> dict[str, Any]:
    """Normalize pasted event text into the M2 event context schema."""
    lines = _nonempty_lines(text)
    event_name = _guess_event_name(lines)
    source = {
        "source_type": "pasted_text",
        "source_label": source_label,
        "source_url": source_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    submission_url = _label_value(lines, "submission url", "submit", "submission")
    if submission_url and not submission_url.startswith(("http://", "https://")):
        submission_url = _extract_url(submission_url)

    context: dict[str, Any] = {
        "event_name": event_name,
        "description": _guess_description(lines, event_name),
        "format": _guess_format(text),
        "location": _label_value(lines, "location", "venue", "where"),
        "timezone": _label_value(lines, "timezone", "time zone"),
        "starts_at": _extract_labeled_time(lines, "starts", "start", "starts at", "start time"),
        "ends_at": _extract_labeled_time(lines, "ends", "end", "ends at", "end time"),
        "tracks": _collect_labeled_values(lines, "tracks", "track", "themes", "theme", "categories"),
        "team_size": _guess_team_size(text),
        "deadlines": _extract_deadlines(lines),
        "judging_criteria": _extract_judging(lines),
        "rules": _extract_prefixed_lines(lines, "rule", "rules", "forbidden"),
        "constraints": _extract_prefixed_lines(lines, "constraint", "constraints", "must", "required"),
        "sponsors": [
            {"name": sponsor, "requirements": []}
            for sponsor in _collect_labeled_values(lines, "sponsors", "sponsor")
        ],
        "submission": {
            "url": submission_url or _extract_url(text),
            "requirements": _collect_labeled_values(lines, "submission requirements", "requirements"),
        },
        "allowed_tools": _collect_labeled_values(lines, "allowed tools", "tools"),
        "recommended_tools": _collect_labeled_values(lines, "recommended tools", "recommended"),
        "open_questions": [],
        "confidence": "low",
        "sources": [source],
        "source_notes": [],
    }

    missing = [
        field for field in KEY_FIELDS
        if not context.get(field)
        or (field == "submission" and not any(context["submission"].values()))
    ]
    context["open_questions"] = [
        f"Missing or unclear: {field.replace('_', ' ')}"
        for field in missing
    ]

    present_key_fields = len(KEY_FIELDS) - len(missing)
    if present_key_fields >= 5:
        context["confidence"] = "high"
    elif present_key_fields >= 3:
        context["confidence"] = "medium"
    context["source_notes"] = _source_notes(context, source_label)

    return {
        "status": "ingested",
        "event": context,
        "missing_fields": missing,
        "next": "review_event_context",
    }
