"""Stage18 54-run planning and fail-closed execution tests (synthetic only)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import plan_and_run_54 as plan
import lodo_engine as engine


class FrozenPlanTests(unittest.TestCase):
    def test_exact_nine_folds_two_methods_three_seeds(self):
        tasks=plan.locked_tasks()
        self.assertEqual(len(tasks),54)
        self.assertEqual(len({x["task_id"] for x in tasks}),54)
        for d in engine.native.DEVICES:
            matching=[x for x in tasks if x["heldout_device"]==d]
            self.assertEqual(len(matching),6)
            self.assertEqual({x["method"] for x in matching},{"FedAvg","FedProx"})
            self.assertEqual({x["seed"] for x in matching},{3107,3108,3109})
            self.assertTrue(all(len(x["source_clients"])==8 for x in matching))
            self.assertTrue(all(d not in x["source_clients"] for x in matching))

    def test_plan_only_does_not_load_target_or_source(self):
        with patch.object(engine,"load_source_only",
                          side_effect=AssertionError("Plan must not load native ZIPs")):
            p=plan.create_plan(engine.CORE)
        self.assertEqual(p["runs_planned"],54)
        self.assertEqual(p["runs_executed_by_planner"],0)
        self.assertEqual(p["status"],"PLAN_ONLY__NO_TARGET_OPENED")
        self.assertIsNone(p["manifest_sha256"])

    def test_execution_rejected_without_human_gate_or_manifest(self):
        args=argparse.Namespace(
            approval_gate=None, source_manifest=None,
            protocol=engine.CORE,source_root=None,output_root=Path("never-created"))
        with patch.object(plan.subprocess,"run",
                          side_effect=AssertionError("Must not execute")):
            with self.assertRaises(PermissionError):
                plan.execute_tasks(args,plan.create_plan())
        self.assertFalse(Path("never-created").exists())

    def test_false_source_manifest_digest_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            approval=root/"approval.json"
            manifest=root/"manifest.json"
            manifest.write_text('{"local_archives":[]}',encoding="utf8")
            approval.write_text(json.dumps({
                "status":"AUTHORIZED_FOR_CONFIRMATORY_TEST",
                "authorized":True,
                "approved_by":"test-only-never-authorize",
                "protocol_sha256":engine.file_sha256(engine.CORE),
                "engine_sha256":engine.file_sha256(Path(engine.__file__)),
                "replay_sha256":engine.file_sha256(engine.REPLAY),
                "source_manifest_sha256":"0"*64,
            }),encoding="utf8")
            args=argparse.Namespace(
                approval_gate=approval,source_manifest=manifest,
                protocol=engine.CORE,source_root=root,output_root=root/"outputs")
            with patch.object(plan.subprocess,"run",
                              side_effect=AssertionError("Must not execute")):
                with self.assertRaisesRegex(PermissionError,"not the approved"):
                    plan.execute_tasks(args,plan.create_plan())
            self.assertFalse(args.output_root.exists())

    def test_existing_partial_run_not_skipped(self):
        task=plan.locked_tasks()[0]
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder)
            (run/"run_receipt.json").write_text("{}",encoding="utf8")
            self.assertFalse(plan.verify_completed(run,task))

    def test_tampered_existing_completion_receipt_rejected(self):
        task=plan.locked_tasks()[0]
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder)
            (run/"run_receipt.json").write_text(
                json.dumps({"heldout_device":"WRONG","mode":"confirmatory",
                            "training_devices":[],"target_results":{}}),
                encoding="utf8")
            (run/"independent_replay.json").write_text(
                json.dumps({"status":"INDEPENDENT_FULL_NATIVE_TARGET_PREDICTION_REPLAY"}),
                encoding="utf8")
            with self.assertRaisesRegex(ValueError,"do not match"):
                plan.verify_completed(run,task)


if __name__=="__main__":
    unittest.main()
