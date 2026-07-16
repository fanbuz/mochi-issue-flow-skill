#!/usr/bin/env python3
"""Extract one canonical Flow Card and emit a compact, revision-bound summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_flow_card import validate_flow_card


FLOW_CARD_PATTERN = re.compile(
    r"<!--\s*flow-card:start[^>]*-->\s*```json\s*(\{.*?\})\s*```\s*<!--\s*flow-card:end\s*-->",
    re.DOTALL,
)
DISALLOWED_ADAPTER_KEYS = {"raw", "parsed", "content", "structuredContent"}


class StatusReadError(ValueError):
    """Raised when an adapter snapshot cannot identify one canonical card."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_card_hash(card: dict[str, Any]) -> str:
    payload = canonical_json(card).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def extract_flow_card(comment_body: str) -> dict[str, Any]:
    matches = FLOW_CARD_PATTERN.findall(comment_body)
    if len(matches) != 1:
        raise StatusReadError("canonical comment does not contain one Flow Card sentinel block")
    try:
        card = json.loads(matches[0])
    except json.JSONDecodeError as error:
        raise StatusReadError(f"canonical Flow Card JSON is invalid: {error.msg}") from error
    if not isinstance(card, dict):
        raise StatusReadError("canonical Flow Card must be a JSON object")
    return card


def select_canonical_comment(snapshot: dict[str, Any]) -> dict[str, Any]:
    duplicate_keys = sorted(DISALLOWED_ADAPTER_KEYS.intersection(snapshot))
    if duplicate_keys:
        raise StatusReadError(
            "adapter payload is not normalized; remove transport/raw fields: " + ", ".join(duplicate_keys)
        )

    canonical_url = snapshot.get("canonicalStatusCommentUrl")
    if not isinstance(canonical_url, str) or not canonical_url:
        raise StatusReadError("canonicalStatusCommentUrl is required")

    direct = snapshot.get("canonicalComment")
    if isinstance(direct, dict):
        if direct.get("url") != canonical_url:
            raise StatusReadError("canonicalComment URL does not match canonicalStatusCommentUrl")
        if not isinstance(direct.get("body"), str):
            raise StatusReadError("canonicalComment.body is required")
        return direct

    comments = snapshot.get("comments")
    if not isinstance(comments, list):
        raise StatusReadError("adapter payload must include canonicalComment or a locally filterable comments list")
    matches = [comment for comment in comments if isinstance(comment, dict) and comment.get("url") == canonical_url]
    if len(matches) != 1 or not isinstance(matches[0].get("body"), str):
        raise StatusReadError("comments list must contain exactly one canonical comment")
    return matches[0]


def read_flow_card(source: dict[str, Any]) -> dict[str, Any]:
    duplicate_keys = sorted(DISALLOWED_ADAPTER_KEYS.intersection(source))
    if duplicate_keys:
        raise StatusReadError(
            "source is not normalized; remove transport/raw fields: " + ", ".join(duplicate_keys)
        )
    card = source if isinstance(source.get("bridges"), list) else extract_flow_card(
        select_canonical_comment(source)["body"]
    )
    validation_errors = validate_flow_card(card)
    if validation_errors:
        raise StatusReadError("canonical Flow Card is invalid: " + "; ".join(validation_errors))
    return card


def _same_commit_set(current: Any, accepted: Any) -> bool:
    if not isinstance(current, dict) or not isinstance(accepted, dict):
        return False
    current_repos = current.get("repos")
    accepted_repos = accepted.get("repos")
    if not isinstance(current_repos, dict) or not isinstance(accepted_repos, dict):
        return False
    if set(current_repos) != set(accepted_repos):
        return False
    return all(
        isinstance(current_repos[repo], dict)
        and isinstance(accepted_repos[repo], dict)
        and current_repos[repo].get("branch") == accepted_repos[repo].get("branch")
        and current_repos[repo].get("sha") == accepted_repos[repo].get("sha")
        for repo in current_repos
    )


