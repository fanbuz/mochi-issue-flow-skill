#!/usr/bin/env python3
"""Validate and verify carrier-neutral conditional edits of one canonical comment."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from flow_status import StatusReadError, canonical_card_hash, read_flow_card
from validate_flow_card import SHA256_PATTERN


SAFETY_MODES = {"atomic-cas", "best-effort-conditional"}


class ConditionalEditError(RuntimeError):
    """Stable failure raised before registry projection may continue."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CanonicalCommentAdapter(Protocol):
    """Network adapters implement only exact read and in-place edit operations."""

    supports_atomic_cas: bool

    def read_comment(self, url: str) -> dict[str, Any]: ...

    def edit_comment(self, url: str, body: str, precondition: dict[str, Any]) -> None: ...


def _request_fields(request: dict[str, Any]) -> tuple[str, int, str, str, dict[str, Any]]:
    url = request.get("canonicalStatusCommentUrl")
    revision = request.get("expectedStatusRevision")
    expected_hash = request.get("expectedCanonicalHash")
    safety_mode = request.get("safetyMode")
    target = request.get("targetCanonicalComment")
    if not isinstance(url, str) or not url:
        raise ConditionalEditError(
            "invalid-request",
            "canonicalStatusCommentUrl must identify an existing comment; bootstrap uses a separate path",
        )
    if type(revision) is not int or revision < 1:
        raise ConditionalEditError("invalid-request", "expectedStatusRevision must be a positive integer")
    if not isinstance(expected_hash, str) or not SHA256_PATTERN.match(expected_hash):
        raise ConditionalEditError("invalid-request", "expectedCanonicalHash must be a canonical SHA-256 value")
    if safety_mode not in SAFETY_MODES:
        raise ConditionalEditError("invalid-request", "safetyMode must be atomic-cas or best-effort-conditional")
    if not isinstance(target, dict) or target.get("url") != url or not isinstance(target.get("body"), str):
        raise ConditionalEditError(
            "invalid-request",
            "targetCanonicalComment must contain the same canonical URL and a complete replacement body",
        )
    return url, revision, expected_hash, safety_mode, target


def _read_target_card(request: dict[str, Any]) -> dict[str, Any]:
    url, expected_revision, _, _, target = _request_fields(request)
    try:
        card = read_flow_card(
            {
                "canonicalStatusCommentUrl": url,
                "canonicalComment": target,
            }
        )
    except StatusReadError as error:
        raise ConditionalEditError(
            "target-invalid",
            f"target canonical comment is invalid ({error.code})",
        ) from error
    if card.get("statusRevision") != expected_revision + 1:
        raise ConditionalEditError(
            "target-invalid",
            "target statusRevision must increment expectedStatusRevision by exactly one",
        )
    if card.get("canonicalStatusCommentUrl") != url:
        raise ConditionalEditError(
            "target-invalid",
            "target Flow Card canonicalStatusCommentUrl must keep the existing comment identity",
        )
    return card


