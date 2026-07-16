import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from audit_flow import audit_flow, audit_flow_report
from validate_flow_card import validate_flow_card


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parent
RELEASE_ROOT = REPO_ROOT if all(
    (REPO_ROOT / name).is_file()
    for name in ("README.md", "README.en.md", "LICENSE", "VERSION", ".gitignore")
) else None


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class FlowCardValidationTest(unittest.TestCase):
    def test_rejects_missing_status_revision(self):
        card = load_fixture("valid-flow-card.json")
        del card["statusRevision"]

        self.assertIn("statusRevision is required", validate_flow_card(card))

    def test_rejects_incomplete_artifact_set(self):
        card = load_fixture("valid-flow-card.json")
        del card["bridges"][0]["currentCommit"]["repos"]["driver-repo"]

        self.assertIn(
            "bridge example-bridge currentCommit misses driver-repo",
            validate_flow_card(card),
        )

    def test_accepts_a_valid_flow_card(self):
        self.assertEqual([], validate_flow_card(load_fixture("valid-flow-card.json")))

    def test_rejects_unexpected_artifact_repository(self):
        card = load_fixture("valid-flow-card.json")
        card["bridges"][0]["currentCommit"]["repos"]["extra-repo"] = {
            "branch": "main",
            "sha": "3333333",
        }

        self.assertIn(
            "bridge example-bridge currentCommit has unexpected repos: extra-repo",
            validate_flow_card(card),
        )

    def test_revision_only_mode_requires_no_lease(self):
        card = load_fixture("valid-flow-card.json")
        card["concurrencyControl"] = {"mode": "revision-only"}
        del card["flowExecutionLease"]

        self.assertEqual([], validate_flow_card(card))

    def test_lease_mode_requires_a_lease(self):
        card = load_fixture("valid-flow-card.json")
        del card["flowExecutionLease"]

        self.assertIn(
            "flowExecutionLease is required when concurrencyControl.mode is lease",
            validate_flow_card(card),
        )

    def test_legacy_v3_without_concurrency_control_defaults_to_lease(self):
        card = load_fixture("valid-flow-card.json")
        del card["concurrencyControl"]

        self.assertEqual([], validate_flow_card(card))

    def test_rejects_invalid_registry_waiver_shape(self):
        card = load_fixture("valid-flow-card.json")
        card["registry"]["waiver"] = "approved"

        self.assertIn("registry.waiver must be an object or null", validate_flow_card(card))


