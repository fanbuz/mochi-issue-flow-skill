#!/usr/bin/env python3
"""Prepare and apply a two-phase archive for superseded Flow Card evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from flow_status import canonical_json


class ArchiveError(ValueError):
    """Raised when an evidence archive cannot be prepared or safely applied."""


def _find_axis_state(card: dict[str, Any], bridge_id: str, axis: str) -> dict[str, Any]:
    for bridge in card.get("bridges", []):
        if isinstance(bridge, dict) and bridge.get("bridgeId") == bridge_id:
            state = bridge.get(f"{axis}State")
            if not isinstance(state, dict):
                raise ArchiveError(f"bridge {bridge_id} has no {axis}State")
            return state
    raise ArchiveError(f"unknown bridgeId: {bridge_id}")


def archive_hash(archive: dict[str, Any]) -> str:
    payload = canonical_json(archive).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _artifact_set_ids(superseded: list[Any]) -> list[str]:
    artifact_set_ids: list[str] = []
    for item in superseded:
        if not isinstance(item, dict):
            continue
        for field in ("commitSetId", "supersededBy"):
            value = item.get(field)
            if isinstance(value, str) and value not in artifact_set_ids:
                artifact_set_ids.append(value)
    return artifact_set_ids


def _validate_created_at(created_at: Any) -> None:
    if not isinstance(created_at, str):
        raise ArchiveError("createdAt must be an ISO-8601 timestamp")
    try:
        value = created_at[:-1] + "+00:00" if created_at.endswith("Z") else created_at
        created = datetime.fromisoformat(value)
    except ValueError as error:
        raise ArchiveError("createdAt must be an ISO-8601 timestamp") from error
    if created.tzinfo is None:
        raise ArchiveError("createdAt must include a timezone")


def prepare_archive(
    card: dict[str, Any], bridge_id: str, axis: str, created_at: str
) -> dict[str, Any]:
    if axis not in {"code", "runtime"}:
        raise ArchiveError("axis must be code or runtime")
    _validate_created_at(created_at)
    state = _find_axis_state(card, bridge_id, axis)
    superseded = state.get("supersededEvidence", [])
    if not isinstance(superseded, list) or not superseded:
        raise ArchiveError("there is no superseded evidence to archive")

    artifact_set_ids = _artifact_set_ids(superseded)

    archive = {
        "archiveVersion": "1",
        "flowId": card.get("flowId"),
        "bridgeId": bridge_id,
        "axis": axis,
        "sourceStatusRevision": card.get("statusRevision"),
        "createdAt": created_at,
        "artifactSetIds": artifact_set_ids,
        "evidenceCount": len(superseded),
        "supersededEvidence": copy.deepcopy(superseded),
    }
    return {
        "archive": archive,
        "contentHash": archive_hash(archive),
        "expectedStatusRevision": card.get("statusRevision"),
    }


def apply_archive(
    card: dict[str, Any], archive: dict[str, Any], archive_url: str, expected_hash: str
) -> dict[str, Any]:
    if not isinstance(archive_url, str) or not archive_url:
        raise ArchiveError("archive URL is required")
    actual_hash = archive_hash(archive)
    if expected_hash != actual_hash:
        raise ArchiveError("archive content hash does not match the prepared archive")
    if archive.get("archiveVersion") != "1":
        raise ArchiveError("archiveVersion is unsupported")
    if not card.get("flowId") or archive.get("flowId") != card.get("flowId"):
        raise ArchiveError("archive flowId does not match the Flow Card")
    expected_revision = archive.get("sourceStatusRevision")
    if type(expected_revision) is not int:
        raise ArchiveError("archive sourceStatusRevision is invalid")
    if card.get("statusRevision") != expected_revision:
        raise ArchiveError("Flow Card revision changed after archive preparation")

    bridge_id = archive.get("bridgeId")
    axis = archive.get("axis")
    if not isinstance(bridge_id, str) or axis not in {"code", "runtime"}:
        raise ArchiveError("archive identity is invalid")
    _validate_created_at(archive.get("createdAt"))
    superseded = archive.get("supersededEvidence")
    if not isinstance(superseded, list) or not superseded:
        raise ArchiveError("archive supersededEvidence is invalid")
    if type(archive.get("evidenceCount")) is not int or archive.get("evidenceCount") != len(superseded):
        raise ArchiveError("archive evidenceCount does not match supersededEvidence")
    if archive.get("artifactSetIds") != _artifact_set_ids(superseded):
        raise ArchiveError("archive artifactSetIds do not match supersededEvidence")
    state = _find_axis_state(card, bridge_id, axis)
    if state.get("supersededEvidence", []) != superseded:
        raise ArchiveError("superseded evidence changed after archive preparation")

    updated = copy.deepcopy(card)
    updated_state = _find_axis_state(updated, bridge_id, axis)
    updated_state.setdefault("archiveRefs", []).append(
        {
            "url": archive_url,
            "contentHash": actual_hash,
            "artifactSetIds": copy.deepcopy(archive.get("artifactSetIds", [])),
            "evidenceCount": archive.get("evidenceCount", 0),
            "createdAt": archive.get("createdAt"),
        }
    )
    updated_state["supersededEvidence"] = []
    updated["statusRevision"] = int(expected_revision) + 1
    registry = updated.get("registry")
    if isinstance(registry, dict) and registry.get("status") == "synchronized":
        registry["status"] = "out-of-sync"
    return updated


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare or apply an offline evidence archive")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("flow_card", type=Path)
    prepare_parser.add_argument("bridge_id")
    prepare_parser.add_argument("axis", choices=("code", "runtime"))
    prepare_parser.add_argument("--created-at", required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("flow_card", type=Path)
    apply_parser.add_argument("archive", type=Path)
    apply_parser.add_argument("archive_url")
    apply_parser.add_argument("--expected-hash", required=True)
    args = parser.parse_args(argv[1:])

    try:
        card = json.loads(args.flow_card.read_text(encoding="utf-8"))
        if args.command == "prepare":
            result = prepare_archive(card, args.bridge_id, args.axis, args.created_at)
        else:
            loaded_archive = json.loads(args.archive.read_text(encoding="utf-8"))
            archive = loaded_archive.get("archive", loaded_archive)
            result = {
                "card": apply_archive(card, archive, args.archive_url, args.expected_hash)
            }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ArchiveError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
