import copy
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from conditional_comment_edit import ConditionalEditError, conditional_edit
from flow_status import canonical_card_hash


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_card() -> dict:
    return json.loads((FIXTURE_DIR / "valid-flow-card.json").read_text(encoding="utf-8"))


def comment_body(card: dict) -> str:
    payload = json.dumps(card, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        "## Flow status\n\n"
        f"<!-- flow-card:start flowId={card['flowId']} protocol=3.0 -->\n"
        f"```json\n{payload}\n```\n"
        f"<!-- flow-card:end flowId={card['flowId']} -->"
    )


def build_request(current: dict, safety_mode: str = "best-effort-conditional") -> dict:
    target = copy.deepcopy(current)
    target["statusRevision"] += 1
    target["registry"]["status"] = "out-of-sync"
    return {
        "canonicalStatusCommentUrl": current["canonicalStatusCommentUrl"],
        "expectedStatusRevision": current["statusRevision"],
        "expectedCanonicalHash": canonical_card_hash(current),
        "safetyMode": safety_mode,
        "actor": {
            "agentId": "example-agent",
            "threadId": "thread-1",
            "sessionId": "session-1",
        },
        "targetCanonicalComment": {
            "url": target["canonicalStatusCommentUrl"],
            "body": comment_body(target),
        },
    }


class FakeCommentAdapter:
    def __init__(
        self,
        card: dict,
        *,
        supports_atomic_cas: bool = False,
        edit_behavior: str = "success",
    ) -> None:
        self.url = card["canonicalStatusCommentUrl"]
        self.body = comment_body(card)
        self.supports_atomic_cas = supports_atomic_cas
        self.edit_behavior = edit_behavior
        self.edit_count = 0
        self.last_precondition = None

    def read_comment(self, url: str) -> dict:
        return {
            "canonicalStatusCommentUrl": self.url,
            "canonicalComment": {"url": self.url, "body": self.body},
        }

    def edit_comment(self, url: str, body: str, precondition: dict) -> None:
        self.edit_count += 1
        self.last_precondition = precondition
        if self.edit_behavior == "failure":
            raise RuntimeError("provider failure with private details")
        if self.edit_behavior == "timeout":
            raise TimeoutError("provider result is unknown")
        if self.edit_behavior == "mismatch":
            return
        self.body = body


class ConditionalCommentEditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime.fromisoformat("2026-07-16T10:00:00+00:00")

    def test_best_effort_edit_verifies_saved_revision_and_hash(self):
        current = load_card()
        request = build_request(current)
        adapter = FakeCommentAdapter(current)

        result = conditional_edit(request, adapter, self.now)

        self.assertEqual("success", result["outcome"])
        self.assertEqual("best-effort-conditional", result["safetyMode"])
        self.assertTrue(result["registryMaySync"])
        self.assertEqual(1, adapter.edit_count)
        self.assertEqual(current["statusRevision"], adapter.last_precondition["expectedStatusRevision"])

    def test_atomic_edit_requires_and_uses_native_capability(self):
        current = load_card()
        request = build_request(current, "atomic-cas")
        adapter = FakeCommentAdapter(current, supports_atomic_cas=True)

        result = conditional_edit(request, adapter, self.now)

        self.assertEqual("success", result["outcome"])
        self.assertEqual("atomic-cas", adapter.last_precondition["safetyMode"])

    def test_rejects_revision_drift_before_edit(self):
        current = load_card()
        request = build_request(current)
        changed = copy.deepcopy(current)
        changed["statusRevision"] += 2
        adapter = FakeCommentAdapter(changed)

        with self.assertRaises(ConditionalEditError) as context:
            conditional_edit(request, adapter, self.now)

        self.assertEqual("revision-drift", context.exception.code)
        self.assertEqual(0, adapter.edit_count)

    def test_rejects_non_owner_in_lease_mode(self):
        current = load_card()
        request = build_request(current)
        request["actor"]["threadId"] = "different-thread"
        adapter = FakeCommentAdapter(current)

        with self.assertRaises(ConditionalEditError) as context:
            conditional_edit(request, adapter, self.now)

        self.assertEqual("ownership-rejected", context.exception.code)
        self.assertEqual(0, adapter.edit_count)

    def test_normalizes_provider_failure_without_leaking_details(self):
        current = load_card()
        adapter = FakeCommentAdapter(current, edit_behavior="failure")

        with self.assertRaises(ConditionalEditError) as context:
            conditional_edit(build_request(current), adapter, self.now)

        self.assertEqual("edit-failed", context.exception.code)
        self.assertNotIn("private details", str(context.exception))

    def test_distinguishes_timeout_with_unknown_provider_result(self):
        current = load_card()
        adapter = FakeCommentAdapter(current, edit_behavior="timeout")

        with self.assertRaises(ConditionalEditError) as context:
            conditional_edit(build_request(current), adapter, self.now)

        self.assertEqual("edit-result-unknown", context.exception.code)

    def test_rejects_post_write_mismatch_and_blocks_registry_sync(self):
        current = load_card()
        adapter = FakeCommentAdapter(current, edit_behavior="mismatch")

        with self.assertRaises(ConditionalEditError) as context:
            conditional_edit(build_request(current), adapter, self.now)

        self.assertEqual("post-write-mismatch", context.exception.code)

    def test_retry_is_idempotent_when_target_was_already_saved(self):
        current = load_card()
        request = build_request(current)
        target_body = request["targetCanonicalComment"]["body"]
        target_card = json.loads(target_body.split("```json\n", 1)[1].split("\n```", 1)[0])
        adapter = FakeCommentAdapter(target_card)

        result = conditional_edit(request, adapter, self.now)

        self.assertEqual("already-applied", result["outcome"])
        self.assertEqual(0, adapter.edit_count)
        self.assertTrue(result["registryMaySync"])

    def test_atomic_mode_rejects_adapter_without_native_cas(self):
        current = load_card()
        request = build_request(current, "atomic-cas")
        adapter = FakeCommentAdapter(current, supports_atomic_cas=False)

        with self.assertRaises(ConditionalEditError) as context:
            conditional_edit(request, adapter, self.now)

        self.assertEqual("adapter-capability-mismatch", context.exception.code)
        self.assertEqual(0, adapter.edit_count)

    def test_lease_check_rejects_naive_current_time(self):
        current = load_card()
        adapter = FakeCommentAdapter(current)

        with self.assertRaises(ConditionalEditError) as context:
            conditional_edit(build_request(current), adapter, datetime.fromisoformat("2026-07-16T10:00:00"))

        self.assertEqual("invalid-request", context.exception.code)
        self.assertEqual(0, adapter.edit_count)


if __name__ == "__main__":
    unittest.main()
