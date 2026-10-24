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
        self.assertIsNone(p["source_manifest_sha256"])

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
                "native_loader_sha256":engine.file_sha256(Path(engine.native.__file__)),
                "requirements_sha256":engine.file_sha256(
                    engine.ROOT/"stage17_v2"/"requirements-pilot.txt"),
                "native_inventory_sha256":engine.file_sha256(
                    engine.ROOT/"stage16_v2"/"EXPOSURE_ELIGIBILITY_ANALYSIS_ONLY.csv"),
                "orchestration_sha256":engine.file_sha256(
                    engine.ROOT/"stage18_v2"/"plan_and_run_54.py"),
                "exposure_analysis_protocol_sha256":engine.file_sha256(
                    engine.ROOT/"stage16_v2"/"PRE_RESULT_EXPOSURE_ESTIMAND_CLARIFICATION_2026-10-24.md"),
                "human_review_complete":True,
                "independent_data_admission_complete":True,
                "no_target_results_reviewed":True,
                "original_nine_zip_admission_scanner_sha256":engine.file_sha256(
                    engine.ROOT/"stage18_v2"/"verify_original_nine_zip_bytes.py"),
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

    def test_review_attestation_required_even_with_all_hashes_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            receipt=base/"unapproved.json"
            fields={
                "status":"AUTHORIZED_FOR_CONFIRMATORY_TEST",
                "authorized":True,
                "approved_by":"synthetic-test-reviewer",
                "protocol_sha256":engine.file_sha256(engine.CORE),
                "engine_sha256":engine.file_sha256(Path(engine.__file__)),
                "replay_sha256":engine.file_sha256(engine.REPLAY),
                "native_loader_sha256":engine.file_sha256(Path(engine.native.__file__)),
                "requirements_sha256":engine.file_sha256(
                    engine.ROOT/"stage17_v2"/"requirements-pilot.txt"),
                "native_inventory_sha256":engine.file_sha256(
                    engine.ROOT/"stage16_v2"/"EXPOSURE_ELIGIBILITY_ANALYSIS_ONLY.csv"),
                "human_review_complete":False,
                "independent_data_admission_complete":True,
                "no_target_results_reviewed":True,
            }
            receipt.write_text(json.dumps(fields))
            with self.assertRaises(PermissionError):
                engine.assert_approval(receipt,engine.CORE)

    def test_prior_revision_cannot_be_resumed_as_current_confirmatory_evidence(self):
        task=plan.locked_tasks()[0]
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/"run_receipt.json").write_text(json.dumps({
                "heldout_device":task["heldout_device"],
                "model":task["method"],
                "seed":task["seed"],
                "mode":"confirmatory",
                "protocol_sha256":"stale-protocol-sha",
                "engine_sha256":"stale-engine-sha",
                "training_devices":task["source_clients"]
            }),encoding="utf8")
            (folder/"independent_replay.json").write_text(json.dumps({
                "status":"INDEPENDENT_FULL_NATIVE_TARGET_PREDICTION_REPLAY",
                "engine_sha256":"stale-engine-sha",
                "protocol_sha256":"stale-protocol-sha",
            }),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"different code/protocol/approval"):
                plan.verify_completed(folder,task)

    def _nine_original_stub_archives(self,root):
        import hashlib
        original=[]
        for idx,device in enumerate(engine.native.DEVICES):
            payload=(device+"-synthetic-original-ZIP-bytes").encode("utf8")
            (root/(device+".zip")).write_bytes(payload)
            original.append({
                "device":device,"filename":device+".zip",
                "local_sha256":hashlib.sha256(payload).hexdigest(),
                "local_bytes":len(payload)
            })
        manifest=root/"original_manifest.json"
        manifest.write_text(json.dumps({
            "manifest_schema":"AFRAS_V2_ORIGINAL_NINE_DEVICE_ZIP_EXPECTED_BYTES_V1",
            "local_archives":original
        }))
        return manifest

    def test_fresh_original_byte_scan_fails_before_any_target_execution(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            manifest=self._nine_original_stub_archives(root)
            # Corruption AFTER issuing manifest: a SHA mismatch, never acceptable.
            (root/(engine.native.DEVICES[-1]+".zip")).write_bytes(
                b"CORRUPT-SYNTHETIC-ORIGINAL-ZIP")
            args=argparse.Namespace(
                approval_gate=root/"fictional_approval.json",
                source_manifest=manifest,
                protocol=engine.CORE,
                source_root=root,output_root=root/"runs")
            fake={"source_manifest_sha256":engine.file_sha256(manifest)}
            with patch.object(engine,"assert_approval",return_value=(fake,{})), \
                 patch.object(plan.subprocess,"run",
                              side_effect=AssertionError("Must not execute any FL")):
                with self.assertRaisesRegex(ValueError,"ZIP byte size differs|ZIP SHA-256 mismatch"):
                    plan.execute_tasks(args,plan.create_plan())
            self.assertFalse(args.output_root.exists())

    def test_fresh_original_byte_gate_succeeds_before_first_fit_is_launched(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            manifest=self._nine_original_stub_archives(root)
            args=argparse.Namespace(
                approval_gate=root/"fictional_approval.json",
                source_manifest=manifest,
                protocol=engine.CORE,
                source_root=root,output_root=root/"runs")
            fake={"source_manifest_sha256":engine.file_sha256(manifest)}
            with patch.object(engine,"assert_approval",return_value=(fake,{})), \
                 patch.object(plan.subprocess,"run",
                              side_effect=RuntimeError("INTENTIONAL_ABORT_BEFORE_TARGET")):
                with self.assertRaisesRegex(RuntimeError,"INTENTIONAL_ABORT_BEFORE_TARGET"):
                    plan.execute_tasks(args,plan.create_plan())
            receipt=args.output_root/"ORIGINAL_NINE_ZIP_BYTE_ADMISSION.json"
            self.assertTrue(receipt.exists())
            obj=json.loads(receipt.read_text())
            self.assertEqual(obj["original_zips_verified"],9)
            self.assertFalse(obj["heldout_model_predictions_generated"])
            self.assertFalse(obj["human_scientific_approval_created"])

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
            with self.assertRaisesRegex(ValueError,"different code/protocol/approval|do not match"):
                plan.verify_completed(run,task)


if __name__=="__main__":
    unittest.main()
