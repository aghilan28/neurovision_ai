# ADR-0023 — Productization P10: Deployment Readiness & Production Certification

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P10 (final productization phase)
> **Builds on:** ADR-0001 … ADR-0022 (the full P1–P9 productization stack)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), AP-9/NR-5 (this record), NR-2 (zero hidden debt), NR-12 (honest
> certification / version gating), NR-13 (scope)
> **Decision owner:** Platform/certification engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P10 **Deployment Readiness & Production Certification
Program** (`certification/`) is shaped as it is, and records the resulting verdict, so the
rationale survives turnover (NR-14).

---

## 1. Context

P1–P9 produced a validated product. P10 answers the final question — *can NeuroVision be
deployed?* — with an honest, evidence-based certification. The scope is **certification
only**: no new capability, no new architecture, no new workflows, no infrastructure changes
(NR-13).

## 2. Decisions

### D1 — A top-level `certification/` layer (peer of `scripts/`/`operations/`/`validation/`)
Certification **audits** P1–P9 and modifies nothing. It is not a governed domain package, so
the per-module import DAG does not constrain it; it imports `backend`/`operations`/
`validation` lazily. One-way: **no domain package imports `certification`** (asserted).

### D2 — One evidence bundle, collected once
`EvidenceCollector` runs the platform once (the P9 validation program + the end-to-end
journey + the P8 operations health/validation/deployment/config + compliance) and every
audit/scorecard/risk/gap/decision consumes that single bundle — so the certification is
internally consistent and reproducible.

### D3 — The decision is a pure, deterministic function of the evidence
The decision engine (P10-I) applies fixed rules to render exactly one verdict (CERTIFIED /
CONDITIONALLY CERTIFIED / NOT CERTIFIED) with a go/no-go recommendation, scope, conditions,
and citations of readiness/risks/gaps/validation/operations/deployment. Re-deriving from the
same evidence yields the same signature.

### D4 — Accuracy is evidence, not a gate; risk/gap recommendations only
Readiness gates on correctness, determinism, calibration validity, traceability, and
operational readiness. The untuned reference baselines' accuracy is reported, never gated on.
Risk mitigations and gap remediations are *recommended*; none is implemented (P10 forbids
changes).

## 3. The verdict (recorded)

**CONDITIONALLY CERTIFIED — GO (conditional).** The technical foundation is fully met
(end-to-end 10/10, validation complete, operations green, deterministic, traceable) and no
gap blocks a non-clinical deployment, so it is not NOT CERTIFIED. Disclosed conditions remain
before unconditioned clinical production, so it is not unconditionally CERTIFIED:

1. Real clinical data + re-validation (G1) — RISK-DATA-01 / GAP-DATA.
2. Tuned production models on a clinical benchmark (G1) — RISK-MODEL-01.
3. Durable persistence (G3) — RISK-DEPLOY-01 / GAP-PERSIST.
4. Production security hardening + injected secrets — GAP-SECHARD / security_readiness.
5. Formal clinical validation — GAP-CLINICAL.

**Scope:** GO for non-clinical / research / engineering deployment under the conditions;
NO-GO for unconditioned clinical production until they are closed. The full record is in
`certification/docs/CERTIFICATION_REPORT.md`.

## 4. Consequences

- `python -m scripts.verify_productization_p10` exercises all 15 criteria (**ALL PASS**) and
  emits the verdict; it is reproducible (a second run yields the same verdict + signature).
- The new suite adds 12 tests; the full repository suite is **836 passed** (was 824). `ruff`
  is clean on all new code; `tests/test_boundaries.py` stays green; no domain package imports
  `certification`.
- No new runtime dependencies; certification runs in isolated temp workspaces and changes no
  repository state.

## 5. Scope guard (explicitly NOT built — NR-13)

New models, model retraining, frontend/backend/infrastructure/deployment/monitoring/security
changes, Version 5, any new productization phase.

## 6. Honesty statement (NR-2 / NR-12)

The verdict uses no assumptions, no optimism, and no future promises. The measured model
accuracies are evidence about untuned reference baselines on synthetic data (G1) — not a
clinical-performance claim. The inherited gaps G1/G2/G3 are carried forward and disclosed as
conditions; P10 does not resolve them (out of scope).
