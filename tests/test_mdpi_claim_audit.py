"""Synthetic tests for manuscript/code evidence audits (stdlib only)."""
import importlib.util
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "analysis" / "audit_mdpi_claims.py"
spec = importlib.util.spec_from_file_location("audit_claims", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

TEMPLATE = r"""
\begin{table}\caption{phase}\label{tab:phase_msr}
CICIoT2023 & B4 (Fuzzy) & $0.9990$ & $1.0000$ & $0.0026$ & $0.0001$ & $0.554$ \\
\end{table}
\begin{table}\caption{lambda}\label{tab:lambda_ablation}
$\mathbf{0.25}^{\star}$ & $\mathbf{0.9995\pm0.0008}$ & $1.0000$ & $0.0143$ & $0.573$ \\
\end{table}
\begin{table}\caption{sweep}\label{tab:lambda_mu_sweep}
$\lambda=0.25, \mu=0.10$ & $0.9990$ & $1.0000$ & $0.0026$ & $0.573$ \\
$\lambda=0.25, \mu=0.05$ & $0.9397$ & $0.9843$ & $0.0045$ & $0.549$ \\
$\lambda=0.25, \mu=0.20$ & $0.9397$ & $0.9843$ & $0.0045$ & $0.549$ \\
\end{table}
"""


class AuditTests(unittest.TestCase):
    def test_detects_conflicting_canonical_values(self):
        ids = {x["id"] for x in mod.audit(TEMPLATE)["findings"]}
        self.assertIn("CANONICAL_TABLE_CONFLICT", ids)
        self.assertIn("LAMBDA_SWEEP_CONFLICT", ids)
        self.assertIn("IDENTICAL_MU_ROWS", ids)

    def test_equal_rows_are_warning_not_misconduct(self):
        a = mod.audit(TEMPLATE)
        issue = next(x for x in a["findings"] if x["id"] == "IDENTICAL_MU_ROWS")
        self.assertEqual(issue["priority"], "warning")

    def test_does_not_invent_when_evidence_missing(self):
        self.assertEqual(mod.audit("no tables")["findings"], [])

    def test_no_false_conflict_when_numbers_match(self):
        fixed = TEMPLATE.replace("0.9995", "0.9990").replace("0.0143", "0.0026")
        ids = {x["id"] for x in mod.audit(fixed)["findings"]}
        self.assertNotIn("CANONICAL_TABLE_CONFLICT", ids)
        self.assertNotIn("LAMBDA_SWEEP_CONFLICT", ids)

    def test_detect_inert_coordination(self):
        src = "def _get_neighbor_actions(self):\n        return None\n"
        ids = {x["id"] for x in mod.audit(TEMPLATE, src)["findings"]}
        self.assertIn("R_LINK_INACTIVE", ids)

    def test_PBRS_zero_expectation_not_assumed(self):
        src = r"\mathbb{E}\bigl[\gamma_{\text{RL}}\Phi(s')-\Phi(s)\bigr]=0"
        ids = {x["id"] for x in mod.audit(src)["findings"]}
        self.assertIn("PBRS_EXPECTATION", ids)


if __name__ == "__main__":
    unittest.main()
