#!/usr/bin/env python3
"""Validate a carrier-neutral Mochi Issue Flow V3 Flow Card."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CODE_STATES = {
    "not-started",
    "evidence-pending",
    "verified",
    "needs-reverify",
    "failed",
    "not-applicable",
}
RUNTIME_STATES = CODE_STATES | {"blocked", "verifying"}
CONCURRENCY_MODES = {"lease", "revision-only"}
REGISTRY_STATUSES = {"synchronized", "out-of-sync", "pending-user-approval", "not-configured"}
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def _commit_set_errors(bridge_id: str, set_name: str, value: Any, required_repos: list[str]) -> list[str]:
    if not isinstance(value, dict):
        return [f"bridge {bridge_id} {set_name} is required"]
    repos = value.get("repos")
    if not isinstance(repos, dict):
        return [f"bridge {bridge_id} {set_name} repos is required"]
    errors: list[str] = []
    extra_repos = set(repos) - set(required_repos)
    if extra_repos:
        errors.append(
            f"bridge {bridge_id} {set_name} has unexpected repos: {', '.join(sorted(extra_repos))}"
        )
    for repo in required_repos:
        artifact = repos.get(repo)
        if not isinstance(artifact, dict):
            errors.append(f"bridge {bridge_id} {set_name} misses {repo}")
            continue
        if not artifact.get("branch") or not artifact.get("sha"):
            errors.append(f"bridge {bridge_id} {set_name} artifact {repo} needs branch and sha")
    return errors


def _state_errors(bridge_id: str, axis: str, required: bool, state: Any, allowed: set[str]) -> list[str]:
    if not isinstance(state, dict):
        return [f"bridge {bridge_id} {axis}State is required"]
    value = state.get("value")
    if value not in allowed:
        return [f"bridge {bridge_id} {axis}State has invalid value {value!r}"]
    if not required and value != "not-applicable":
        return [f"bridge {bridge_id} {axis}State must be not-applicable when {axis}Required is false"]
    if not required and not state.get("notApplicableReason"):
        return [f"bridge {bridge_id} {axis}State needs notApplicableReason"]
    errors: list[str] = []
    for field in ("activeEvidence", "supersededEvidence"):
        if field in state and not isinstance(state[field], list):
            errors.append(f"bridge {bridge_id} {axis}State {field} must be a list")
    archive_refs = state.get("archiveRefs", [])
    if not isinstance(archive_refs, list):
        errors.append(f"bridge {bridge_id} {axis}State archiveRefs must be a list")
    else:
        for index, ref in enumerate(archive_refs):
            if not isinstance(ref, dict):
                errors.append(f"bridge {bridge_id} {axis}State archiveRefs[{index}] must be an object")
                continue
            required_fields = ("url", "contentHash", "artifactSetIds", "evidenceCount", "createdAt")
            if any(field not in ref for field in required_fields):
                errors.append(f"bridge {bridge_id} {axis}State archiveRefs[{index}] is incomplete")
            if not isinstance(ref.get("url"), str) or not ref.get("url"):
                errors.append(f"bridge {bridge_id} {axis}State archiveRefs[{index}] url is invalid")
            if not isinstance(ref.get("contentHash"), str) or not SHA256_PATTERN.match(ref["contentHash"]):
                errors.append(f"bridge {bridge_id} {axis}State archiveRefs[{index}] contentHash is invalid")
            if not isinstance(ref.get("artifactSetIds"), list):
                errors.append(
                    f"bridge {bridge_id} {axis}State archiveRefs[{index}] artifactSetIds must be a list"
                )
            elif not all(isinstance(item, str) and item for item in ref["artifactSetIds"]):
                errors.append(
                    f"bridge {bridge_id} {axis}State archiveRefs[{index}] artifactSetIds are invalid"
                )
            if type(ref.get("evidenceCount")) is not int or ref.get("evidenceCount", -1) < 0:
                errors.append(f"bridge {bridge_id} {axis}State archiveRefs[{index}] evidenceCount is invalid")
            if not isinstance(ref.get("createdAt"), str) or not ref.get("createdAt"):
                errors.append(f"bridge {bridge_id} {axis}State archiveRefs[{index}] createdAt is invalid")
    return errors


def _concurrency_errors(card: dict[str, Any]) -> list[str]:
    control = card.get("concurrencyControl")
    mode = "lease"
    if control is not None:
        if not isinstance(control, dict) or control.get("mode") not in CONCURRENCY_MODES:
            return ["concurrencyControl.mode must be lease or revision-only"]
        mode = control["mode"]

    lease = card.get("flowExecutionLease")
    if mode == "lease":
        if not isinstance(lease, dict):
            return ["flowExecutionLease is required when concurrencyControl.mode is lease"]
        if not isinstance(lease.get("expiresAt"), str):
            return ["flowExecutionLease.expiresAt is required"]
        try:
            value = lease["expiresAt"]
            expires_at = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        except ValueError:
            return ["flowExecutionLease.expiresAt must be an ISO-8601 timestamp"]
        if expires_at.tzinfo is None:
            return ["flowExecutionLease.expiresAt must include a timezone"]
    elif lease is not None:
        return ["flowExecutionLease must be absent when concurrencyControl.mode is revision-only"]
    return []


def _dag_errors(card: dict[str, Any], bridge_ids: set[str]) -> list[str]:
    graph: dict[str, list[str]] = {bridge_id: [] for bridge_id in bridge_ids}
    errors: list[str] = []
    dependencies = card.get("dependencies", [])
    if not isinstance(dependencies, list):
        return ["dependencies must be a list"]
    for edge in dependencies:
        if not isinstance(edge, dict):
            errors.append("dependency must be an object")
            continue
        source, target = edge.get("from"), edge.get("to")
        if source not in bridge_ids or target not in bridge_ids:
            errors.append(f"dependency {source!r}->{target!r} references an unknown bridge")
            continue
        graph[source].append(target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append("dependency graph contains a cycle")
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for bridge_id in graph:
        visit(bridge_id)
    return errors


def validate_flow_card(card: dict[str, Any]) -> list[str]:
    """Return deterministic validation messages; an empty list means valid."""
    errors: list[str] = []
    if not isinstance(card.get("protocolVersion"), str):
        errors.append("protocolVersion is required")
    if not card.get("flowId"):
        errors.append("flowId is required")
    if type(card.get("statusRevision")) is not int:
        errors.append("statusRevision is required")
    canonical_url = card.get("canonicalStatusCommentUrl")
    if canonical_url is not None and not isinstance(canonical_url, str):
        errors.append("canonicalStatusCommentUrl must be a string or null")

    registry = card.get("registry")
    if not isinstance(registry, dict) or not isinstance(registry.get("requiredForDone"), bool):
        errors.append("registry.requiredForDone is required")
    else:
        if registry.get("status") not in REGISTRY_STATUSES:
            errors.append("registry.status is invalid")
        if "lastSyncedStatusRevision" in registry and type(registry["lastSyncedStatusRevision"]) is not int:
            errors.append("registry.lastSyncedStatusRevision must be an integer")
        waiver = registry.get("waiver")
        if waiver is not None:
            if not isinstance(waiver, dict):
                errors.append("registry.waiver must be an object or null")
            elif "approved" in waiver and not isinstance(waiver["approved"], bool):
                errors.append("registry.waiver.approved must be a boolean")

    errors.extend(_concurrency_errors(card))

    bridges = card.get("bridges")
    if not isinstance(bridges, list) or not bridges:
        return errors + ["bridges is required"]

    bridge_ids: set[str] = set()
    for bridge in bridges:
        if not isinstance(bridge, dict):
            errors.append("bridge must be an object")
            continue
        bridge_id = bridge.get("bridgeId")
        if not isinstance(bridge_id, str) or not bridge_id:
            errors.append("bridgeId is required")
            continue
        if bridge_id in bridge_ids:
            errors.append(f"duplicate bridgeId {bridge_id}")
        bridge_ids.add(bridge_id)

        required_repos = bridge.get("relevantArtifactRepos")
        if not isinstance(required_repos, list) or not all(isinstance(repo, str) and repo for repo in required_repos):
            errors.append(f"bridge {bridge_id} relevantArtifactRepos is required")
            continue
        if len(required_repos) != len(set(required_repos)):
            errors.append(f"bridge {bridge_id} relevantArtifactRepos contains duplicates")
        errors.extend(_commit_set_errors(bridge_id, "currentCommit", bridge.get("currentCommit"), required_repos))
        errors.extend(_commit_set_errors(bridge_id, "acceptedCommit", bridge.get("acceptedCommit"), required_repos))

        code_required = bridge.get("codeRequired")
        runtime_required = bridge.get("runtimeRequired")
        if not isinstance(code_required, bool):
            errors.append(f"bridge {bridge_id} codeRequired is required")
        if not isinstance(runtime_required, bool):
            errors.append(f"bridge {bridge_id} runtimeRequired is required")
        if isinstance(code_required, bool):
            errors.extend(_state_errors(bridge_id, "code", code_required, bridge.get("codeState"), CODE_STATES))
        if isinstance(runtime_required, bool):
            errors.extend(
                _state_errors(
                    bridge_id,
                    "runtime",
                    runtime_required,
                    bridge.get("runtimeState"),
                    RUNTIME_STATES,
                )
            )
        for field in ("nextOwner", "nextAction"):
            if field in bridge and not isinstance(bridge[field], str):
                errors.append(f"bridge {bridge_id} {field} must be a string")

    errors.extend(_dag_errors(card, bridge_ids))
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_flow_card.py FLOW_CARD.json", file=sys.stderr)
        return 64
    card = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    errors = validate_flow_card(card)
    print(json.dumps({"errors": errors}, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
