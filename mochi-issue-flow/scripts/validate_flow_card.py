#!/usr/bin/env python3
"""Validate a carrier-neutral Mochi Issue Flow V3 Flow Card."""

from __future__ import annotations

import json
import sys
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


def _commit_set_errors(bridge_id: str, set_name: str, value: Any, required_repos: list[str]) -> list[str]:
    if not isinstance(value, dict):
        return [f"bridge {bridge_id} {set_name} is required"]
    repos = value.get("repos")
    if not isinstance(repos, dict):
        return [f"bridge {bridge_id} {set_name} repos is required"]
    errors: list[str] = []
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
    return []


def _dag_errors(card: dict[str, Any], bridge_ids: set[str]) -> list[str]:
    graph: dict[str, list[str]] = {bridge_id: [] for bridge_id in bridge_ids}
    errors: list[str] = []
    for edge in card.get("dependencies", []):
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
    if not isinstance(card.get("statusRevision"), int):
        errors.append("statusRevision is required")

    registry = card.get("registry")
    if not isinstance(registry, dict) or not isinstance(registry.get("requiredForDone"), bool):
        errors.append("registry.requiredForDone is required")

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
            errors.extend(_state_errors(bridge_id, "runtime", runtime_required, bridge.get("runtimeState"), RUNTIME_STATES))

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