class FlowAuditTest(unittest.TestCase):
    def test_reports_commit_drift_and_preserves_superseded_evidence(self):
        card = load_fixture("drift-flow-card.json")

        findings = audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))

        self.assertIn(
            {"code": "commit-drift", "severity": "error", "bridgeId": "example-bridge"},
            findings,
        )
        bridge = card["bridges"][0]
        self.assertEqual("needs-reverify", bridge["codeState"]["value"])
        self.assertEqual("needs-reverify", bridge["runtimeState"]["value"])
        self.assertEqual("accepted-set", bridge["codeState"]["supersededEvidence"][0]["commitSetId"])
        self.assertEqual("accepted-set", bridge["runtimeState"]["supersededEvidence"][0]["commitSetId"])

    def test_reports_registry_deferred_when_policy_requires_registry(self):
        card = copy.deepcopy(load_fixture("valid-flow-card.json"))
        card["registry"] = {
            "status": "pending-user-approval",
            "requiredForDone": True,
            "waiver": None,
        }

        findings = audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))

        self.assertIn(
            {"code": "registry-deferred", "severity": "error", "bridgeId": ""},
            findings,
        )

    def test_invalidates_required_axes_even_when_no_active_evidence_exists(self):
        card = load_fixture("drift-flow-card.json")
        bridge = card["bridges"][0]
        bridge["codeState"]["activeEvidence"] = []
        bridge["runtimeState"]["activeEvidence"] = []

        audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))

        self.assertEqual("needs-reverify", bridge["codeState"]["value"])
        self.assertEqual("needs-reverify", bridge["runtimeState"]["value"])

    def test_closeout_rejects_needs_reverify_without_routine_findings(self):
        card = load_fixture("valid-flow-card.json")
        card["bridges"][0]["runtimeState"]["value"] = "needs-reverify"

        report = audit_flow_report(
            card,
            datetime.fromisoformat("2026-07-11T10:00:00+00:00"),
            "closeout",
        )

        self.assertEqual([], report["findings"])
        self.assertFalse(report["closeoutEligible"])
        self.assertIn(
            {
                "code": "flow-runtime-not-verified",
                "bridgeId": "",
                "axis": "runtime",
                "state": "needs-reverify",
            },
            report["closeoutReasons"],
        )

    def test_closeout_accepts_verified_required_axes(self):
        card = load_fixture("valid-flow-card.json")

        report = audit_flow_report(
            card,
            datetime.fromisoformat("2026-07-11T10:00:00+00:00"),
            "closeout",
        )

        self.assertTrue(report["closeoutEligible"])
        self.assertEqual([], report["closeoutReasons"])

    def test_reports_registry_revision_drift(self):
        card = load_fixture("valid-flow-card.json")
        card["registry"]["lastSyncedStatusRevision"] = 0

        findings = audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))

        self.assertIn(
            {"code": "registry-stale", "severity": "error", "bridgeId": ""},
            findings,
        )

    def test_optional_registry_drift_is_visible_but_does_not_block_closeout(self):
        card = load_fixture("valid-flow-card.json")
        card["registry"]["lastSyncedStatusRevision"] = 0

        report = audit_flow_report(
            card,
            datetime.fromisoformat("2026-07-11T10:00:00+00:00"),
            "closeout",
        )

        self.assertIn(
            {"code": "registry-stale", "severity": "error", "bridgeId": ""},
            report["findings"],
        )
        self.assertTrue(report["closeoutEligible"])

    def test_synchronized_registry_without_revision_is_always_reported(self):
        card = load_fixture("valid-flow-card.json")
        del card["registry"]["lastSyncedStatusRevision"]

        findings = audit_flow(card, datetime.fromisoformat("2026-07-11T10:00:00+00:00"))

        self.assertIn(
            {"code": "registry-revision-unbound", "severity": "error", "bridgeId": ""},
            findings,
        )

    def test_closeout_requires_registry_revision_binding_when_required(self):
        card = load_fixture("valid-flow-card.json")
        card["registry"]["requiredForDone"] = True
        del card["registry"]["lastSyncedStatusRevision"]

        report = audit_flow_report(
            card,
            datetime.fromisoformat("2026-07-11T10:00:00+00:00"),
            "closeout",
        )

        self.assertFalse(report["closeoutEligible"])
        self.assertIn(
            {"code": "registry-revision-unbound", "bridgeId": ""},
            report["closeoutReasons"],
        )

    def test_approved_waiver_allows_closeout_but_keeps_registry_finding_visible(self):
        card = load_fixture("valid-flow-card.json")
        card["registry"].update(
            {
                "requiredForDone": True,
                "lastSyncedStatusRevision": 0,
                "waiver": {"approved": True, "reason": "accepted delivery exception"},
            }
        )

        report = audit_flow_report(
            card,
            datetime.fromisoformat("2026-07-11T10:00:00+00:00"),
            "closeout",
        )

        self.assertIn(
            {"code": "registry-stale", "severity": "error", "bridgeId": ""},
            report["findings"],
        )
        self.assertTrue(report["closeoutEligible"])
        self.assertEqual([], report["closeoutReasons"])

    def test_closeout_cli_exit_code_matches_eligibility(self):
        script = SCRIPT_DIR / "audit_flow.py"
        eligible = subprocess.run(
            [sys.executable, str(script), "--mode", "closeout", str(FIXTURE_DIR / "valid-flow-card.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, eligible.returncode)
        self.assertTrue(json.loads(eligible.stdout)["closeoutEligible"])

        card = load_fixture("valid-flow-card.json")
        card["bridges"][0]["runtimeState"]["value"] = "pending"
        with tempfile.TemporaryDirectory() as directory:
            card_path = Path(directory) / "ineligible.json"
            card_path.write_text(json.dumps(card), encoding="utf-8")
            ineligible = subprocess.run(
                [sys.executable, str(script), "--mode", "closeout", str(card_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(2, ineligible.returncode)
        self.assertFalse(json.loads(ineligible.stdout)["closeoutEligible"])

    def test_routine_cli_keeps_legacy_exit_contract(self):
        script = SCRIPT_DIR / "audit_flow.py"
        valid = subprocess.run(
            [sys.executable, str(script), str(FIXTURE_DIR / "valid-flow-card.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        drift = subprocess.run(
            [sys.executable, str(script), str(FIXTURE_DIR / "drift-flow-card.json")],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, valid.returncode)
        self.assertEqual("routine", json.loads(valid.stdout)["mode"])
        self.assertIsNone(json.loads(valid.stdout)["closeoutEligible"])
        self.assertEqual(2, drift.returncode)
        self.assertIn("commit-drift", {item["code"] for item in json.loads(drift.stdout)["findings"]})

    def test_closeout_reports_structural_failure_instead_of_crashing(self):
        card = load_fixture("valid-flow-card.json")
        card["bridges"][0]["runtimeState"] = None

        report = audit_flow_report(
            card,
            datetime.fromisoformat("2026-07-11T10:00:00+00:00"),
            "closeout",
        )

        self.assertFalse(report["closeoutEligible"])
        self.assertIn(
            {"code": "status-missing", "bridgeId": ""},
            report["closeoutReasons"],
        )


class PublicSkillShapeTest(unittest.TestCase):
    def test_skill_frontmatter_has_only_name_and_description(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        keys = {line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line}

        self.assertEqual({"name", "description"}, keys)

    def test_skill_declares_v3_l3_flow_card_contract(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("Flow Card", text)
        self.assertIn("canonicalStatusCommentUrl", text)
        self.assertIn("currentCommit", text)
        self.assertIn("acceptedCommit", text)

    def test_skill_declares_user_facing_update_and_progressive_loading_contracts(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("Outcome first", text)
        self.assertIn("Treat Flow Card operations as internal bookkeeping", text)
        self.assertIn("Aggregate the whole internal sequence into one update", text)
        self.assertIn("Do not repeat the same result", text)
        self.assertIn("Load only what the route needs", text)
        self.assertIn("Do not read their source during normal operation", text)
        self.assertIn("references/user-facing-messages.md", text)
        self.assertIn("references/conditional-comment-edit.md", text)

    def test_flow_card_template_contains_parse_sentinels_and_revision(self):
        template = (SKILL_DIR / "templates" / "flow-card-comment.md").read_text(encoding="utf-8")

        self.assertIn("<!-- flow-card:start", template)
        self.assertIn('"statusRevision"', template)
        self.assertIn("<!-- flow-card:end", template)

    @unittest.skipUnless(RELEASE_ROOT, "release metadata is not part of an installed skill package")
    def test_release_metadata_and_readmes_describe_v3_and_apache(self):
        readme_zh = (RELEASE_ROOT / "README.md").read_text(encoding="utf-8")
        readme_en = (RELEASE_ROOT / "README.en.md").read_text(encoding="utf-8")
        license_text = (RELEASE_ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertEqual("3.2.1", (RELEASE_ROOT / "VERSION").read_text(encoding="utf-8").strip())
        self.assertIn("Apache-2.0", readme_zh)
        self.assertIn("Flow Card", readme_zh)
        self.assertIn("Apache-2.0", readme_en)
        self.assertIn("Flow Card", readme_en)
        self.assertIn("Apache License", license_text)

    def test_public_templates_do_not_leak_project_specific_repository_names(self):
        public_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_DIR.rglob("*")
            if path.is_file()
            and "tests" not in path.parts
            and path.suffix in {".json", ".md", ".py", ".yaml"}
        ).lower()

        self.assertNotIn("ehr-server", public_text)
        self.assertNotIn("oa-web", public_text)

    def test_bilingual_user_facing_scenarios_lead_with_business_outcomes(self):
        scenarios = load_fixture("user-facing-message-scenarios.json")
        forbidden_leads = ("l3", "flow card", "bridge", "lease", "registry", "s1")

        self.assertEqual(
            {
                "read-only",
                "before-write",
                "write-success",
                "write-failure",
                "waiting-approval",
                "multi-step-recovery",
                "closeout",
            },
            {item["scenario"] for item in scenarios},
        )
        self.assertEqual({"zh", "en"}, {item["language"] for item in scenarios})
        for item in scenarios:
            opening = item["message"].split("\n\n", 1)[0].strip().lower()
            self.assertFalse(opening.startswith(forbidden_leads), item["scenario"])
            for term in ("flow card", "canonical", "revision", "hash", "lease", "registry", "bridge", "代码轴", "运行轴", "租约"):
                self.assertNotIn(term, item["message"].lower(), item["scenario"])
            for phrase in item["mustContain"]:
                self.assertIn(phrase, item["message"])

    @unittest.skipUnless(RELEASE_ROOT, "release metadata is not part of an installed skill package")
    def test_python_bytecode_is_not_a_release_artifact(self):
        ignore_rules = (RELEASE_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("__pycache__/", ignore_rules)
