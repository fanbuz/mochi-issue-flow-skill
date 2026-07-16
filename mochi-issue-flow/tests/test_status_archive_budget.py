import copy
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from archive_flow_evidence import ArchiveError, apply_archive, archive_hash, prepare_archive
from audit_flow import audit_flow
from check_context_budget import measure_json, measure_route_bundle, measure_text
from flow_status import StatusReadError, build_summary, extract_flow_card, read_flow_card, summary_is_current
from validate_flow_card import validate_flow_card


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SKILL_DIR = Path(__file__).resolve().parents[1]


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def build_budget_card(spec: dict) -> dict:
    card = load_fixture("valid-flow-card.json")
    base_bridge = card["bridges"][0]
    bridges = []
    for bridge_index in range(spec["bridgeCount"]):
        bridge = copy.deepcopy(base_bridge)
        bridge["bridgeId"] = f"bridge-{bridge_index + 1}"
        bridge["currentCommit"]["artifactSetId"] = f"set-{bridge_index + 1}"
        bridge["acceptedCommit"]["artifactSetId"] = f"set-{bridge_index + 1}"
        bridge["runtimeState"]["blockers"] = [
            {
                "code": f"blocker-{blocker_index + 1}",
                "summary": "anonymous runtime condition awaiting verification",
            }
            for blocker_index in range(spec["blockersPerBridge"])
        ]
        for axis in ("codeState", "runtimeState"):
            bridge[axis]["supersededEvidence"] = [
                {
                    "commitSetId": f"old-{evidence_index + 1}",
                    "supersededBy": f"set-{bridge_index + 1}",
                    "reason": "artifact commit set changed",
                    "evidence": [
                        {"url": f"https://carrier.example/evidence/{bridge_index + 1}/{evidence_index + 1}"}
                    ],
                }
                for evidence_index in range(spec["supersededEvidencePerAxis"])
            ]
        bridges.append(bridge)
    card["bridges"] = bridges
    return card


class FlowStatusTest(unittest.TestCase):
    def test_flow_card_template_round_trips_through_parser_and_validator(self):
        body = (SKILL_DIR / "templates" / "flow-card-comment.md").read_text(encoding="utf-8")

        card = extract_flow_card(body)

        self.assertEqual([], validate_flow_card(card))

    def test_reads_normalized_canonical_comment_and_builds_summary(self):
        card = read_flow_card(load_fixture("normalized-status-read.json"))

        summary = build_summary(card)

        self.assertEqual("status-read-example", summary["flowId"])
        self.assertEqual(7, summary["sourceStatusRevision"])
        self.assertEqual("verified", summary["flowCodeState"])
        self.assertEqual("blocked", summary["flowRuntimeState"])
        self.assertEqual(["set-7"], summary["artifactSetIds"])
        self.assertEqual("runtime-owner", summary["nextActions"][0]["owner"])
        self.assertEqual("environment-unavailable", summary["blockers"][0]["detail"]["code"])
        self.assertTrue(summary_is_current(summary, card))

    def test_summary_is_stale_after_revision_or_content_change(self):
        card = load_fixture("valid-flow-card.json")
        summary = build_summary(card)
        changed = copy.deepcopy(card)
        changed["statusRevision"] += 1

        self.assertFalse(summary_is_current(summary, changed))

    def test_summary_generation_is_deterministic(self):
        card = load_fixture("valid-flow-card.json")

        self.assertEqual(build_summary(card), build_summary(copy.deepcopy(card)))

    def test_summary_projects_commit_drift_as_needs_reverify(self):
        card = load_fixture("drift-flow-card.json")

        summary = build_summary(card)

        self.assertEqual("needs-reverify", summary["flowCodeState"])
        self.assertEqual("needs-reverify", summary["flowRuntimeState"])
        self.assertIn(
            {
                "bridgeId": "example-bridge",
                "detail": {
                    "code": "commit-drift",
                    "summary": "current and accepted commit sets differ",
                },
            },
            summary["blockers"],
        )

    def test_rejects_transport_and_parsed_duplicates(self):
        payload = load_fixture("normalized-status-read.json")
        payload["raw"] = {"comments": []}
        payload["parsed"] = {"flowId": "duplicate"}

        with self.assertRaises(StatusReadError):
            read_flow_card(payload)

    def test_locally_filters_to_one_canonical_comment(self):
        normalized = load_fixture("normalized-status-read.json")
        canonical = normalized["canonicalComment"]
        snapshot = {
            "canonicalStatusCommentUrl": normalized["canonicalStatusCommentUrl"],
            "comments": [
                {"url": "https://carrier.example/issues/1#comment-1", "body": "historical note"},
                canonical,
                {"url": "https://carrier.example/issues/1#comment-3", "body": "unrelated evidence"},
            ],
        }

        card = read_flow_card(snapshot)

        self.assertEqual("status-read-example", card["flowId"])

    def test_rejects_multiple_flow_card_blocks_in_one_comment(self):
        body = load_fixture("normalized-status-read.json")["canonicalComment"]["body"]

        with self.assertRaises(StatusReadError) as context:
            extract_flow_card(body + "\n" + body)

        self.assertEqual("flow-card-ambiguous", context.exception.code)

    def test_accepts_attributed_start_and_end_sentinels(self):
        body = load_fixture("normalized-status-read.json")["canonicalComment"]["body"]
        body = body.replace(
            "<!-- flow-card:start v3 -->",
            "<!-- flow-card:start flowId=status-read-example protocol=3.0 -->",
        ).replace(
            "<!-- flow-card:end -->",
            "<!-- flow-card:end flowId=status-read-example -->",
        )

        card = extract_flow_card(body)

        self.assertEqual("status-read-example", card["flowId"])

    def test_ignores_unrelated_json_fences_outside_the_sentinel(self):
        body = load_fixture("normalized-status-read.json")["canonicalComment"]["body"]
        unrelated = '```json\n{"kind":"unrelated"}\n```'

        card = extract_flow_card(unrelated + "\n" + body + "\n" + unrelated)

        self.assertEqual("status-read-example", card["flowId"])

    def test_rejects_sentinel_flow_id_mismatch(self):
        body = load_fixture("normalized-status-read.json")["canonicalComment"]["body"]
        body = body.replace(
            "<!-- flow-card:start v3 -->",
            "<!-- flow-card:start flowId=other-flow protocol=3.0 -->",
        ).replace(
            "<!-- flow-card:end -->",
            "<!-- flow-card:end flowId=status-read-example -->",
        )

        with self.assertRaises(StatusReadError) as context:
            extract_flow_card(body)

        self.assertEqual("flow-card-flow-id-mismatch", context.exception.code)

    def test_rejects_unclosed_sentinel_with_stable_reason(self):
        body = load_fixture("normalized-status-read.json")["canonicalComment"]["body"]
        body = body.replace("<!-- flow-card:end -->", "")

        with self.assertRaises(StatusReadError) as context:
            extract_flow_card(body)

        self.assertEqual("flow-card-ambiguous", context.exception.code)

    def test_distinguishes_invalid_json_from_invalid_json_type(self):
        body = load_fixture("normalized-status-read.json")["canonicalComment"]["body"]
        payload = body.split("```json\n", 1)[1].split("\n```", 1)[0]

        with self.assertRaises(StatusReadError) as invalid_json:
            extract_flow_card(body.replace(payload, '{"broken":'))
        with self.assertRaises(StatusReadError) as invalid_type:
            extract_flow_card(body.replace(payload, '["not", "an", "object"]'))

        self.assertEqual("flow-card-invalid-json", invalid_json.exception.code)
        self.assertEqual("flow-card-invalid-type", invalid_type.exception.code)


