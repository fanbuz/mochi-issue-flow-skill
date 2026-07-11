import copy
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from audit_flow import audit_flow
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

        self.assertEqual("3.0.1", (RELEASE_ROOT / "VERSION").read_text(encoding="utf-8").strip())
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

    @unittest.skipUnless(RELEASE_ROOT, "release metadata is not part of an installed skill package")
    def test_python_bytecode_is_not_a_release_artifact(self):
        ignore_rules = (RELEASE_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("__pycache__/", ignore_rules)