def _read_live_card(request: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    url, _, _, _, _ = _request_fields(request)
    if not isinstance(snapshot, dict):
        raise ConditionalEditError(
            "canonical-read-failed",
            "adapter did not return a normalized canonical comment snapshot",
        )
    if snapshot.get("canonicalStatusCommentUrl") != url:
        raise ConditionalEditError(
            "canonical-identity-mismatch",
            "adapter returned a different canonical comment identity",
        )
    try:
        return read_flow_card(snapshot)
    except StatusReadError as error:
        raise ConditionalEditError(
            "canonical-read-failed",
            f"canonical comment could not be read exactly ({error.code})",
        ) from error


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ConditionalEditError("ownership-rejected", "active lease has no valid expiry")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as error:
        raise ConditionalEditError("ownership-rejected", "active lease has no valid expiry") from error
    if parsed.tzinfo is None:
        raise ConditionalEditError("ownership-rejected", "active lease expiry has no timezone")
    return parsed


def _verify_ownership(request: dict[str, Any], live_card: dict[str, Any], now: datetime) -> None:
    control = live_card.get("concurrencyControl")
    mode = control.get("mode", "lease") if isinstance(control, dict) else "lease"
    if mode == "revision-only":
        return
    if now.tzinfo is None:
        raise ConditionalEditError("invalid-request", "lease checks require a timezone-aware current time")

    lease = live_card.get("flowExecutionLease")
    actor = request.get("actor")
    if not isinstance(lease, dict) or not isinstance(actor, dict):
        raise ConditionalEditError("ownership-rejected", "lease mode requires the current actor identity")
    if now > _parse_timestamp(lease.get("expiresAt")):
        raise ConditionalEditError("ownership-rejected", "the Flow Card lease has expired")

    owner = lease.get("owner")
    expected_owner = {"agentId": owner} if isinstance(owner, str) else owner
    if not isinstance(expected_owner, dict) or not expected_owner:
        raise ConditionalEditError("ownership-rejected", "the Flow Card lease has no owner identity")
    for key in ("agentId", "threadId", "sessionId"):
        expected_value = expected_owner.get(key)
        if expected_value is not None and actor.get(key) != expected_value:
            raise ConditionalEditError("ownership-rejected", "the current actor does not own the Flow Card lease")


def prepare_conditional_edit(
    request: dict[str, Any],
    live_snapshot: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Validate one exact live snapshot and return the adapter precondition."""
    url, expected_revision, expected_hash, safety_mode, _ = _request_fields(request)
    target_card = _read_target_card(request)
    live_card = _read_live_card(request, live_snapshot)
    live_hash = canonical_card_hash(live_card)
    target_hash = canonical_card_hash(target_card)

    if live_card.get("statusRevision") == target_card.get("statusRevision") and live_hash == target_hash:
        return {
            "outcome": "already-applied",
            "skipEdit": True,
            "canonicalStatusCommentUrl": url,
            "safetyMode": safety_mode,
            "targetStatusRevision": target_card["statusRevision"],
            "targetCanonicalHash": target_hash,
            "registryMaySync": True,
        }
    if live_card.get("statusRevision") != expected_revision:
        raise ConditionalEditError("revision-drift", "canonical statusRevision changed before edit")
    if live_hash != expected_hash:
        raise ConditionalEditError("canonical-hash-drift", "canonical content changed before edit")
    if live_card.get("flowId") != target_card.get("flowId"):
        raise ConditionalEditError("target-invalid", "target Flow Card must preserve flowId")
    _verify_ownership(request, live_card, now)

    return {
        "outcome": "ready",
        "skipEdit": False,
        "canonicalStatusCommentUrl": url,
        "safetyMode": safety_mode,
        "expectedStatusRevision": expected_revision,
        "expectedCanonicalHash": expected_hash,
        "targetStatusRevision": target_card["statusRevision"],
        "targetCanonicalHash": target_hash,
        "registryMaySync": False,
    }


def verify_conditional_edit(
    request: dict[str, Any],
    saved_snapshot: dict[str, Any],
    *,
    outcome: str = "success",
) -> dict[str, Any]:
    """Verify the exact saved comment before allowing registry projection."""
    url, _, _, safety_mode, _ = _request_fields(request)
    target_card = _read_target_card(request)
    target_hash = canonical_card_hash(target_card)
    try:
        saved_card = _read_live_card(request, saved_snapshot)
    except ConditionalEditError as error:
        raise ConditionalEditError(
            "post-write-mismatch",
            "saved canonical comment could not be verified",
        ) from error
    if (
        saved_card.get("statusRevision") != target_card.get("statusRevision")
        or canonical_card_hash(saved_card) != target_hash
    ):
        raise ConditionalEditError(
            "post-write-mismatch",
            "saved canonical comment does not match the requested target",
        )
    return {
        "outcome": outcome,
        "canonicalStatusCommentUrl": url,
        "safetyMode": safety_mode,
        "targetStatusRevision": target_card["statusRevision"],
        "targetCanonicalHash": target_hash,
        "registryMaySync": True,
    }


def conditional_edit(
    request: dict[str, Any],
    adapter: CanonicalCommentAdapter,
    now: datetime,
) -> dict[str, Any]:
    """Run an in-place conditional edit through a carrier adapter and verify it."""
    url, _, _, safety_mode, target = _request_fields(request)
    if safety_mode == "atomic-cas" and not getattr(adapter, "supports_atomic_cas", False):
        raise ConditionalEditError(
            "adapter-capability-mismatch",
            "atomic-cas was requested but the carrier adapter does not provide native CAS",
        )
    try:
        live_snapshot = adapter.read_comment(url)
    except Exception as error:
        raise ConditionalEditError("read-failed", "canonical comment read failed") from error
    prepared = prepare_conditional_edit(request, live_snapshot, now)
    if prepared["skipEdit"]:
        return prepared

    precondition = {
        "safetyMode": safety_mode,
        "expectedStatusRevision": prepared["expectedStatusRevision"],
        "expectedCanonicalHash": prepared["expectedCanonicalHash"],
    }
    try:
        adapter.edit_comment(url, target["body"], precondition)
    except TimeoutError as error:
        raise ConditionalEditError(
            "edit-result-unknown",
            "carrier edit timed out; reread the exact comment before retrying",
        ) from error
    except Exception as error:
        raise ConditionalEditError("edit-failed", "carrier edit failed") from error

    try:
        saved_snapshot = adapter.read_comment(url)
    except Exception as error:
        raise ConditionalEditError(
            "post-write-mismatch",
            "saved canonical comment could not be reread",
        ) from error
    return verify_conditional_edit(request, saved_snapshot)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ConditionalEditError("invalid-request", "input JSON must be an object")
    return value


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare or verify a conditional canonical comment edit")
    parser.add_argument("phase", choices=("prepare", "verify"))
    parser.add_argument("request", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--now", help="ISO-8601 timestamp required for deterministic lease checks")
    args = parser.parse_args(argv[1:])
    try:
        request = _load(args.request)
        snapshot = _load(args.snapshot)
        if args.phase == "prepare":
            if not args.now:
                raise ConditionalEditError("invalid-request", "prepare requires --now")
            now = datetime.fromisoformat(args.now[:-1] + "+00:00" if args.now.endswith("Z") else args.now)
            result = prepare_conditional_edit(request, snapshot, now)
        else:
            result = verify_conditional_edit(request, snapshot)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (json.JSONDecodeError, ValueError, ConditionalEditError) as error:
        code = error.code if isinstance(error, ConditionalEditError) else "invalid-request"
        print(json.dumps({"error": str(error), "errorCode": code}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
