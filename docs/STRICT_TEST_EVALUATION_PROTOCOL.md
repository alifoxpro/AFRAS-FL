# Strict TEST — one-time frozen evaluation for the NEW experimental protocol

Scientific status: this command has NOT been executed on CICIoT2023 or DIAD2024.
The public repository contains neither the original processed datasets nor
strict Stage 3 teacher / Stage 4 policy checkpoints.

## Required before opening TEST

1. Audit how 14 features and High/Medium/Low labels were constructed from raw datasets.
2. Verify that source rows are meaningfully ordered and that device/session/campaign
   leakage has been excluded. A 19-record embargo alone is not sufficient.
3. Generate the strict split manifest, train Mamba teachers from TRAIN with
   VAL-based checkpoint selection, and train B2/B3/B4 policies from TRAIN
   with VAL-based checkpoint selection.
4. Freeze all three predeclared policies and document the intended comparisons.
5. Confirm the TRAIN-fitted scalers, Stage 3 teacher provenance, Stage 4
   provenance, split manifest and TEST hashes are all consistent.
6. Only then, execute the one-time unsealing command.

## Command (only when experiments are complete and frozen)

    python scripts/evaluation/evaluate_strict_test.py --dataset ciciot2023 --seed 42 --unseal-test

The runner rejects accidental TEST access unless --unseal-test is supplied.
It rejects PILOT or subsampled models, changed teacher/scaler/policy hashes,
changed split manifest, or changed TEST CSVs.

## Output

Saved in experiments/strict_test_eval/<dataset>/seed_<seed>/ :

- TEST_UNSEAL_RECEIPT.json: written BEFORE inference, marks attempt begun.
- TEST_RESULTS.json: all five clients and all three predeclared policies,
  including 3x3 severity-to-action confusion matrices, action-success and
  Jain fairness of action success.
- TEST_PER_CLIENT.csv: per-client action success and specific action error rates.
- TEST_REPORT.md: readable pooled comparison and cautions.

Output directories are never overwritten. If execution fails after TEST was
opened, retain the receipt and disclose the interrupted attempt. Never conceal
it by deleting the receipt and claiming a repeat is the first untouched test.

## Scientific limitations

- This is a distinct contextual-bandit experiment with gamma=0, NOT the
  historical AFRAS-FL paper's originally reported result protocol.
- Unverified original severity labels cannot justify naming these metrics
  conventional binary IDS FPR/FNR. Low does not necessarily equal benign.
- Neighbor R_link has not been implemented; mu_link must equal zero.
- Upstream feature selection/group overlap/preprocessing may still leak.
- Selection or tuning informed by this TEST invalidates its status as untouched.
- GitHub Actions unit tests check only Python syntax and synthetic guards;
  they do not reproduce a GPU training run or establish deployment readiness.
