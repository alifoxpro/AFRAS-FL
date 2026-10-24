"""Synthetic-only validation of frozen Stage19 nine-device inferential units.

These test fixtures are arbitrary numbers and are never a native result.
"""
import copy
import itertools
import math
import unittest

import independent_device_paired_analysis as a


def fixture_plan():
    tasks=[]
    for i,d in enumerate(a.CANONICAL_DEVICES,1):
        others=[x for x in a.CANONICAL_DEVICES if x!=d]
        for method,seed in itertools.product(a.METHODS,a.SEEDS):
            tasks.append({
                "task_id":f"fold_{i:02d}__{d}__{method}__seed{seed}",
                "fold":i,
                "heldout_device":d,
                "method":method,
                "seed":seed,
                "source_clients":others,
                "expected_training_source_clients":8,
                "native_test_policy":"All original native heldout rows; no target subsampling",
            })
    return {
        "status":"PLAN_ONLY__NO_TARGET_OPENED",
        "runs_planned":54,"runs_executed_by_planner":0,
        "source_manifest_sha256":"1"*64,
        "frozen_core_full_execution_authorized":False,
        "tasks":tasks,
    }


def fixture_results(plan):
    result={}
    for t in plan["tasks"]:
        device=t["heldout_device"]
        idx=a.CANONICAL_DEVICES.index(device)
        seed=t["seed"]
        # Hand-crafted nonreal per-device synthetic model differences.
        baseline=.55 + (idx*.02) + ((seed-3107)*.001)
        score=baseline+(.01 if t["method"]=="FedProx" else 0.0)
        result[t["task_id"]]={
            "native_class_support":{"benign":100,"gafgyt_combo":100},
            "source_sampling_sha256":{
                d:("a"*63+str(idx)) for d in t["source_clients"]
            },
            "source_transform_sha256":"c"*64,
            "metrics":{
                "rows":200,
                "balanced_accuracy":score,
                "benign_fpr":.1,
                "attack_recall":.9,
            },
        }
    return result


class FrozenPreResultTests(unittest.TestCase):
    def test_exact_54_task_roster_and_no_cherrypicking(self):
        p=fixture_plan()
        self.assertEqual(len(a.full_plan_tasks(p)),54)
        bad=copy.deepcopy(p)
        bad["tasks"]=bad["tasks"][:-1]
        with self.assertRaisesRegex(ValueError,"All 54"):
            a.full_plan_tasks(bad)
        bad=copy.deepcopy(p)
        bad["tasks"][0],bad["tasks"][1]=bad["tasks"][1],bad["tasks"][0]
        with self.assertRaisesRegex(ValueError,"Missing, reordered"):
            a.full_plan_tasks(bad)

    def test_one_device_is_one_statistical_unit_even_with_three_seeds(self):
        p=fixture_plan()
        result=a.aggregate(fixture_results(p),p)
        self.assertEqual(result["total_runs"],54)
        self.assertEqual(result["n_heldout_devices"],9)
        self.assertEqual(result["paired_inference"]["sign_flip_combinations"],512)
        self.assertAlmostEqual(result["paired_inference"]["paired_difference"],.01)
        self.assertAlmostEqual(result["mean_native_device_balanced_accuracy"]["FedProx"]
                               -result["mean_native_device_balanced_accuracy"]["FedAvg"],.01)
        self.assertEqual(len(result["by_device"]),9)
        self.assertEqual(result["paired_inference"]["unit_of_inference"],
                         "NINE_HELDOUT_DEVICES__NOT_ROWS_OR_SEEDS")
        self.assertFalse(result["scientific_novelty_established"])

    def test_unmatched_seed_sample_bank_refused(self):
        p=fixture_plan()
        results=fixture_results(p)
        task=next(t for t in p["tasks"] if t["method"]=="FedProx")
        results[task["task_id"]]["source_sampling_sha256"]["Ennio_Doorbell"]="bad"
        if task["heldout_device"]=="Ennio_Doorbell":
            results[task["task_id"]]["source_sampling_sha256"]["Samsung_SNH_1011_N_Webcam"]="bad"
        with self.assertRaisesRegex(ValueError,"Unmatched baseline"):
            a.aggregate(results,p)

    def test_native_class_support_must_be_unchanged_across_seeds(self):
        p=fixture_plan()
        results=fixture_results(p)
        t=p["tasks"][0]
        results[t["task_id"]]["native_class_support"]["benign"]=101
        with self.assertRaisesRegex(ValueError,"Unmatched baseline"):
            a.aggregate(results,p)

    def test_metric_recalculation_rejects_false_balanced_accuracy(self):
        raw={
            "confusion":{"tp":80,"tn":70,"fp":30,"fn":20},
            "native_target_rows":200,
            "balanced_accuracy":.76,
            "benign_fpr":.3,
            "attack_recall":.8,
            "classwise_native_metrics":{"benign":{"support":100}},
        }
        with self.assertRaisesRegex(ValueError,"contradict"):
            a.validate_confusion(raw)
        raw["balanced_accuracy"]=.75
        self.assertAlmostEqual(a.validate_confusion(raw)["balanced_accuracy"],.75)

    def test_exact_sign_flip_under_null_is_conservative(self):
        result=a.inference([0.0]*9,replicates=120,seed=3107)
        self.assertEqual(result["two_sided_exact_sign_flip_p"],1.)
        self.assertEqual(result["percentile_95_ci"],[0.,0.])
        self.assertEqual(result["sign_flip_combinations"],512)
        with self.assertRaisesRegex(ValueError,"nine"):
            a.inference([.1]*54)

    def test_all_same_direction_randomization_has_exact_p_two_over_512(self):
        result=a.inference([.15]*9,replicates=120,seed=3107)
        self.assertAlmostEqual(result["two_sided_exact_sign_flip_p"],2/512)
        self.assertAlmostEqual(result["paired_difference"],.15)
        self.assertTrue(0<=result["percentile_95_ci"][0]<=result["percentile_95_ci"][1]<=1)

    def test_early_partial_54_result_rejected(self):
        p=fixture_plan()
        results=fixture_results(p)
        results.pop(p["tasks"][0]["task_id"])
        with self.assertRaisesRegex(ValueError,"All 54"):
            a.aggregate(results,p)


if __name__=="__main__":
    unittest.main()
