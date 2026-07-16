#!/usr/bin/env python3
"""Measure Flow artifacts with deterministic character budgets."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from flow_status import canonical_json


DEFAULT_BUDGETS = {
    "instruction": {"warning": 12_000, "hard": 24_000},
    "summary": {"warning": 4_000, "hard": 12_000},
    "adapter": {"warning": 12_000, "hard": 24_000},
    "card": {"warning": 12_000, "hard": 24_000},
    "recovery": {"warning": 32_000, "hard": 40_000},
    "route-bundle": {"warning": 16_000, "hard": 24_000},
}


def _count_o200k_tokens(text: str) -> tuple[int | None, str | None]:
    try:
        import tiktoken  # type: ignore[import-not-found]
    except ImportError:
        return None, None
    try:
        package_version = version("tiktoken")
    except PackageNotFoundError:
        package_version = "unknown"
    return len(tiktoken.get_encoding("o200k_base").encode(text)), package_version


def _measure_normalized(
    normalized: str,
    kind: str,
    warning_chars: int | None = None,
    hard_chars: int | None = None,
) -> dict[str, Any]:
    if kind not in DEFAULT_BUDGETS:
        raise ValueError(f"unsupported budget kind: {kind}")
    warning = warning_chars if warning_chars is not None else DEFAULT_BUDGETS[kind]["warning"]
    hard = hard_chars if hard_chars is not None else DEFAULT_BUDGETS[kind]["hard"]
    if warning <= 0 or hard <= warning:
        raise ValueError("hard character budget must be greater than the positive warning budget")

    character_count = len(normalized)
    status = "failed" if character_count > hard else "warning" if character_count > warning else "ok"
    token_count, tokenizer_package_version = _count_o200k_tokens(normalized)
    return {
        "kind": kind,
        "status": status,
        "characterCount": character_count,
        "utf8ByteCount": len(normalized.encode("utf-8")),
        "warningCharacterLimit": warning,
        "hardCharacterLimit": hard,
        "tokenizer": "o200k_base",
        "tokenizerPackageVersion": tokenizer_package_version,
        "tokenCount": token_count,
        "tokenCountAvailable": token_count is not None,
    }


def measure_json(
    value: Any,
    kind: str,
    warning_chars: int | None = None,
    hard_chars: int | None = None,
) -> dict[str, Any]:
    return _measure_normalized(canonical_json(value), kind, warning_chars, hard_chars)


def measure_text(
    value: str,
    kind: str = "instruction",
    warning_chars: int | None = None,
    hard_chars: int | None = None,
) -> dict[str, Any]:
    if not isinstance(value, str):
        raise ValueError("text budget input must be a string")
    return _measure_normalized(value, kind, warning_chars, hard_chars)


def measure_route_bundle(
    skill_dir: Path,
    spec: dict[str, Any],
    dynamic_artifacts: dict[str, Any],
) -> dict[str, Any]:
    """Measure one route's actual instruction/reference/dynamic working set."""
    artifact_paths = spec.get("artifacts")
    dynamic_names = spec.get("dynamicArtifacts", [])
    if not isinstance(artifact_paths, list) or not artifact_paths:
        raise ValueError("route bundle artifacts must be a non-empty list")
    if not all(isinstance(path, str) and path for path in artifact_paths):
        raise ValueError("route bundle artifact paths must be strings")
    if len(artifact_paths) != len(set(artifact_paths)):
        raise ValueError("route bundle artifact paths must be unique")
    if not isinstance(dynamic_names, list) or not all(
        isinstance(name, str) and name for name in dynamic_names
    ):
        raise ValueError("route bundle dynamicArtifacts must be a list of names")
    if len(dynamic_names) != len(set(dynamic_names)):
        raise ValueError("route bundle dynamicArtifacts must be unique")

    root = skill_dir.resolve()
    text_parts: list[str] = []
    script_source_count = 0
    reference_count = 0
    for relative in artifact_paths:
        path = (root / relative).resolve()
        if path != root and root not in path.parents:
            raise ValueError(f"route bundle path escapes the skill directory: {relative}")
        if not path.is_file():
            raise ValueError(f"route bundle artifact does not exist: {relative}")
        relative_parts = Path(relative).parts
        if "scripts" in relative_parts and path.suffix == ".py":
            script_source_count += 1
        if "references" in relative_parts:
            reference_count += 1
        text_parts.append(f"## {relative}\n{path.read_text(encoding='utf-8').strip()}")

    if script_source_count and not spec.get("debugReason"):
        raise ValueError("normal route bundle must not load script source")

    missing = [name for name in dynamic_names if name not in dynamic_artifacts]
    if missing:
        raise ValueError("route bundle misses dynamic artifacts: " + ", ".join(missing))
    for name in dynamic_names:
        value = dynamic_artifacts[name]
        normalized = value if isinstance(value, str) else canonical_json(value)
        text_parts.append(f"## dynamic:{name}\n{normalized}")

    report = _measure_normalized(
        "\n\n".join(text_parts),
        "route-bundle",
        spec.get("warningCharacters"),
        spec.get("hardCharacters"),
    )
    report.update(
        {
            "artifactPaths": artifact_paths,
            "dynamicArtifactNames": dynamic_names,
            "referenceCount": reference_count,
            "scriptSourceCount": script_source_count,
            "debugReason": spec.get("debugReason"),
        }
    )
    return report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check a normalized JSON artifact against its context budget")
    parser.add_argument("source", type=Path)
    parser.add_argument("--kind", choices=tuple(DEFAULT_BUDGETS), required=True)
    parser.add_argument("--warning-chars", type=int)
    parser.add_argument("--hard-chars", type=int)
    parser.add_argument("--skill-dir", type=Path)
    args = parser.parse_args(argv[1:])

    try:
        source_text = args.source.read_text(encoding="utf-8")
        if args.kind == "instruction":
            report = measure_text(source_text, args.kind, args.warning_chars, args.hard_chars)
        elif args.kind == "route-bundle":
            if args.skill_dir is None:
                raise ValueError("route-bundle requires --skill-dir")
            spec = json.loads(source_text)
            if not isinstance(spec, dict):
                raise ValueError("route-bundle source must be an object")
            inline_artifacts = spec.pop("inlineArtifacts", {})
            if not isinstance(inline_artifacts, dict):
                raise ValueError("route-bundle inlineArtifacts must be an object")
            if args.warning_chars is not None:
                spec["warningCharacters"] = args.warning_chars
            if args.hard_chars is not None:
                spec["hardCharacters"] = args.hard_chars
            report = measure_route_bundle(args.skill_dir, spec, inline_artifacts)
        else:
            report = measure_json(json.loads(source_text), args.kind, args.warning_chars, args.hard_chars)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2 if report["status"] == "failed" else 0
    except (json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
