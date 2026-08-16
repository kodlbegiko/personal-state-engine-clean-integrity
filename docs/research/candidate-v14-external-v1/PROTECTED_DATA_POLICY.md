# Protected Data Policy

Historical EV-v4 case-level payloads are prohibited. Candidate-v14 development and internal-holdout examples are prohibited. Protected generation must not inspect Candidate-v14 predictions.

The protected corpus and answer key are frozen before inference, hashed independently, and never edited after formal start. Predictions are written once, hashed immediately, and scoring is downstream-only.

After formal evaluation begins: no candidate changes, threshold changes, protected-set edits, answer-key edits, case-level debugging, failure-driven patching, or formal rerun.

A second attempted formal run must detect the branch-level formal-run lock and exit before importing or invoking Candidate-v14.
