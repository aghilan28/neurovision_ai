# V3 Risk Review

> **Document type:** Certification (V3) · **Status:** Issued
> **Companion:** `V3_GAP_ANALYSIS.md` (gaps), `V3_COMPLETION_REPORT.md` (verdict).

A formal risk assessment for Version 3. Each risk has a likelihood, an impact, the
controls in place, and a residual rating. Risks are tracked across versions; the
inherited ones (R1/R3/R4) carry forward from V1/V2 unchanged.

---

## 1. Risk register

| ID | Risk | Likelihood | Impact | Controls in place | Residual |
|----|------|-----------|--------|-------------------|----------|
| **R1** | **Synthetic→real gap** — intelligence validated only on synthetic operation may not reflect real-EEG-driven operation. | High (until real EEG) | High (clinical validity) | Scope guard: V3 claims operational scope only; G1 disclosed. | Medium (bounded by scope) |
| **R2** | **Recommendation over-reliance** — an operator treats an operational suggestion as an instruction. | Medium | Medium | Suggestions only; evidence + analytics links shown; escalation is candidate-only; explicit framing in the workspace. | Low |
| **R3** | **Unmechanized governance** — a boundary/scope violation lands because the `.gcc/` gate is not in CI. | Medium | Medium | `tests/test_boundaries.py` fails the build on a forbidden import; ADRs record scope. | Low–Medium |
| **R4** | **In-memory persistence** — process loss drops registries/audit/lineage; no durable replay. | Medium | Medium (operational), Low (correctness) | Determinism: artifacts regenerate byte-identically from inputs. | Low–Medium |
| **R5** | **Analytics misread as truth** — a derived analytic is treated as a source of truth. | Low | Medium | Gate's risk dimension forbids non-derived analytics; lineage parents are upstream nodes; framed as derived. | Low |
| **R6** | **Presentation drift** — the workstation shows a value not backed by a registered artifact. | Low | Medium | Import-pure presentation; six consistency checks; `visualization_consistency` rejects dangling refs. | Low |
| **R7** | **Determinism regression** — a future change introduces wall-clock/randomness. | Low | High (reproducibility) | Logical clock everywhere; determinism + reproducibility tests; no wall-clock in production code. | Low |

## 2. Risk categories (directive coverage)

- **Architecture risks** — boundary erosion (R3, R6): controlled by enforced DAG + tests.
- **Workflow / Graph risks** — hidden state / graph-only truth: structurally prevented (derived-only; ontology-validated).
- **Analytics risks** — analytics-as-truth (R5): prevented by the governance gate.
- **Recommendation risks** — over-reliance / autonomous action (R2): suggestions only, no execution, no auto-escalation.
- **Audit / Lineage risks** — broken chains: every chain `verify()`/`verify_chain()`s in tests + snapshot.
- **Governance risks** — unmechanized enforcement (R3): the one open governance risk.

## 3. Open / resolved / unknown / future risks

- **Open:** R1, R3, R4 (inherited foundational); tracked toward V4 entry.
- **Resolved (by design):** R5, R6 (structural controls), R2 (framing + candidate-only escalation).
- **Unknown:** real-world operational-load behavior (no streaming in V3 scope) — to be assessed when V4 introduces real-time.
- **Future:** scaling the graph/analytics to large populations; durable multi-run lineage.

## 4. Risk verdict

No risk is **unmitigated-and-blocking**. The high-impact risk (R1) is bounded by an
explicit scope guard (V3 makes no clinical claim). The QUALIFIED certification is
consistent with this risk posture; unqualified CERTIFIED requires retiring R1/R3/R4.
