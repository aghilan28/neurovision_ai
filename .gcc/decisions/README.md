# `.gcc/decisions/` — Decision Records (ADRs)

> **Layer:** Governance & Context Control (GCC)
> **Governs:** AP-9 (versioned decisions), NR-5 (no architecture change without a
> recorded decision), NR-14 (Lore Protocol)

This directory holds the project's **Architecture/Method Decision Records** — the
versioned, dated rationale for consequential decisions, with alternatives
considered. A decision record exists so that *why* a thing was built survives
contributor and AI-agent turnover.

| ADR | Title | Phase | Status |
|-----|-------|-------|--------|
| [ADR-0001](./ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md) | V1-P5 Baseline Model Layer + V1-P6 Uncertainty & Calibration Layer | V1-P5 / V1-P6 | Accepted |
| [ADR-0002](./ADR-0002-v1-p7-p8-offline-inference-and-research-app.md) | V1-P7 Offline Inference Platform + V1-P8 Offline Research Application | V1-P7 / V1-P8 | Accepted |
| [ADR-0003](./ADR-0003-v2-p1-p2-clinical-case-and-review.md) | V2-P1 Clinical Case Foundation + V2-P2 Clinical Review Workflow | V2-P1 / V2-P2 | Accepted |
| [ADR-0004](./ADR-0004-v2-p3-p4-findings-and-knowledge.md) | V2-P3 Findings & Interpretation Layer + V2-P4 Clinical Knowledge Layer | V2-P3 / V2-P4 | Accepted |
| [ADR-0005](./ADR-0005-v2-p5-p6-intelligence-and-decision-support.md) | V2-P5 Multi-Case Intelligence Layer + V2-P6 Decision Support Layer | V2-P5 / V2-P6 | Accepted |
| [ADR-0006](./ADR-0006-v2-p7-p8-workstation-and-certification.md) | V2-P7 Clinical Workstation + V2-P8 Version 2 Certification | V2-P7 / V2-P8 | Accepted |
| [ADR-0007](./ADR-0007-v3-p1-p2-events-and-temporal.md) | V3-P1 Operational Event Foundation + V3-P2 Temporal Intelligence Layer | V3-P1 / V3-P2 | Accepted |
| [ADR-0008](./ADR-0008-v3-p3-p4-workflow-and-graph.md) | V3-P3 Workflow Intelligence Layer + V3-P4 Operational Knowledge Graph | V3-P3 / V3-P4 | Accepted |
| [ADR-0009](./ADR-0009-v3-p5-p6-analytics-and-recommendations.md) | V3-P5 Operational Analytics Layer + V3-P6 Operational Recommendation Layer | V3-P5 / V3-P6 | Accepted |
| [ADR-0010](./ADR-0010-v3-p7-p8-workstation-and-certification.md) | V3-P7 Operational Intelligence Workstation + V3-P8 Version 3 Certification | V3-P7 / V3-P8 | Accepted |
| [ADR-0011](./ADR-0011-v4-p1-p2-goals-and-policies.md) | V4-P1 Goal Intelligence Foundation + V4-P2 Policy & Constraint Engine | V4-P1 / V4-P2 | Accepted |
| [ADR-0012](./ADR-0012-v4-p3-p4-planning-and-tasks.md) | V4-P3 Planning Foundation + V4-P4 Task Intelligence Layer | V4-P3 / V4-P4 | Accepted |
| [ADR-0013](./ADR-0013-v4-p5-p6-agents-and-execution.md) | V4-P5 Agent Coordination Framework + V4-P6 Execution Orchestration Layer | V4-P5 / V4-P6 | Accepted |
| [ADR-0014](./ADR-0014-productization-p1-real-eeg-foundation.md) | Productization P1 — Real EEG Foundation Layer | Productization P1 | Accepted |
| [ADR-0015](./ADR-0015-productization-p2-signal-processing.md) | Productization P2 — Signal Processing Foundation | Productization P2 | Accepted |
| [ADR-0016](./ADR-0016-productization-p3-feature-engineering.md) | Productization P3 — Feature Engineering Platform | Productization P3 | Accepted |
| [ADR-0017](./ADR-0017-productization-p4-model-foundation.md) | Productization P4 — Model Foundation Platform | Productization P4 | Accepted |
| [ADR-0018](./ADR-0018-productization-p5-clinical-inference.md) | Productization P5 — Clinical Inference Foundation | Productization P5 | Accepted |
| [ADR-0019](./ADR-0019-productization-p6-application-backend.md) | Productization P6 — Application Backend Platform | Productization P6 | Accepted |
| [ADR-0020](./ADR-0020-productization-p7-application-frontend.md) | Productization P7 — Application Frontend Platform | Productization P7 | Accepted |
| [ADR-0021](./ADR-0021-productization-p8-operations-foundation.md) | Productization P8 — Operations Foundation Platform | Productization P8 | Accepted |
| [ADR-0022](./ADR-0022-productization-p9-validation-assurance.md) | Productization P9 — Validation & Performance Assurance Program | Productization P9 | Accepted |
| [ADR-0023](./ADR-0023-productization-p10-deployment-certification.md) | Productization P10 — Deployment Readiness & Production Certification | Productization P10 | Accepted |
| [ADR-0024](./ADR-0024-drp1-real-dataset-integration.md) | DRP-1 — Real Dataset Integration Program | Deployment Remediation DRP-1 | Accepted |
| [ADR-0025](./ADR-0025-drp2-production-models.md) | DRP-2 — Production Model Program | Deployment Remediation DRP-2 | Accepted |
| [ADR-0026](./ADR-0026-drp3-serving-platform.md) | DRP-3 — Production Serving Platform | Deployment Remediation DRP-3 | Accepted |
| [ADR-0027](./ADR-0027-drp4-persistence-platform.md) | DRP-4 — Persistence Platform | Deployment Remediation DRP-4 | Accepted |
| [ADR-0028](./ADR-0028-drp5-security-platform.md) | DRP-5 — Security Hardening & Access Control Platform | Deployment Remediation DRP-5 | Accepted |
| [ADR-0029](./ADR-0029-drp6-clinical-validation.md) | DRP-6 — Clinical Validation & Evidence Platform | Deployment Remediation DRP-6 | Accepted |
| [ADR-0030](./ADR-0030-track1-real-data-acquisition.md) | Track 1 — Real Data Acquisition & Integration Program | Product Completion Track 1 | Accepted |
| [ADR-0031](./ADR-0031-track2-real-model-training.md) | Track 2 — Real Model Training & Benchmark Program | Product Completion Track 2 | Accepted |
| [ADR-0032](./ADR-0032-track3-real-product-application.md) | Track 3 — Real Product Application Program | Product Completion Track 3 | Accepted |

A change to architecture, boundaries, or method requires a new (or amended) ADR
before/with the change (NR-5).