class EvidenceArchiveTest(unittest.TestCase):
    def test_prepare_then_apply_preserves_original_and_adds_verified_ref(self):
        card = load_fixture("drift-flow-card.json")
        audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))

        prepared = prepare_archive(card, "example-bridge", "code", "2026-07-16T10:00:00Z")
        updated = apply_archive(
            card,
            prepared["archive"],
            "https://carrier.example/issues/1#comment-archive-1",
            prepared["contentHash"],
        )

        self.assertTrue(card["bridges"][0]["codeState"]["supersededEvidence"])
        self.assertEqual([], updated["bridges"][0]["codeState"]["supersededEvidence"])
        self.assertEqual(prepared["contentHash"], updated["bridges"][0]["codeState"]["archiveRefs"][0]["contentHash"])
        self.assertEqual(3, updated["statusRevision"])
        self.assertEqual("out-of-sync", updated["registry"]["status"])
        self.assertEqual([], validate_flow_card(updated))

    def test_apply_rejects_revision_drift_without_mutating_source(self):
        card = load_fixture("drift-flow-card.json")
        audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))
        prepared = prepare_archive(card, "example-bridge", "runtime", "2026-07-16T10:00:00Z")
        changed = copy.deepcopy(card)
        changed["statusRevision"] += 1

        with self.assertRaises(ArchiveError):
            apply_archive(
                changed,
                prepared["archive"],
                "https://carrier.example/archive",
                prepared["contentHash"],
            )
        self.assertTrue(changed["bridges"][0]["runtimeState"]["supersededEvidence"])

    def test_apply_rejects_tampered_archive_hash(self):
        card = load_fixture("drift-flow-card.json")
        audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))
        prepared = prepare_archive(card, "example-bridge", "code", "2026-07-16T10:00:00Z")
        tampered = copy.deepcopy(prepared["archive"])
        tampered["createdAt"] = "2026-07-16T11:00:00Z"

        with self.assertRaises(ArchiveError):
            apply_archive(
                card,
                tampered,
                "https://carrier.example/archive",
                prepared["contentHash"],
            )

    def test_apply_rejects_archive_from_another_flow(self):
        card = load_fixture("drift-flow-card.json")
        audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))
        prepared = prepare_archive(card, "example-bridge", "code", "2026-07-16T10:00:00Z")
        other_flow = copy.deepcopy(card)
        other_flow["flowId"] = "other-flow"

        with self.assertRaisesRegex(ArchiveError, "flowId"):
            apply_archive(
                other_flow,
                prepared["archive"],
                "https://carrier.example/archive",
                prepared["contentHash"],
            )

    def test_apply_rejects_internally_inconsistent_archive(self):
        card = load_fixture("drift-flow-card.json")
        audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))
        prepared = prepare_archive(card, "example-bridge", "runtime", "2026-07-16T10:00:00Z")
        malformed = copy.deepcopy(prepared["archive"])
        malformed["evidenceCount"] += 1

        with self.assertRaisesRegex(ArchiveError, "evidenceCount"):
            apply_archive(
                card,
                malformed,
                "https://carrier.example/archive",
                archive_hash(malformed),
            )


