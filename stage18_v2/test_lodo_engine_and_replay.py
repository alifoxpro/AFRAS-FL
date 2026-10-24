"""Stage18 V2: synthetic software tests; NEVER native heldout performance evidence."""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

import lodo_engine as e
import replay_predictions as r


def make_inventory(path:Path, device:str, counts:dict):
    with path.open("w",newline="",encoding="utf8") as f:
        w=csv.writer(f)
        w.writerow(("device","class","total_rows"))
        for label in r.LABELS:
            w.writerow((device,label,counts.get(label,0)))


class FrozenSourceGuards(unittest.TestCase):
    def test_core_v1_is_exact_and_all_nine_folds_separate(self):
        spec=e.verify_frozen_core(e.CORE)
        self.assertFalse(spec["full_execution_authorized"])
        self.assertEqual(tuple(spec["data"]["device_names"]),tuple(e.native.DEVICES))
        self.assertEqual(len(spec["modeling"]["random_seeds"]),3)
        for held in e.native.DEVICES:
            src=e.fold_sources(held)
            self.assertEqual(len(src),8)
            self.assertNotIn(held,src)
            self.assertEqual(set(src)|{held},set(e.native.DEVICES))

    def test_confirmatory_rejected_without_gate_before_any_data_load(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            args=argparse.Namespace(
                source_root=root,output_dir=root/"new_output",heldout=e.native.DEVICES[0],
                method="FedAvg",seed=3107,mode="confirmatory",protocol=e.CORE,
                approval_gate=None,preflight_cap=0,preflight_rounds=0,
                preflight_epochs=0
            )
            with patch.object(e,"load_source_only") as load:
                with self.assertRaisesRegex(PermissionError,"gate file"):
                    e.run(args)
                load.assert_not_called()
            self.assertFalse(args.output_dir.exists())

    def test_wrong_code_hash_gate_fails_closed_before_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            gate=root/"gate.json"
            gate.write_text(json.dumps({
                "status":"AUTHORIZED_FOR_CONFIRMATORY_TEST",
                "authorized":True,"approved_by":"synthetic-test-operator",
                "protocol_sha256":"0"*64,
                "engine_sha256":"0"*64,
                "replay_sha256":"0"*64,
            }),encoding="utf8")
            args=argparse.Namespace(
                source_root=root,output_dir=root/"out",heldout=e.native.DEVICES[0],
                method="FedProx",seed=3107,mode="confirmatory",protocol=e.CORE,
                approval_gate=gate,preflight_cap=0,preflight_rounds=0,
                preflight_epochs=0
            )
            with patch.object(e,"load_source_only") as loader:
                with self.assertRaisesRegex(PermissionError,"hashes differ"):
                    e.run(args)
                loader.assert_not_called()
            self.assertFalse(args.output_dir.exists())

    def test_holdout_excluded_in_synthetic_eight_source_training_main(self):
        rng=np.random.default_rng(42)
        target=e.native.DEVICES[0]
        loaded=[]
        header=[f"feature{i}" for i in range(e.N)]
        def source_loader(_root,dev,k,seed,previous):
            self.assertNotEqual(dev,target)
            self.assertEqual(previous,header if loaded else None)
            loaded.append(dev)
            X=rng.normal(size=(12,e.N)).astype(np.float32)
            y=np.asarray([0]*6+[1]*6,dtype=np.float32)
            return (X,y),{
                "native_rows":12,"sample_size":12,
                "sample_row_ids_sha256":"synthetic-only",
                "sample_class_counts":{"benign":6,"gafgyt_combo":6}
            },header

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            args=argparse.Namespace(
                source_root=root,output_dir=root/"result",heldout=target,
                method="FedAvg",seed=3107,mode="preflight",protocol=e.CORE,
                approval_gate=None,preflight_cap=12,preflight_rounds=1,
                preflight_epochs=1
            )
            with patch.object(e,"load_source_only",side_effect=source_loader), \
                 patch.object(e.native,"iter_native_csv",
                              side_effect=AssertionError("No target may be read")):
                e.run(args)
            self.assertEqual(len(loaded),8)
            self.assertEqual(set(loaded),set(e.fold_sources(target)))
            o=json.loads((root/"result"/"run_receipt.json").read_text())
            self.assertEqual(o["source_clients"],8)
            self.assertFalse(o["target_archive_opened"])
            self.assertFalse(o["target_test_scored"])
            self.assertTrue(o["no_target_features_or_labels_accessed"])
            self.assertIsNone(o["target_results"])
            self.assertFalse((root/("Ennio_Doorbell.zip")).exists())


class UniformSamplingAndOptimizer(unittest.TestCase):
    def test_global_uniform_sample_same_chunks_vs_different_chunk_sizes(self):
        rng=np.random.default_rng(31)
        benign=rng.normal(size=(27,e.N))
        attack=rng.normal(size=(33,e.N))
        a=e.UniformDeviceTopK(20,3107)
        b=e.UniformDeviceTopK(20,3107)
        a.ingest(benign,"benign",0)
        a.ingest(attack,"gafgyt_combo",0)
        b.ingest(benign[:5],"benign",0)
        b.ingest(benign[5:],"benign",5)
        for ix in (0,7,19):
            end={0:7,7:19,19:33}[ix]
            b.ingest(attack[ix:end],"gafgyt_combo",ix)
        x1,y1,m1=a.finish()
        x2,y2,m2=b.finish()
        self.assertEqual(m1["sample_row_ids_sha256"],m2["sample_row_ids_sha256"])
        self.assertTrue(np.array_equal(x1,x2))
        self.assertTrue(np.array_equal(y1,y2))
        self.assertEqual(sum(m1["sample_class_counts"].values()),20)
        self.assertEqual(m1["native_rows"],60)

    def test_adamw_fedprox_mu_zero_matches_fedavg(self):
        rng=np.random.default_rng(6)
        X=rng.normal(size=(25,e.N)).astype(np.float32)
        y=np.asarray([0]*12+[1]*13,dtype=np.float32)
        torch.manual_seed(8)
        state={k:v.clone() for k,v in e.native.BinaryMLP().state_dict().items()}
        a,_=e.local_adamw(state,(X,y),"FedAvg",0.,3107,2,12,.001)
        b,_=e.local_adamw(state,(X,y),"FedProx",0.,3107,2,12,.001)
        for key in a:
            self.assertTrue(torch.equal(a[key],b[key]),key)


class RawPredictionStreamAndReplay(unittest.TestCase):
    def sample_run(self,base:Path):
        target=e.native.DEVICES[0]
        # Raw test fixture creates no actual N-BaIoT ZIPs, only mock native CSV handles.
        header=[f"f{i}" for i in range(e.N)]
        benign=np.zeros((4,e.N),dtype=np.float32)
        attack=np.ones((3,e.N),dtype=np.float32)
        def to_handle(arr):
            f=io.StringIO()
            f.write(",".join(header)+"\n")
            for row in arr:
                f.write(",".join(str(float(x)) for x in row)+"\n")
            f.seek(0)
            return f
        def records(root,dev):
            self.assertEqual(dev,target)
            yield "benign",to_handle(benign)
            yield "gafgyt_combo",to_handle(attack)
        torch.manual_seed(9)
        init={k:v.clone() for k,v in e.native.BinaryMLP().state_dict().items()}
        pth=base/"target_predictions.csv.gz"
        with patch.object(e.native,"iter_native_csv",side_effect=records):
            counts,digest=e.write_all_target_predictions(
                base,target,init,header,
                np.zeros(e.N,dtype=np.float32),
                np.ones(e.N,dtype=np.float32),pth)
        self.assertEqual(sum(counts.values()),7)
        self.assertEqual(len(counts),len(r.LABELS))
        self.assertEqual(counts["mirai_ack"],0)
        inventory=base/"analysis_only_inventory.csv"
        make_inventory(inventory,target,counts)
        receipt=base/"run_receipt.json"
        receipt.write_text(json.dumps({
            "mode":"confirmatory","status":"CONFIRMATORY_RAW_PREDICTION_OUTPUT",
            "heldout_device":target,"training_devices":list(e.fold_sources(target)),
            "target_test_scored":True,"target_archive_opened":True,
            "source_clients":8,"model":"FedAvg","seed":3107,
            "protocol_sha256":"synthetic-fixture-hash",
            "engine_sha256":"synthetic-fixture-hash",
            "target_results":{
                "raw_file":pth.name,"raw_sha256":digest,
                "native_class_support":counts,"rows":7
            }
        }))
        return target,pth,inventory,receipt

    def test_stage13_canonical_digest_equal_for_signed_zero(self):
        import hashlib
        base=np.zeros((1,e.N),dtype=np.float64)
        minus=base.copy()
        minus[0,4]=-0.0
        digest_a=e.raw_feature_digests(base)[0]
        digest_b=e.raw_feature_digests(minus)[0]
        self.assertEqual(digest_a,digest_b)
        ref=np.ascontiguousarray(base,dtype="<f8")
        ref[ref==0]=0.0
        self.assertEqual(
            digest_a,hashlib.blake2b(ref.tobytes(),digest_size=16).hexdigest()
        )

    def test_bad_vector_digest_rejected_even_when_raw_sha_updated(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            _,pth,inv,receipt=self.sample_run(base)
            with gzip.open(pth,"rt",newline="") as f:
                lines=f.readlines()
            cols=lines[1].strip().split(",")
            cols[-2]="not_a_valid_digest"
            lines[1]=",".join(cols)+"\n"
            with gzip.open(pth,"wt",newline="") as f:
                f.writelines(lines)
            obj=json.loads(receipt.read_text())
            obj["target_results"]["raw_sha256"]=e.file_sha256(pth)
            receipt.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,"Invalid canonical Stage13"):
                r.replay_and_validate(receipt,inv,base/"reject.json")

    def test_native_original_row_stream_and_independent_metric_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            target,pth,inv,receipt=self.sample_run(base)
            result=r.replay_and_validate(receipt,inv,base/"metric_replay.json")
            self.assertEqual(result["metrics"]["native_target_rows"],7)
            self.assertEqual(result["metrics"]["confusion"]["tp"]
                +result["metrics"]["confusion"]["fn"],3)
            self.assertEqual(result["metrics"]["confusion"]["tn"]
                +result["metrics"]["confusion"]["fp"],4)
            self.assertEqual(
                result["metrics"]["classwise_native_metrics"]["mirai_ack"]["attack_recall"],
                "NON_ESTIMABLE"
            )
            self.assertEqual(result["device"],target)

    def test_missing_target_row_refused_despite_valid_rehashed_raw_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            _,pth,inv,receipt=self.sample_run(base)
            with gzip.open(pth,"rt",newline="") as f:
                lines=f.readlines()
            with gzip.open(pth,"wt",newline="") as f:
                f.writelines(lines[:-1])
            payload=json.loads(receipt.read_text())
            payload["target_results"]["raw_sha256"]=e.file_sha256(pth)
            receipt.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError,"Incomplete/extra"):
                r.replay_and_validate(receipt,inv,base/"no.json")

    def test_invalid_heldout_probabilities_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            _,pth,inv,receipt=self.sample_run(base)
            with gzip.open(pth,"rt",newline="") as f:
                lines=f.readlines()
            fields=lines[1].strip().split(",")
            fields[-1]="nan"
            lines[1]=",".join(fields)+"\n"
            with gzip.open(pth,"wt",newline="") as f:
                f.writelines(lines)
            data=json.loads(receipt.read_text())
            data["target_results"]["raw_sha256"]=e.file_sha256(pth)
            receipt.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"Invalid model output"):
                r.replay_and_validate(receipt,inv,base/"invalid.json")


if __name__=="__main__":
    unittest.main()
