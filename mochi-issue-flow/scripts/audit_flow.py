#!/usr/bin/env python3
"""Audit a Mochi Issue Flow V3 Flow Card using supplied offline snapshots only."""

from __future__ import annotations

import argparse
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
    if not isinstance(current_repos, dict) or not isinstance(accepted_repos, dict):
        return False
    if set(current_repos) != set(accepted_repos):
        return False
    for repo in current_repos:
        current_artifact = current_repos[repo]
        accepted_artifact = accepted_repos[repo]
        if not isinstance(current_artifact, dict) or not isinstance(accepted_artifact, dict):
            return False
        if current_artifact.get("branch") != accepted_artifact.get("branch"):
            return False
        if current_artifact.get("sha") != accepted_artifact.get("sha"):
            return False
    return True


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
    values: list[Any] = []
    for bridge in bridges:
        if not isinstance(bridge, dict) or not bridge.get(required_key):
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


def audit_flow(card: dict[str, Any], now: datetime) -> list[dict[str, str]]:
    """Mutate only derived state/evidence and return stable offline findings."""
    findings: list[dict[str, str]] = []
    for error in validate_flow_card(card):
        findings.append({"code": "status-missing", "severity": "error", "bridgeId": ""})
        if error:
            break

    registry = card.get("registry")
    if not isinstance(registry, dict):
        registry = {}
    waiver = registry.get("waiver")
    waiver_approved = isinstance(waiver, dict) and waiver.get("approved") is True
    if registry.get("requiredForDone") and registry.get("status") != "synchronized" and not waiver_approved:
        findings.append({"code": "registry-deferred", "severity": "error", "bridgeId": ""})
    if registry.get("status") == "synchronized":
        synced_revision = registry.get("lastSyncedStatusRevision")
        current_revision = card.get("statusRevision")
        if isinstance(synced_revision, int) and synced_revision != current_revision:
            findings.append({"code": "registry-stale", "severity": "error", "bridgeId": ""})
        elif not isinstance(synced_revision, int):
            findings.append({"code": "registry-revision-unbound", "severity": "error", "bridgeId": ""})

    concurrency_control = card.get("concurrencyControl")
    concurrency_mode = (
        concurrency_control.get("mode", "lease")
        if isinstance(concurrency_control, dict)
        else "lease"
    )
    if concurrency_mode == "lease":
        lease = card.get("flowExecutionLease", {})
        expires_at = lease.get("expiresAt")
        if isinstance(expires_at, str):
            try:
                value = expires_at[:-1] + "+00:00" if expires_at.endswith("Z") else expires_at
                expired = now > datetime.fromisoformat(value)
            except (TypeError, ValueError):
                findings.append({"code": "lease-expiry-invalid", "severity": "error", "bridgeId": ""})
            else:
                if expired:
                    findings.append({"code": "lease-stalled", "severity": "error", "bridgeId": ""})

    bridges = card.get("bridges", [])
    for bridge in bridges:
        if not isinstance(bridge, dict):
            continue
        bridge_id = bridge.get("bridgeId", "")
        current = bridge.get("currentCommit") or {}
        accepted = bridge.get("acceptedCommit") or {}
        if not isinstance(current, dict) or not isinstance(accepted, dict):
            continue
        if not _same_commit_set(current, accepted):
            code_state = bridge.get("codeState")
            runtime_state = bridge.get("runtimeState")
            if not isinstance(code_state, dict) or not isinstance(runtime_state, dict):
                continue
            _invalidate_axis(code_state, accepted, current, bridge.get("codeRequired", False))
            _invalidate_axis(runtime_state, accepted, current, bridge.get("runtimeRequired", False))
            bridge["coordinationState"] = "needs-reverify"
            findings.append({"code": "commit-drift", "severity": "error", "bridgeId": bridge_id})
        runtime_state = bridge.get("runtimeState") or {}
        if (
            bridge.get("runtimeRequired")
            and isinstance(runtime_state, dict)
            and runtime_state.get("value") == "blocked"
        ):
            findings.append({"code": "runtime-blocker", "severity": "error", "bridgeId": bridge_id})

    card["flowCodeState"] = {"value": _derive_axis(bridges, "codeRequired", "codeState")}
    card["flowRuntimeState"] = {"value": _derive_axis(bridges, "runtimeRequired", "runtimeState")}
    return findings


def audit_flow_report(card: dict[str, Any], now: datetime, mode: str = "routine") -> dict[str, Any]:
    """Return an explicit audit report while preserving the legacy audit_flow API."""
    if mode not in {"routine", "closeout"}:
        raise ValueError(f"unsupported audit mode: {mode}")

    findings = audit_flow(card, now)
    if mode == "routine":
        return {
            "mode": mode,
            "findings": findings,
            "closeoutEligible": None,
            "closeoutReasons": [],
        }

    reasons: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_reason(code: str, bridge_id: str = "", axis: str = "", state: str = "") -> None:
        key = (code, bridge_id)
        if key in seen:
            return
        seen.add(key)
        reason = {"code": code, "bridgeId": bridge_id}
        if axis:
            reason["axis"] = axis
        if state:
            reason["state"] = state
        reasons.append(reason)

    registry = card.get("registry")
    waiver = registry.get("waiver") if isinstance(registry, dict) else None
    waiver_approved = isinstance(waiver, dict) and waiver.get("approved") is True
    registry_required = isinstance(registry, dict) and registry.get("requiredForDone") is True
    for finding in findings:
        if finding.get("severity") == "error":
            if (waiver_approved or not registry_required) and finding.get("code") in {
                "registry-deferred",
                "registry-revision-unbound",
                "registry-stale",
            }:
                continue
            add_reason(finding["code"], finding.get("bridgeId", ""))

    allowed_states = {"verified", "not-applicable"}
    for axis, field in (("code", "flowCodeState"), ("runtime", "flowRuntimeState")):
        state_object = card.get(field)
        state = state_object.get("value", "missing") if isinstance(state_object, dict) else "missing"
        if state not in allowed_states:
            add_reason(f"flow-{axis}-not-verified", axis=axis, state=state)

    return {
        "mode": mode,
        "findings": findings,
        "closeoutEligible": not reasons,
        "closeoutReasons": reasons,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit a Mochi Issue Flow V3 Flow Card")
    parser.add_argument("flow_card", type=Path)
    parser.add_argument("--mode", choices=("routine", "closeout"), default="routine")
    args = parser.parse_args(argv[1:])

    card = json.loads(args.flow_card.read_text(encoding="utf-8"))
    report = audit_flow_report(card, datetime.now().astimezone(), args.mode)
    print(json.dumps({**report, "card": card}, ensure_ascii=False, sort_keys=True))
    if args.mode == "closeout":
        return 0 if report["closeoutEligible"] else 2
    return 0 if not any(item["severity"] == "error" for item in report["findings"]) else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
