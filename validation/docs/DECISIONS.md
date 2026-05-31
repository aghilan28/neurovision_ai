# Validation & Performance Assurance — Key Decisions (Productization P9)

See `.gcc/decisions/ADR-0022-productization-p9-validation-assurance.md` for the full ADR.

1. **`validation/` is a top-level evaluation layer (peer of `scripts/`/`operations/`).** It
   measures P1–P8 and modifies nothing. It may import `backend`/`operations` (lazily); no
   domain package imports it (asserted). Evaluation-only, one-way.

2. **Deterministic evidence vs informational performance.** Fingerprints / success counts /
   metric values / readiness scores are deterministic and signed; wall-clock latency /
   throughput / memory are informational and never hashed. Verdicts reproduce; timings are
   still reported.

3. **Reuse existing metrics — reimplement nothing.** Model metrics come from the P4
   evaluation engine; calibration/uncertainty come from P4 (ECE/Brier) + the P5 inference
   asset; the pipeline is the real P1–P5 pipeline. Validation orchestrates and reads.

4. **"Do not retrain" is honored.** The platform has no persisted weights — a model *is*
   its deterministic reconstruction (P4/P5). Validation invokes the existing deterministic
   P4 training to obtain each baseline's evaluation; it introduces no new training regime,
   no tuning, and no new models.

5. **Accuracy is evidence, not a gate.** The four baselines are deterministic untuned
   reference models (P4). Their accuracy is reported in the executive summary; readiness
   gates on correctness, determinism, calibration validity, and traceability instead.

6. **Drift is measured, never corrected (P9-H).** The drift module quantifies change and
   reports it; it performs no correction.

7. **Robustness = graceful handling.** The platform must never crash on bad input; it must
   return a structured outcome (rejected/quarantined) and recover for the next input. The
   robustness suite asserts exactly that.

## Inherited gaps (unchanged, disclosed)

* **G1 (synthetic-data lineage):** validation runs on the committed deterministic EEG
  fixtures; the measured accuracy figures are evidence about the reference baselines on that
  data, not a clinical performance claim.
* **G3 (in-memory persistence):** unchanged; validation uses isolated temp workspaces.