def _derive_axis(bridges: list[dict[str, Any]], required_key: str, state_key: str) -> str:
    values: list[Any] = []
    for bridge in bridges:
        if not isinstance(bridge, dict) or not bridge.get(required_key):
            continue
        if not _same_commit_set(bridge.get("currentCommit"), bridge.get("acceptedCommit")):
            values.append("needs-reverify")
            continue
        state = bridge.get(state_key)
        values.append(state.get("value") if isinstance(state, dict) else None)
    if not values:
        return "not-applicable"
    if "failed" in values:
        return "failed"
    if "needs-reverify" in values:
        return "needs-reverify"
    if state_key == "runtimeState" and "blocked" in values:
        return "blocked"
    if all(value == "verified" for value in values):
        return "verified"
    return "pending"


def _compact_blocker(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        compact = {
            key: value[key]
            for key in ("code", "summary", "owner", "nextAction")
            if key in value
        }
        return compact or "unspecified blocker"
    return str(value)


def build_summary(card: dict[str, Any]) -> dict[str, Any]:
    bridges = [bridge for bridge in card.get("bridges", []) if isinstance(bridge, dict)]
    blockers: list[dict[str, Any]] = []
    next_actions: list[dict[str, str]] = []
    artifact_set_ids: list[str] = []

    for bridge in bridges:
        bridge_id = str(bridge.get("bridgeId", ""))
        current_commit = bridge.get("currentCommit")
        commit_drift = not _same_commit_set(current_commit, bridge.get("acceptedCommit"))
        current_set_id = current_commit.get("artifactSetId") if isinstance(current_commit, dict) else None
        if isinstance(current_set_id, str) and current_set_id not in artifact_set_ids:
            artifact_set_ids.append(current_set_id)

        bridge_blockers: list[Any] = []
        code_state = bridge.get("codeState")
        runtime_state = bridge.get("runtimeState")
        for candidate in (
            bridge.get("blockers", []),
            code_state.get("blockers", []) if isinstance(code_state, dict) else [],
            runtime_state.get("blockers", []) if isinstance(runtime_state, dict) else [],
        ):
            if isinstance(candidate, list):
                bridge_blockers.extend(candidate)
        blockers.extend(
            {"bridgeId": bridge_id, "detail": _compact_blocker(blocker)}
            for blocker in bridge_blockers
        )
        if commit_drift:
            blockers.append(
                {
                    "bridgeId": bridge_id,
                    "detail": {
                        "code": "commit-drift",
                        "summary": "current and accepted commit sets differ",
                    },
                }
            )

        owner = bridge.get("nextOwner")
        action = bridge.get("nextAction")
        if isinstance(owner, str) or isinstance(action, str):
            next_actions.append(
                {
                    "bridgeId": bridge_id,
                    "owner": owner if isinstance(owner, str) else "",
                    "action": action if isinstance(action, str) else "",
                }
            )

    return {
        "summaryVersion": "1",
        "flowId": card.get("flowId"),
        "sourceStatusRevision": card.get("statusRevision"),
        "sourceCanonicalHash": canonical_card_hash(card),
        "flowCodeState": _derive_axis(bridges, "codeRequired", "codeState"),
        "flowRuntimeState": _derive_axis(bridges, "runtimeRequired", "runtimeState"),
        "artifactSetIds": artifact_set_ids,
        "blockers": blockers,
        "nextActions": next_actions,
    }


def summary_is_current(summary: dict[str, Any], card: dict[str, Any]) -> bool:
    return (
        summary.get("sourceStatusRevision") == card.get("statusRevision")
        and summary.get("sourceCanonicalHash") == canonical_card_hash(card)
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a compact summary from a Flow Card or adapter snapshot")
    parser.add_argument("source", type=Path)
    args = parser.parse_args(argv[1:])

    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        card = read_flow_card(source)
        print(json.dumps({"summary": build_summary(card)}, ensure_ascii=False, sort_keys=True))
        return 0
    except (json.JSONDecodeError, StatusReadError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
