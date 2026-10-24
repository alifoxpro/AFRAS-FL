"""Scientific/negative tests for original-source-vs-actual-trained exposure.

Synthetic digests and rows ONLY. Never import or open original N-BaIoT ZIPs.
"""
from __future__ import annotations
import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import full_source_vs_training_exposure as a
from training_exposure_strata import LABELS


def write_predictions(path, rows):
    with gzip.open(path,"wt",encoding="utf8",newline="") as f:
        w=csv.writer(f)
        w.writerow(("device","attack_class","source_row_index","y_true",
                    "feature_digest","attack_probability"))
        w.writerows(rows)


class GenuineThreeSourceStrataTests(unittest.TestCase):
    def test_source_index_masks_exclude_heldout_self_and_preserve_cross_device(self):
        with tempfile.TemporaryDirectory() as scratch:
            path=Path(scratch)/"vectors.sqlite3"
            con=a.create_digest_index(path)
            try:
                v=b"\x11"*16
                self.assertEqual(a.add_device_fingerprints(con,0,[v,v]),1)
                same=con.execute("SELECT device_mask FROM vectors WHERE digest=?",(v,)).fetchone()[0]
                self.assertEqual(same,1)
                self.assertEqual(a.classify(same,0,False),"unavailable")
                self.assertEqual(a.classify(same,1,False),"available_not_used")
                with self.assertRaisesRegex(ValueError,"missing from full"):
                    a.classify(same,0,True)
                self.assertEqual(a.add_device_fingerprints(con,2,[v]),1)
                mask=con.execute("SELECT device_mask FROM vectors WHERE digest=?",(v,)).fetchone()[0]
                self.assertEqual(mask,5)
                self.assertEqual(a.classify(mask,0,True),"trained_exact")
                self.assertEqual(a.classify(mask,2,False),"available_not_used")
                con.commit()
            finally:
                con.close()

    def test_empty_exposure_groups_get_non_estimable_not_zero(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            con=a.create_digest_index(root/"database.sqlite3")
            try:
                x=b"\x11"*16
                y=b"\x22"*16
                a.add_device_fingerprints(con,1,[x])  # Ennio target=0, source=1
                a.add_device_fingerprints(con,2,[y])
                target="Ennio_Doorbell"
                pred=root/"predictions.csv.gz"
                write_predictions(pred,[
                    (target,"benign",0,0,x.hex(),0.7),
                    (target,"benign",1,0,(b"\x33"*16).hex(),0.1),
                    (target,"gafgyt_combo",0,1,x.hex(),0.9),
                    (target,"gafgyt_combo",1,1,y.hex(),0.6),
                    (target,"gafgyt_combo",2,1,(b"\x44"*16).hex(),0.2),
                ])
                r=a.study_one_target(pred,target,{x.hex()},con)
                self.assertEqual(r["full_target_rows"],5)
                attack=r["classwise"]["gafgyt_combo"]
                self.assertEqual(attack["original_target_support"],3)
                q=attack["three_nonoverlapping_strata"]
                self.assertEqual(tuple(q[s]["support"] for s in a.STRATA),(1,1,1))
                self.assertEqual(tuple(q[s]["native_rate"] for s in a.STRATA),(1.,1.,0.))
                benign=r["classwise"]["benign"]
                self.assertEqual(benign["native_rate_type"],"BENIGN_FPR")
                self.assertEqual(
                    benign["three_nonoverlapping_strata"]["available_not_used"]["native_rate"],
                    a.NA)
                absent=r["classwise"]["mirai_ack"]
                self.assertEqual(absent["three_nonoverlapping_strata"]["unavailable"]["native_rate"],
                                 a.NA)
                self.assertEqual(absent["original_target_support"],0)
            finally:
                con.close()

    def test_refuse_duplicate_or_missing_native_target_rows(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            con=a.create_digest_index(root/"db.sqlite3")
            try:
                target="Ennio_Doorbell"
                p=root/"pred.csv.gz"
                write_predictions(p,[
                    (target,"benign",0,0,"a"*32,0.1),
                    (target,"benign",0,0,"b"*32,0.1),
                ])
                with self.assertRaisesRegex(ValueError,"Original row ID"):
                    a.study_one_target(p,target,set(),con)
            finally:
                con.close()

    def test_bad_source_index_values_and_concurrent_existing_index_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            db=Path(t)/"db.sqlite"
            c=a.create_digest_index(db)
            with self.assertRaises(FileExistsError):
                a.create_digest_index(db)
            with self.assertRaisesRegex(ValueError,"Unknown device index"):
                a.add_device_fingerprints(c,9,[b"\x00"*16])
            with self.assertRaisesRegex(ValueError,"Require canonical"):
                a.add_device_fingerprints(c,0,["not a 16 byte digest"])
            with self.assertRaisesRegex(ValueError,"Bad target"):
                a.classify(0,9,False)
            c.close()

    def test_block_all_original_archive_access_when_authorization_missing(self):
        import test_independent_device_paired_analysis as fixtures
        plan=fixtures.fixture_plan()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaisesRegex(PermissionError,"Unapproved"):
                a.check_and_compute(
                    plan,{"status":"NOT_AUTHORIZED_REVIEW_TEMPLATE",
                          "authorized":False},root,root,root/"manifest.json",
                    root/"support.csv",root/"should_never_exist.sqlite3")
            self.assertFalse((root/"should_never_exist.sqlite3").exists())


if __name__=="__main__":
    unittest.main()
