from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


OKF_VERSION = "google-open-knowledge-format/v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_MANIFEST = REPO_ROOT / ".okf" / "manifest.json"
DOCS_MANIFEST = REPO_ROOT / "docs" / ".okf" / "manifest.json"


class OkfValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OkfValidationError(f"missing JSON file: {path.relative_to(REPO_ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise OkfValidationError(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}") from exc


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def title_from_markdown(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def governed_sources(manifest: dict[str, Any]) -> set[str]:
    sources: set[str] = set()
    for pattern in manifest.get("governed_patterns", []):
        for path in REPO_ROOT.glob(pattern):
            if path.is_file() and ".okf" not in path.parts:
                sources.add(rel(path))
    return sources


def require_string(record: dict[str, Any], field: str, context: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise OkfValidationError(f"{context} missing string field: {field}")
    return value


def validate_collection_shape(manifest: dict[str, Any], context: str) -> None:
    if manifest.get("okf_version") != OKF_VERSION:
        raise OkfValidationError(f"{context} has unsupported okf_version")
    if manifest.get("kind") != "knowledge_collection":
        raise OkfValidationError(f"{context} must be a knowledge_collection")
    require_string(manifest, "id", context)
    require_string(manifest, "title", context)
    documents = manifest.get("documents")
    if not isinstance(documents, list):
        raise OkfValidationError(f"{context} documents must be a list")


def validate_document_entry(entry: dict[str, Any], collection_context: str) -> None:
    source_path = require_string(entry, "source_path", collection_context)
    sidecar_path = require_string(entry, "okf_path", collection_context)
    require_string(entry, "id", collection_context)
    require_string(entry, "title", collection_context)
    expected_sha = require_string(entry, "sha256", collection_context)
    if len(expected_sha) != 64 or any(char not in "0123456789abcdef" for char in expected_sha):
        raise OkfValidationError(f"{source_path} has invalid sha256 in {collection_context}")

    source = REPO_ROOT / source_path
    sidecar = REPO_ROOT / sidecar_path
    if not source.is_file():
        raise OkfValidationError(f"missing source file: {source_path}")
    if not sidecar.is_file():
        raise OkfValidationError(f"missing OKF sidecar: {sidecar_path}")

    actual_sha = sha256(source)
    if actual_sha != expected_sha:
        raise OkfValidationError(f"checksum mismatch in {collection_context}: {source_path}")

    sidecar_record = load_json(sidecar)
    if sidecar_record.get("okf_version") != OKF_VERSION:
        raise OkfValidationError(f"{sidecar_path} has unsupported okf_version")
    if sidecar_record.get("kind") != "knowledge_document":
        raise OkfValidationError(f"{sidecar_path} must be a knowledge_document")
    if sidecar_record.get("id") != entry["id"]:
        raise OkfValidationError(f"{sidecar_path} id does not match manifest")
    if sidecar_record.get("title") != entry["title"]:
        raise OkfValidationError(f"{sidecar_path} title does not match manifest")
    if sidecar_record.get("source", {}).get("path") != source_path:
        raise OkfValidationError(f"{sidecar_path} source path does not match manifest")
    if sidecar_record.get("source", {}).get("sha256") != actual_sha:
        raise OkfValidationError(f"{sidecar_path} checksum does not match source")
    if sidecar_record.get("content", {}).get("path") != source_path:
        raise OkfValidationError(f"{sidecar_path} content path does not match source")


def validate_manifest(path: Path, expected_sources: set[str] | None = None) -> dict[str, Any]:
    manifest = load_json(path)
    context = rel(path)
    validate_collection_shape(manifest, context)
    documents = manifest["documents"]
    listed_sources = {require_string(entry, "source_path", context) for entry in documents}

    if expected_sources is not None and listed_sources != expected_sources:
        missing = sorted(expected_sources - listed_sources)
        extra = sorted(listed_sources - expected_sources)
        problems = []
        if missing:
            problems.append(f"missing {missing}")
        if extra:
            problems.append(f"extra {extra}")
        raise OkfValidationError(f"{context} source coverage mismatch: {', '.join(problems)}")

    for entry in documents:
        validate_document_entry(entry, context)
    return manifest


def validate() -> None:
    root_manifest = validate_manifest(ROOT_MANIFEST)
    validate_manifest(ROOT_MANIFEST, governed_sources(root_manifest))
    docs_sources = {rel(path) for path in (REPO_ROOT / "docs").glob("*.md")}
    validate_manifest(DOCS_MANIFEST, docs_sources)


def main() -> int:
    try:
        validate()
    except OkfValidationError as exc:
        print(f"OKF validation failed: {exc}")
        return 1
    print("OKF validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
