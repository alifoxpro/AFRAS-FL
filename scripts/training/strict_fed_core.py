"""Pure, auditable decision reward and federated metrics (no test dependencies).

This is a re-specified reward for an action-exogenous contextual-bandit
experiment; it is NOT guaranteed to match the manuscript's historical MOSAR.
"""
import math
from numbers import Integral


def normalized_client_weights(sizes, expected_clients=None):
    """Validate FedAvg client counts; never normalize invalid/zero populations."""
    values = list(sizes)
    if not values or (expected_clients is not None and
                      len(values) != expected_clients):
        raise ValueError("Federated client/count cardinality mismatch")
    if any(not isinstance(n, Integral) or isinstance(n, bool) or n <= 0
           for n in values):
        raise ValueError("FedAvg weights require positive integer TRAIN sample counts")
    total = sum(values)
    weights = [n / total for n in values]
    if any(not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError("Nonfinite or zero FedAvg client weight")
    if not math.isclose(math.fsum(weights), 1.0, abs_tol=1e-12):
        raise ValueError("FedAvg weights failed unit-sum check")
    return weights


ACTIONS = ("ALLOW", "RATE_LIMIT", "BLOCK")
SEVERITIES = ("High", "Medium", "Low")
ACTION_FOR_SEVERITY = (2, 1, 0)
ACTION_COST = (0.0, 0.3, 0.5)
SEVERITY_WEIGHT = (1.0, 0.5, 0.1)


def mosar_reward(severity, action, teacher_probs, fuzzy_action=None,
                 fuzzy_confidence=0.0, lambda_fuzzy=0.0, mu_link=0.0):
    """Return stationary reward, optionally plus action-dependent fuzzy bonus.

    The confidence is teacher-model confidence, not the learned Q magnitudes.
    R_latency is an *assumed action-cost proxy*, NOT measured latency.
    """
    if abs(mu_link) > 1e-12:
        raise ValueError("R_link has no validated neighbor action data; mu_link must be zero")
    if severity not in (0, 1, 2) or action not in (0, 1, 2):
        raise ValueError("Invalid severity/action index")
    if len(teacher_probs) != 3 or not all(math.isfinite(float(x)) for x in teacher_probs):
        raise ValueError("Invalid teacher probability vector")
    if any(float(p) < -1e-6 for p in teacher_probs) or abs(sum(map(float, teacher_probs))-1) > 1e-3:
        raise ValueError("Teacher scores must sum to 1")
    if not 0 <= lambda_fuzzy <= 1 or not 0 <= fuzzy_confidence <= 1:
        raise ValueError("Invalid fuzzy parameters")
    correct_action = ACTION_FOR_SEVERITY[severity]
    is_correct = action == correct_action
    detection = 1.0 if is_correct else -0.5
    teacher_accuracy = float(teacher_probs[severity]) - 0.5
    latency_proxy = -0.1 * ACTION_COST[action]
    teacher_conf = max(map(float, teacher_probs)) - (1 / 3)
    quality = 1.0 if is_correct else (-0.5 if action == 0 and severity == 0 else -0.2)
    impact = SEVERITY_WEIGHT[severity] * quality
    base = (0.30 * detection + 0.20 * teacher_accuracy +
            0.15 * latency_proxy + 0.15 * teacher_conf + 0.20 * impact)
    guidance = 0.0
    if fuzzy_action is not None:
        if fuzzy_action not in (0, 1, 2):
            raise ValueError("Invalid rule-recommended action")
        guidance = 0.3 * fuzzy_confidence if fuzzy_action == action else -0.1
    return float(base + lambda_fuzzy * guidance)


def jain_fairness(values):
    if not values:
        raise ValueError("Expected nonempty client success rates")
    if any(x < 0 or not math.isfinite(float(x)) for x in values):
        raise ValueError("Invalid success rate")
    denom = len(values) * sum(x * x for x in values)
    return (sum(values) ** 2 / denom) if denom > 0 else 0.0


def decision_metrics(severities, actions):
    """Action-to-severity accuracy; the rates below are NOT binary IDS FPR/FNR.

    'false_block_on_low' assumes Low is a label *category*, NOT necessarily benign.
    """
    y, a = list(severities), list(actions)
    if not y or len(y) != len(a):
        raise ValueError("Matched nonempty labels and actions required")
    if any(s not in (0, 1, 2) for s in y) or any(s not in (0, 1, 2) for s in a):
        raise ValueError("Invalid classification codes")
    count = len(y)
    correct = sum(act == ACTION_FOR_SEVERITY[s] for s, act in zip(y, a))
    lows = [act for s, act in zip(y, a) if s == 2]
    highs = [act for s, act in zip(y, a) if s == 0]
    counts = [[sum((s == ss and act == aa) for s, act in zip(y, a))
               for aa in range(3)] for ss in range(3)]
    per_severity = {}
    present_recalls, present_f1 = [], []
    for severity, name in enumerate(SEVERITIES):
        target_action = ACTION_FOR_SEVERITY[severity]
        true_positive = counts[severity][target_action]
        support = sum(counts[severity])
        predicted_as_class = sum(counts[actual][target_action]
                                 for actual in range(3))
        false_positive = predicted_as_class - true_positive
        false_negative = support - true_positive
        recall = _defined_ratio(true_positive, support)
        precision = _defined_ratio(true_positive, predicted_as_class)
        f1 = _defined_ratio(2 * true_positive,
                            2 * true_positive + false_positive + false_negative)
        per_severity[name] = {
            "support": support, "precision": precision,
            "recall": recall, "f1": f1,
        }
        if support:
            present_recalls.append(recall)
            present_f1.append(f1)
    return {
        "n": count,
        "action_success_rate": correct / count,
        "balanced_severity_action_accuracy_present_classes":
            sum(present_recalls) / len(present_recalls),
        "macro_f1_present_severity_classes":
            sum(present_f1) / len(present_f1),
        "per_severity": per_severity,
        "macro_averaging_policy":
            "Present ground-truth severity classes only; missing-class metrics null",
        "false_block_on_low": sum(act == 2 for act in lows) / len(lows) if lows else None,
        "false_allow_on_high": sum(act == 0 for act in highs) / len(highs) if highs else None,
        "severity_action_counts": counts,
    }


def _defined_ratio(top, bottom):
    """Undefined diagnostic rates are None, NEVER a fabricated zero."""
    return top / bottom if bottom else None


def pooled_binary_counts(reports, expected_clients=None):
    """Sum independently audited client confusion counts, refusing mixed lineage.

    reports is a per-client sequence of binary_intrusion_metrics() outputs,
    OR None when original Attack/Benign source evidence is unavailable.
    Partial binary coverage across clients is refused.
    """
    items = list(reports)
    if not items or (expected_clients is not None and len(items) != expected_clients):
        raise ValueError("Expected a complete set of client binary evidence")
    if all(report is None for report in items):
        return None
    if any(report is None for report in items):
        raise ValueError("Partial original binary attack labels across TEST clients")
    totals = {}
    for name in ("TP", "FN", "FP", "TN"):
        values = [record.get(name) if isinstance(record, dict) else None
                  for record in items]
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError("Invalid per-client binary confusion counts")
        totals[name] = sum(values)
    tp, fn, fp, tn = (totals[key] for key in ("TP", "FN", "FP", "TN"))
    if sum(totals.values()) == 0:
        raise ValueError("Empty binary confusion totals")
    return {
        **totals,
        "FPR": _defined_ratio(fp, fp + tn),
        "FNR": _defined_ratio(fn, fn + tp),
        "TPR": _defined_ratio(tp, tp + fn),
        "TNR": _defined_ratio(tn, tn + fp),
        "accuracy": _defined_ratio(tp + tn, tp + tn + fp + fn),
        "precision_attack": _defined_ratio(tp, tp + fp),
        "recall_attack": _defined_ratio(tp, tp + fn),
        "f1_attack": _defined_ratio(2 * tp, 2 * tp + fp + fn),
        "n": tp + fn + fp + tn,
        "binary_attack_prediction_rule": "ALLOW=benign; RATE_LIMIT/BLOCK=attack",
        "requires_raw_label_evidence": True,
    }


def binary_intrusion_metrics(is_attack, actions):
    """Only when raw Attack/Benign provenance exists.

    Action 0 ALLOW predicts benign, actions 1 RATE_LIMIT and 2 BLOCK predict attack.
    Undefined rates (empty positive/negative class) return None, not fabricated zero.
    """
    y, a = list(is_attack), list(actions)
    if not y or len(y) != len(a):
        raise ValueError("Aligned nonempty binary labels and actions required")
    if any(type(z) not in (int, bool) or z not in (0, 1) for z in y):
        raise ValueError("Attack labels must be explicit 0/1 integers")
    if any(type(z) is not int or z not in (0, 1, 2) for z in a):
        raise ValueError("Actions must be 0=ALLOW, 1=RATE_LIMIT or 2=BLOCK")
    TP = sum(z == 1 and p != 0 for z, p in zip(y, a))
    FN = sum(z == 1 and p == 0 for z, p in zip(y, a))
    FP = sum(z == 0 and p != 0 for z, p in zip(y, a))
    TN = sum(z == 0 and p == 0 for z, p in zip(y, a))
    return {
        "TP": TP, "FN": FN, "FP": FP, "TN": TN,
        "FPR": FP / (FP + TN) if FP + TN else None,
        "FNR": FN / (FN + TP) if FN + TP else None,
        "TPR": TP / (TP + FN) if TP + FN else None,
        "TNR": TN / (TN + FP) if TN + FP else None,
        "accuracy": (TP + TN) / (TP + TN + FP + FN),
        "precision_attack": _defined_ratio(TP, TP + FP),
        "recall_attack": _defined_ratio(TP, TP + FN),
        "f1_attack": _defined_ratio(2 * TP, 2 * TP + FP + FN),
        "n": TP + FN + FP + TN,
        "binary_attack_prediction_rule": "ALLOW=benign; RATE_LIMIT/BLOCK=attack",
        "requires_raw_label_evidence": True,
    }
