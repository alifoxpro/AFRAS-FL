"""Synthetic-only Stage19 exact exposure reproducibility tests.

NO original UCI test data, no target model inference and no human approvals.
"""
import csv
import gzip
from pathlib import Path
import tempfile
import unittest

import training_exposure_strata as a


def file_gz(path,fields,rows):
    with gzip.open(path,"wt",encoding="utf8",newline="") as f:
        w=csv.writer(f)
        w.writerow(fields)
        w.writerows(rows)


class TrueSampleOnlyExposureTests(unittest.TestCase):
    def test_eight_sources_require_exact_bank_sample_count(self):
        sources=[f"synthetic_source_{i}" for i in range(8)]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"bank.csv.gz"
            rows=[(src,"a"*32) for src in sources for _ in range(2)]
            file_gz(p,a.BANK,rows)
            values=a.training_fingerprints(p,sources,per_client=2)
            self.assertEqual(values,{"a"*32})
            self.assertEqual(len(rows),16)
            with self.assertRaisesRegex(ValueError,"Missing source"):
                a.training_fingerprints(p,sources,per_client=3)

    def test_reject_wrong_source_or_invalid_hash(self):
        sources=[f"source_{i}" for i in range(8)]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"bad.csv.gz"
            file_gz(p,a.BANK,[("NON_SOURCE_DEVICE","b"*32)])
            with self.assertRaisesRegex(ValueError,"Invalid source"):
                a.training_fingerprints(p,sources,per_client=1)

    def test_original_native_support_and_metrics_from_all_rows(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"test.csv.gz"
            rows=[
                ("Ennio_Doorbell","benign",0,0,"a"*32,.7),
                ("Ennio_Doorbell","benign",1,0,"b"*32,.2),
                ("Ennio_Doorbell","gafgyt_combo",0,1,"a"*32,.8),
                ("Ennio_Doorbell","gafgyt_combo",1,1,"b"*32,.1),
            ]
            file_gz(p,a.PRED,rows)
            counts={c:0 for c in a.LABELS}
            counts["benign"]=2
            counts["gafgyt_combo"]=2
            x=a.analyze_target(p,"Ennio_Doorbell",{"a"*32},counts)
            self.assertEqual(x["original_target_rows"],4)
            self.assertEqual(x["eligible_attack_classes"],1)
            self.assertEqual(x["classwise"]["benign"]["exposed_metric"],1.)
            self.assertEqual(x["classwise"]["benign"]["unexposed_metric"],0.)
            self.assertEqual(x["classwise"]["gafgyt_combo"]["exposed_metric"],1.)
            self.assertEqual(x["classwise"]["gafgyt_combo"]["unexposed_metric"],0.)
            self.assertEqual(x["classwise"]["mirai_ack"]["exposed_metric"],a.NA)
            self.assertFalse(x["classwise"]["mirai_ack"]["both_strata_estimable"])

    def test_missing_original_row_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"test.csv.gz"
            file_gz(p,a.PRED,[
                ("Ennio_Doorbell","benign",0,0,"a"*32,.4),
            ])
            counts={c:0 for c in a.LABELS}
            counts["benign"]=2
            with self.assertRaisesRegex(ValueError,"Native class support"):
                a.analyze_target(p,"Ennio_Doorbell",{"a"*32},counts)

    def test_no_54_results_cannot_generate_any_scientific_summary(self):
        import test_independent_device_paired_analysis as fixtures
        plan=fixtures.fixture_plan()
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FileNotFoundError):
                a.analyze_all(plan,Path(t),{
                    "status":"AUTHORIZED_FOR_CONFIRMATORY_TEST",
                    "authorized":True
                })


if __name__=="__main__":
    unittest.main()
