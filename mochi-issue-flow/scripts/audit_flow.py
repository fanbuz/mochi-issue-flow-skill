#!/usr/bin/env python3
"""Audit a Mochi Issue Flow V3 Flow Card using supplied offline snapshots only."""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from validate_flow_card import validate_flow_card


def _same_commit_set(current: dict[str, Any], accepted: dict[str, Any]) -> bool:
    current_repos = current.get("repos", {})
    accepted_repos = accepted.get("repos", {})
    if set(current_repos) != set(accepted_repos):
        return False
    return all(
        current_repos[repo].get("branch") == accepted_repos[repo].get("branch")
        and current_repos[repo].get("sha") == accepted_repos[repo].get("sha")
        for repo in current_repos
    )


def _invalidate_axis(
    state: dict[str, Any],
    accepted_set: dict[str, Any],
    current_set: dict[str, Any],
    required: bool,
) -> None:
    if not required:
        return
    active = state.get("activeEvidence", [])
    if active:
        state.setdefault("supersededEvidence", []).append(
            {
                "commitSetId": accepted_set.get("artifactSetId"),
                "evidence": copy.deepcopy(active),
                "supersededBy": current_set.get("artifactSetId"),
                "reason": "artifact commit set changed",
            }
        )
        state["activeEvidence"] = []
    state["value"] = "needs-reverify"


def _derive_axis(bridges: list[dict[str, Any]], required_key: str, state_key: str) -> str:
    values = [bridge[state_key].get("value") for bridge in bridges if bridge.get(required_key)]
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


def audit_flow(card: dict[str, Any], now: datetime) -> list[dict[str, str]]:
    """Mutate only derived state/evidence and return stable offline findings."""
    findings: list[dict[str, str]] = []
    for error in validate_flow_card(card):
        findings.append({"code": "status-missing", "severity": "error", "bridgeId": ""})
        if error:
            break

    registry = card.get("registry", {})
    waiver = registry.get("waiver") or {}
    if registry.get("requiredForDone") and registry.get("status") != "synchronized" and not waiver.get("approved"):
        findings.append({"code": "registry-deferred", "severity": "error", "bridgeId": ""})

    lease = card.get("flowExecutionLease", {})
    expires_at = lease.get("expiresAt")
    if isinstance(expires_at, str) and now > datetime.fromisoformat(expires_at):
        findings.append({"code": "lease-stalled", "severity": "error", "bridgeId": ""})

    bridges = card.get("bridges", [])
    for bridge in bridges:
        bridge_id = bridge.get("bridgeId", "")
        current = bridge.get("currentCommit", {})
        accepted = bridge.get("acceptedCommit", {})
        if not _same_commit_set(current, accepted):
            _invalidate_axis(bridge["codeState"], accepted, current, bridge.get("codeRequired", False))
            _invalidate_axis(bridge["runtimeState"], accepted, current, bridge.get("runtimeRequired", False))
            bridge["coordinationState"] = "needs-reverify"
            findings.append({"code": "commit-drift", "severity": "error", "bridgeId": bridge_id})
        if bridge.get("runtimeRequired") and bridge["runtimeState"].get("value") == "blocked":
            findings.append({"code": "runtime-blocker", "severity": "error", "bridgeId": bridge_id})

    card["flowCodeState"] = {"value": _derive_axis(bridges, "codeRequired", "codeState")}
    card["flowRuntimeState"] = {"value": _derive_axis(bridges, "runtimeRequired", "runtimeState")}
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: audit_flow.py FLOW_CARD.json", file=sys.stderr)
        return 64
    card = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    findings = audit_flow(card, datetime.now().astimezone())
    print(json.dumps({"findings": findings, "card": card}, ensure_ascii=False, sort_keys=True))
    return 0 if not any(item["severity"] == "error" for item in findings) else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
