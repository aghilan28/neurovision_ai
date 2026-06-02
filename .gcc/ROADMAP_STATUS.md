# ROADMAP STATUS

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — updated when the plan/critical path changes.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Update when programs/workstreams/epics/phases or the critical path change; log it ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P4
> **Companions:** [`VERSION_STATUS.md`](./VERSION_STATUS.md), [`NEXT_STATE.md`](./NEXT_STATE.md)

Tracks the work breakdown: **Programs → Workstreams → Epics → Phases →
Deliverables**, their **dependencies**, and the **critical path**. It is the
planning view; [`VERSION_STATUS.md`](./VERSION_STATUS.md) is the maturity view.

---

## 1. Programs (long-lived streams of work)

| ID | Program | Spans | Purpose |
|----|---------|-------|---------|
| **PROG-FND** | Foundation & Governance | V0 (ongoing upkeep V0→V4) | Constitution, architecture, governance, AI OS. |
| **PROG-DSP** | Signal Processing | V1→V4 | Deterministic EEG preprocessing. |
| **PROG-DATA** | Data & Curation | V1→V4 | Patient-level, leakage-safe data access. |
| **PROG-ML** | Modeling & Uncertainty | V1→V4 | Detection of SZ/IIC with calibrated UQ. |
| **PROG-EVAL** | Validation | V1→V4 | Patient-disjoint evaluation, calibration, domain-shift. |
| **PROG-APP** | Application & Workflow | V2→V4 | Backend services + clinician workflow. |
| **PROG-RT** | Real-Time & Ops | V3→V4 | Streaming, monitoring, deployment, reliability. |

## 2. Workstreams → Epics → Phases (current + near-term)

### PROG-FND (Foundation & Governance) — **active**
| Workstream | Epic | Phase | Deliverables | Status |
|------------|------|-------|--------------|--------|
| Constitution | Constitution Layer | V0-P1 | vision/objectives/scope/versions/principles/rules/glossary | ✅ |
| Architecture | Repo Architecture | V0-P2 | tree + per-dir READMEs + 5 architecture docs | ✅ |
| Governance | Governance Framework | V0-P3 | 10 governance docs + index | ✅ |
| AI OS | Operating System | V0-P4 | state/registers/protocols/templates/checklists | ⏳ |
| Enforcement | GCC Automation | V0→V1 | CI checks for imports/boundaries/acyclicity + doc consistency | ⬜ next |

### PROG-DSP / PROG-DATA / PROG-EVAL / PROG-ML (V1) — **not started (blocked on V0 gate)**
| Program | First epic | Deliverables | Status |
|---------|-----------|--------------|--------|
| PROG-DSP | Deterministic preprocessing | filters/montage/windowing/normalization + determinism tests | ⬜ |
| PROG-DATA | Patient-indexed access | catalog + LOSO split generation | ⬜ |
| PROG-EVAL | Patient-disjoint harness | LOSO runner + calibration/coverage + shift eval | ⬜ |
| PROG-ML | Baseline detection + UQ | SZ/IIC model + conformal prediction + abstain | ⬜ |

(V2/V3/V4 epics are enumerated in [`VERSION_STATUS.md`](./VERSION_STATUS.md) and the
version model; they are intentionally not expanded until their prerequisites near.)

## 3. Dependencies (high level)
```
PROG-FND (V0 gate) ─► everything
PROG-DSP ─► PROG-DATA ─► PROG-ML ─► PROG-EVAL ─► PROG-APP ─► PROG-RT
(build order is leaf-first, mirroring the acyclic dependency graph)
```
Detailed dependencies: [`DEPENDENCY_REGISTRY.md`](./DEPENDENCY_REGISTRY.md).

## 4. Critical Path (today)
```
finish V0-P4  ─►  wire GCC automation  ─►  V0 exit gate (ADR)  ─►  V1: preprocessing
   (now)            (next tooling)          (NR-12 gate)            (first V1 code)
```
The single most important near-term item is the **V0 exit gate**: nothing in V1
may claim completion before it (NR-12). The most important *enabling* item is **GCC
automation**, so that V1 code is governed mechanically from its first commit.

## 5. How To Update This File
When scope or sequencing changes: update the program/workstream tables, re-draw the
critical path, and log the change. Keep deliverables **concrete and verifiable**.
