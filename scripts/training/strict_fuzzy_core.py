"""Strict TRAIN-only, SAME-SCALE fuzzy rule fitting and inference.

A NEW transparent nine-cell Gaussian rule protocol, not the historical
7-phase denoise / NURBS-SMOTE pipeline. In particular, membership functions
are fitted directly to Stage 3 TRAIN-standardized two-feature state
coordinates; the very same coordinates are presented at inference.

No VAL/TEST inputs, secondary scaler, time-series wavelet filter, source
label inference, or synthetic oversampling is used here.
"""
import math
from collections import Counter

SCHEMA = "afras-strict-train-only-raw-scale-fuzzy-v1"
SETS = ("Low", "Medium", "High")
ACTIONS = ("ALLOW", "RATE_LIMIT", "BLOCK")
ACTION_FOR_SEVERITY = (2, 1, 0)


def _quantile(values, frac):
    values = sorted(values)
    if not values:
        raise ValueError("Cannot compute quantiles for empty training data")
    position = (len(values) - 1) * frac
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    return values[lo] * (1 - (position-lo)) + values[hi] * (position-lo)


def _membership(value, center, width):
    return math.exp(-0.5 * ((value - center) / width) ** 2)


def fit_train_only_rules(states, labels, feature_names, min_support=10,
                         min_confidence=0.50):
    """Fit deterministic rules from TRAIN ONLY, returning JSON-safe package."""
    x = [tuple(float(v) for v in row) for row in states]
    y = []
    for z in labels:
        try:
            value = float(z)
        except (TypeError, ValueError) as exc:
            raise ValueError("Unknown TRAIN severity class") from exc
        if isinstance(z, bool) or not math.isfinite(value) or value not in (0.0, 1.0, 2.0):
            raise ValueError("Unknown TRAIN severity class")
        y.append(int(value))
    if len(x) != len(y) or not x:
        raise ValueError("Aligned nonempty TRAIN states and severity labels required")
    if not isinstance(feature_names, (tuple, list)) or len(feature_names) != 2:
        raise ValueError("Exactly two named state features required")
    if len(set(feature_names)) != 2 or not all(
            isinstance(n, str) and n and not n.startswith("__")
            for n in feature_names):
        raise ValueError("Nonempty distinct feature names required")
    if any(len(row) != 2 or not all(math.isfinite(v) for v in row) for row in x):
        raise ValueError("Two finite feature values per TRAIN state required")
    if any(z not in (0, 1, 2) for z in y):
        raise ValueError("Unknown TRAIN severity class")
    if type(min_support) is not int or min_support < 1:
        raise ValueError("min_support must be positive integer")
    if not math.isfinite(float(min_confidence)) or not 0 < min_confidence <= 1:
        raise ValueError("min_confidence must be within (0,1]")
    params = {}
    for dim, name in enumerate(feature_names):
        values = [row[dim] for row in x]
        low, mid, high = (_quantile(values, q) for q in (0.1, 0.5, 0.9))
        span = high - low
        if span <= 1e-12:
            low, high = min(values), max(values)
            span = high - low
        if span <= 1e-12:
            raise ValueError(f"Constant/non-informative TRAIN feature {name}")
        width = max(span * .45, 1e-8)
        params[name] = {
            set_name: {"center": float(center), "width": float(width)}
            for set_name, center in zip(SETS, (low, mid, high))
        }
    cells = {}
    for row, z in zip(x, y):
        antecedent = []
        for dim, name in enumerate(feature_names):
            degrees = [_membership(row[dim], params[name][s]["center"],
                                   params[name][s]["width"]) for s in SETS]
            antecedent.append(max(range(3), key=lambda i: degrees[i]))
        key = tuple(antecedent)
        cells.setdefault(key, Counter())[z] += 1
    rules = []
    for key in sorted(cells):
        counts = cells[key]
        total = sum(counts.values())
        severity = min((0, 1, 2), key=lambda z: (-counts[z], z))
        conf = counts[severity] / total
        if total < min_support or conf < min_confidence:
            continue
        action = ACTION_FOR_SEVERITY[severity]
        rules.append({
            "rule_id": len(rules),
            "antecedents": [[feature_names[i], SETS[key[i]]] for i in range(2)],
            "consequent": ACTIONS[action],
            "consequent_action": action,
            "confidence": float(conf),
            "support": total,
            "severity": severity,
        })
    if not rules:
        raise ValueError(
            "No adequately supported TRAIN-only fuzzy rules; do not fit on VAL/TEST "
            "to make rules appear")
    return {
        "schema": SCHEMA,
        "feature_names": list(feature_names),
        "membership_params": params,
        "rules": rules,
        "n_rules": len(rules),
        "n_train": len(y),
        "min_support": min_support,
        "min_confidence": float(min_confidence),
        "partition": "TRAIN",
        "feature_scale": "stage3_train_standardized_window_means_no_extra_fit",
        "no_wavelet_or_synthetic_oversampling": True,
        "source_semantics": "new strict protocol; NOT historic seven-phase fuzzy",
    }


def infer_rule(package, feature_values):
    """Score on exactly the same state scale on which rules were fitted."""
    if not isinstance(package, dict) or package.get("schema") != SCHEMA:
        raise ValueError("Unrecognized strict fuzzy package")
    vals = [float(v) for v in feature_values]
    if len(vals) != 2 or any(not math.isfinite(v) for v in vals):
        raise ValueError("Expected two finite strict fuzzy state coordinates")
    names = package["feature_names"]
    params = package["membership_params"]
    best_action, best_strength = None, 0.0
    for rule in package["rules"]:
        firing = float(rule["confidence"])
        for dimension, (name, set_name) in enumerate(rule["antecedents"]):
            if name != names[dimension] or set_name not in SETS:
                raise ValueError("Rule feature alignment differs from trained state")
            p = params[name][set_name]
            firing *= _membership(vals[dimension], p["center"], p["width"])
        if firing > best_strength:
            best_action, best_strength = rule["consequent_action"], firing
    if best_action is None:
        return None, 0.0
    if best_action not in (0, 1, 2) or not 0 <= best_strength <= 1 + 1e-12:
        raise ValueError("Invalid fuzzy inference output")
    return best_action, min(1.0, float(best_strength))
