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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check a normalized JSON artifact against its context budget")
    parser.add_argument("source", type=Path)
    parser.add_argument("--kind", choices=tuple(DEFAULT_BUDGETS), required=True)
    parser.add_argument("--warning-chars", type=int)
    parser.add_argument("--hard-chars", type=int)
    args = parser.parse_args(argv[1:])

    try:
        source_text = args.source.read_text(encoding="utf-8")
        report = (
            measure_text(source_text, args.kind, args.warning_chars, args.hard_chars)
            if args.kind == "instruction"
            else measure_json(json.loads(source_text), args.kind, args.warning_chars, args.hard_chars)
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2 if report["status"] == "failed" else 0
    except (json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
