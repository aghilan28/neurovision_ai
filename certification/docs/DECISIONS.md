# Production Certification — Key Decisions (Productization P10)

See `.gcc/decisions/ADR-0023-productization-p10-deployment-certification.md` for the full ADR.

1. **`certification/` is a top-level certification layer (peer of `scripts/`/`operations/`/
   `validation/`).** It audits P1–P9 and modifies nothing. It imports `backend`/`operations`/
   `validation` lazily; no domain package imports it (asserted). Evaluation/certification-only,
   one-way.

2. **One evidence bundle, collected once.** Every audit, scorecard, risk, gap, and the final
   decision consume the same `EvidenceCollector` output, so the certification is internally
   consistent and reproducible.

3. **The decision is a pure function of the evidence.** Deterministic rules render exactly
   one verdict; re-deriving from the same bundle yields the same signature. No assumptions,
   no optimism, no future promises.

4. **CONDITIONALLY CERTIFIED is the honest verdict.** The technical foundation is fully met
   and nothing blocks a non-clinical deployment, but disclosed clinical-production conditions
   (G1 real data + tuned models, G3 durable persistence, security hardening, clinical
   validation) remain — so the engine returns CONDITIONALLY CERTIFIED with the conditions
   enumerated, scoped GO for non-clinical / NO-GO for unconditioned clinical production.

5. **Accuracy is evidence, not a gate.** Readiness gates on correctness, determinism,
   calibration validity, traceability, and operational readiness; the untuned reference
   baselines' accuracy is reported, never gated on.

6. **Risk/gap recommendations only.** Risk mitigations and gap remediations are
   *recommended*; none is implemented (P10 forbids changes).

## Inherited gaps (carried forward, disclosed — not introduced by P10)

* **G1** synthetic-data lineage / untuned models, **G2** unmechanized governance, **G3**
  in-memory persistence. P10 reports them as conditions; it does not resolve them (out of
  scope).
