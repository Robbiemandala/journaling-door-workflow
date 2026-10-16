import json
import tempfile
import unittest
from pathlib import Path

from door_workflow.core import (build_patterns, capture, decide, duplicate_review, export_public,
                                plan_workflow, privacy_check, record_deliverable, record_run,
                                replan_workflow, resolve_duplicate, search, verify_workflow, write_json)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make_artifact(self, name, text="evidence"):
        path = self.root / "artifacts" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path.relative_to(self.root))

    def test_full_human_gated_loop(self):
        source = capture(self.root, "A reflection about signal.\nIdea: Make provenance visible.", title="Signal")
        idea = json.loads(next((self.root / "data" / "ideas").glob("*.json")).read_text())
        with self.assertRaises(ValueError):
            decide(self.root, idea["id"], "pursue")
        decision = decide(self.root, idea["id"], "pursue", target="demo-repo", completion_proof="verified artifact")
        workflow = plan_workflow(self.root, decision["id"], worker_model="cheap-worker")
        with self.assertRaises(ValueError):
            record_run(self.root, workflow["id"], "worker", "completed", artifacts=[self.make_artifact("worker.txt")])
        record_run(self.root, workflow["id"], "scout", "completed", artifacts=[self.make_artifact("scout.txt")])
        record_run(self.root, workflow["id"], "worker", "completed", artifacts=[self.make_artifact("worker.txt")])
        record_run(self.root, workflow["id"], "verifier", "completed", artifacts=[self.make_artifact("verify.txt")])
        verified = verify_workflow(self.root, workflow["id"])
        self.assertEqual(verified["status"], "integrity_verified")
        self.assertFalse(verified["claims"]["agents_actually_ran"])
        deliverable = record_deliverable(self.root, decision["id"], "Demo artifact", artifact="artifacts/worker.txt", proof="verified artifact", verifier_result="PASS: completion criterion addressed")
        self.assertEqual(deliverable["decision_id"], decision["id"])
        self.assertFalse(json.loads((self.root / "data" / "workflows" / f"{workflow['id']}.json").read_text())["routing_proven"])

    def test_stale_receipt_is_waiting(self):
        source = capture(self.root, "Idea: Keep evidence inspectable.")
        idea = json.loads(next((self.root / "data" / "ideas").glob("*.json")).read_text())
        decision = decide(self.root, idea["id"], "pursue", target="x", completion_proof="y")
        workflow = plan_workflow(self.root, decision["id"])
        scout = self.make_artifact("scout.txt", "one")
        worker = self.make_artifact("worker.txt", "one")
        verifier = self.make_artifact("verifier.txt", "one")
        record_run(self.root, workflow["id"], "scout", "completed", artifacts=[scout])
        record_run(self.root, workflow["id"], "worker", "completed", artifacts=[worker])
        record_run(self.root, workflow["id"], "verifier", "completed", artifacts=[verifier])
        Path(self.root / worker).write_text("changed", encoding="utf-8")
        checked = verify_workflow(self.root, workflow["id"])
        self.assertEqual(checked["status"], "waiting")
        self.assertIn(worker, checked["stale_artifacts"])

    def test_verifier_alias_is_normalized_and_cannot_be_independent(self):
        capture(self.root, "Idea: Compare evidence paths canonically.")
        idea = json.loads(next((self.root / "data" / "ideas").glob("*.json")).read_text())
        decision = decide(self.root, idea["id"], "pursue", target="x", completion_proof="y")
        workflow = plan_workflow(self.root, decision["id"])
        scout = self.make_artifact("scout.txt")
        shared = self.make_artifact("shared.txt")
        record_run(self.root, workflow["id"], "scout", "completed", artifacts=[scout])
        worker_run = record_run(self.root, workflow["id"], "worker", "completed", artifacts=[shared])
        (self.root / "artifacts" / "shared-link.txt").symlink_to(self.root / shared)
        with self.assertRaisesRegex(ValueError, "symlink"):
            record_run(self.root, workflow["id"], "verifier", "completed", artifacts=["artifacts/shared-link.txt"])
        verifier_run = record_run(self.root, workflow["id"], "verifier", "completed", artifacts=["./" + shared])
        self.assertEqual(worker_run["artifacts"], [shared])
        self.assertEqual(verifier_run["artifacts"], [shared])
        checked = verify_workflow(self.root, workflow["id"])
        self.assertEqual(checked["status"], "waiting")
        self.assertFalse(checked["independent_verifier_receipt"])
        self.assertIn("verifier evidence overlaps worker evidence", checked["waiting_reasons"])

    def test_malformed_completed_receipt_waits_without_traceback(self):
        capture(self.root, "Idea: Validate every receipt before verification.")
        idea = json.loads(next((self.root / "data" / "ideas").glob("*.json")).read_text())
        decision = decide(self.root, idea["id"], "pursue", target="x", completion_proof="y")
        workflow = plan_workflow(self.root, decision["id"])
        scout = self.make_artifact("scout.txt")
        worker = self.make_artifact("worker.txt")
        verifier = self.make_artifact("verifier.txt")
        record_run(self.root, workflow["id"], "scout", "completed", artifacts=[scout])
        record_run(self.root, workflow["id"], "worker", "completed", artifacts=[worker])
        malformed = record_run(self.root, workflow["id"], "verifier", "completed", artifacts=[verifier])
        malformed["artifact_evidence"] = [{}]
        write_json(self.root / "data" / "receipts" / f"{malformed['id']}.json", malformed)
        # An unrelated wrong-shaped receipt is also treated as invalid evidence,
        # rather than being allowed to throw while audit records are read.
        (self.root / "data" / "receipts" / "wrong-shape.json").write_text("[]", encoding="utf-8")
        checked = verify_workflow(self.root, workflow["id"])
        self.assertEqual(checked["status"], "waiting")
        self.assertIn("invalid receipt schema: evidence path must be a string", checked["waiting_reasons"])
        self.assertIn("invalid receipt schema: top-level record must be an object", checked["waiting_reasons"])

    def test_blocked_requires_replan_and_restarts_dag(self):
        capture(self.root, "Idea: Replan after a blocked worker.")
        idea = json.loads(next((self.root / "data" / "ideas").glob("*.json")).read_text())
        decision = decide(self.root, idea["id"], "pursue", target="x", completion_proof="y")
        workflow = plan_workflow(self.root, decision["id"])
        scout = self.make_artifact("scout.txt")
        record_run(self.root, workflow["id"], "scout", "completed", artifacts=[scout])
        record_run(self.root, workflow["id"], "worker", "blocked", summary="missing input")
        with self.assertRaises(ValueError):
            record_run(self.root, workflow["id"], "worker", "completed", artifacts=[self.make_artifact("worker.txt")])
        replan_workflow(self.root, workflow["id"], reason="input arrived")
        with self.assertRaises(ValueError):
            record_run(self.root, workflow["id"], "worker", "completed", artifacts=[self.make_artifact("worker-2.txt")])

    def test_duplicate_and_independent_patterns(self):
        first = capture(self.root, "Idea: Notice the signal.\nThe signal repeats.")
        second = capture(self.root, "Idea: Notice the signal.\nThe signal repeats.")
        self.assertTrue(duplicate_review(self.root))
        resolve_duplicate(self.root, second["id"], first["id"])
        pattern = build_patterns(self.root)
        # A recurrence is retained but does not inflate independent-source counts.
        self.assertFalse([row for row in pattern["patterns"] if row["token"] == "signal"])
        self.assertTrue(search(self.root, "signal"))

    def test_privacy_and_export(self):
        capture(self.root, "A fictional note.")
        self.assertEqual(privacy_check(self.root)["status"], "pass")
        exported = export_public(self.root, self.root / "data" / "exports" / "public")
        payload = json.loads(Path(exported["path"]).read_text())
        self.assertFalse(exported["raw_text_included"])
        self.assertNotIn('"text":', json.dumps(payload))
        self.assertFalse(payload["privacy"]["metadata_included"])
        with self.assertRaises(ValueError):
            export_public(self.root, self.root / "data" / "ideas" / "overwrite")
        (self.root / "bad.json").write_text("/" + "Users/private/name", encoding="utf-8")
        self.assertEqual(privacy_check(self.root)["status"], "fail")

    def test_repeated_pursue_requires_supersession_and_current_plan(self):
        capture(self.root, "Idea: Keep one active lane.")
        idea = json.loads(next((self.root / "data" / "ideas").glob("*.json")).read_text())
        first = decide(self.root, idea["id"], "pursue", target="lane-a", completion_proof="proof-a")
        with self.assertRaises(ValueError):
            decide(self.root, idea["id"], "pursue", target="lane-b", completion_proof="proof-b", note="different note")
        second = decide(self.root, idea["id"], "incubate", note="Pause current lane")
        first_after = json.loads((self.root / "data" / "decisions" / f"{first['id']}.json").read_text())
        self.assertEqual(first_after["status"], "superseded")
        with self.assertRaises(ValueError):
            plan_workflow(self.root, first["id"])
        # A new pursuit can replace the superseded decision explicitly.
        third = decide(self.root, idea["id"], "pursue", target="lane-c", completion_proof="proof-c", supersede=True)
        self.assertEqual(third["status"], "active")

    def test_deliverable_requires_worker_hash_and_regular_inside_root(self):
        capture(self.root, "Idea: Bind delivery to evidence.")
        idea = json.loads(next((self.root / "data" / "ideas").glob("*.json")).read_text())
        decision = decide(self.root, idea["id"], "pursue", target="x", completion_proof="y")
        workflow = plan_workflow(self.root, decision["id"])
        scout = self.make_artifact("scout.txt")
        worker = self.make_artifact("worker.txt", "original")
        verifier = self.make_artifact("verifier.txt")
        record_run(self.root, workflow["id"], "scout", "completed", artifacts=[scout])
        record_run(self.root, workflow["id"], "worker", "completed", artifacts=[worker])
        record_run(self.root, workflow["id"], "verifier", "completed", artifacts=[verifier])
        self.assertEqual(verify_workflow(self.root, workflow["id"])["status"], "integrity_verified")
        Path(self.root / worker).write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValueError):
            record_deliverable(self.root, decision["id"], "Bad", artifact=worker, proof="criterion", verifier_result="PASS")

    def test_missing_or_malformed_source_is_rejected_safely(self):
        with self.assertRaises(ValueError):
            from door_workflow.core import add_hypothesis
            add_hypothesis(self.root, "unsupported claim", source_id="missing")
        malformed = self.root / "data" / "transcripts" / "bad.json"
        malformed.parent.mkdir(parents=True, exist_ok=True)
        malformed.write_text("{not-json", encoding="utf-8")
        self.assertEqual(search(self.root, "anything"), [])


if __name__ == "__main__":
    unittest.main()