class ContextBudgetTest(unittest.TestCase):
    def test_core_summary_adapter_and_recovery_artifacts_are_budgeted(self):
        instruction = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        adapter = load_fixture("normalized-status-read.json")
        summary = build_summary(read_flow_card(adapter))
        recovery = {"coreInstructions": instruction, "statusSummary": summary}

        reports = {
            "instruction": measure_text(instruction),
            "summary": measure_json(summary, "summary"),
            "adapter": measure_json(adapter, "adapter"),
            "card": measure_json(load_fixture("valid-flow-card.json"), "card"),
            "recovery": measure_json(recovery, "recovery"),
        }

        self.assertTrue(all(report["status"] == "ok" for report in reports.values()))
        self.assertLessEqual(reports["summary"]["characterCount"], 12_000)
        self.assertLessEqual(reports["recovery"]["characterCount"], 40_000)

    def test_small_medium_and_large_scenarios_have_monotonic_cost(self):
        scenarios = load_fixture("context-budget-scenarios.json")
        reports = {
            name: measure_json(build_budget_card(spec), "card")
            for name, spec in scenarios.items()
        }

        self.assertLess(reports["small"]["characterCount"], reports["medium"]["characterCount"])
        self.assertLess(reports["medium"]["characterCount"], reports["large"]["characterCount"])
        self.assertEqual("ok", reports["small"]["status"])
        self.assertEqual("failed", reports["large"]["status"])

    def test_custom_thresholds_distinguish_warning_and_failure(self):
        value = {"payload": "x" * 60}

        warning = measure_json(value, "summary", warning_chars=40, hard_chars=100)
        failure = measure_json(value, "summary", warning_chars=20, hard_chars=40)

        self.assertEqual("warning", warning["status"])
        self.assertEqual("failed", failure["status"])

    def test_route_worksets_are_bounded_and_do_not_load_script_source(self):
        routes = load_fixture("route-worksets.json")
        adapter = load_fixture("normalized-status-read.json")
        dynamic_artifacts = {
            "summary": build_summary(read_flow_card(adapter)),
            "card": load_fixture("valid-flow-card.json"),
            "runtimeFailure": {
                "operation": "save monthly schedule",
                "result": "transaction failed",
                "nextAction": "inspect the local service exception",
            },
        }

        reports = {
            route: measure_route_bundle(SKILL_DIR, spec, dynamic_artifacts)
            for route, spec in routes.items()
        }

        self.assertTrue(all(report["status"] == "ok" for report in reports.values()))
        self.assertTrue(all(report["scriptSourceCount"] == 0 for report in reports.values()))
        self.assertEqual(
            ["SKILL.md", "references/status-read-adapter.md"],
            reports["read-only-status"]["artifactPaths"],
        )
        self.assertNotIn("card", reports["read-only-status"]["dynamicArtifactNames"])
        self.assertIn("card", reports["conditional-mutation"]["dynamicArtifactNames"])

    def test_route_workset_rejects_normal_script_source_loading(self):
        spec = {
            "artifacts": ["SKILL.md", "scripts/flow_status.py"],
            "dynamicArtifacts": ["summary"],
        }

        with self.assertRaisesRegex(ValueError, "script source"):
            measure_route_bundle(SKILL_DIR, spec, {"summary": {"flowId": "example"}})

    def test_alias_template_is_not_a_second_flow_card(self):
        text = (SKILL_DIR / "templates" / "flow-card-alias.md").read_text(encoding="utf-8")

        self.assertIn("Canonical status", text)
        self.assertNotIn("flow-card:start", text)

    def test_public_fixtures_do_not_contain_private_paths_or_credentials(self):
        fixture_text = "\n".join(
            path.read_text(encoding="utf-8") for path in FIXTURE_DIR.glob("*.json")
        )

        self.assertNotIn("/Users/", fixture_text)
        self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", fixture_text)
        self.assertNotRegex(fixture_text, r"gh[pousr]_[A-Za-z0-9]{20,}")


if __name__ == "__main__":
    unittest.main()
