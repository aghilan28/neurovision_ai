# ADR-0039 — MP-4: Source of Truth Consolidation

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Model Provisioning Program — MP-4
> **Builds on:** ADR-0001 … ADR-0038 (V0 … MP-3)
> **Resolves:** Repository-governance risk — *the product lives on the tip of a deep stacked-PR
> chain; the default branch does not represent the product; the source of truth is not obvious
> to an independent operator*
> **Enforces / honors:** AP-9/NR-5 (this record), NR-2 (honesty), NR-13 (scope — governance only)

## 1. Context (audited from git, not reports)

- The repository default branch (`origin/HEAD`) is **`v0/foundation-constitution-architecture`**
  (`5461e0f`) — the original constitution/architecture **skeleton**.
- The actual product is the tip of a **linear, cumulative** history: **44 commits, 0 merge
  commits**, V0 → … → MP-3 (`85a8b05`). The product is **43 commits ahead** of the default
  branch, and the default branch is a clean **ancestor** of the product tip.
- Pull requests: **#15 merged** (V3-P1/P2); **#21–#51 open** and stacked cumulatively.
- Consequence: a plain `git clone` lands on the V0 skeleton, not the product. The source of
  truth is not discoverable without knowledge of the historical PR stack.

This is **not** a product-building phase. MP-4 establishes *repository truth* only — it adds no
feature and changes no product behaviour.

## 2. Decisions

### D1 — `main` is the single authoritative product branch
The authoritative source of truth is the branch **`main`**, created at the product tip
(V0 → MP-3) plus this governance commit. A fresh clone of `main` is the complete, runnable
product. The historical phase branches / PRs are preserved as provenance but are never required
to obtain or run NeuroVision.

### D2 — Consolidation is a fast-forward (no merge, no conflicts)
Because the history is linear and the default branch is an ancestor of the tip, no merge or
conflict resolution is required: `main` *is* the existing spine. A consolidation pull request
is opened **`main → v0/foundation-constitution-architecture`** so a maintainer merge makes the
**default branch carry the full product** (zero hidden-branch knowledge for operators).

### D3 — Repository self-describes its truth (`REPOSITORY.md`)
A root `REPOSITORY.md` documents the source of truth, structure, branch topology, the MP4-A…D
audit reports (reality / topology / completeness / merge-readiness), and the deployment +
operator/developer onboarding guides — so the repository explains itself with no external
context.

### D4 — Objective, reproducible verification
`scripts/verify_mp4_source_of_truth.py` (15 criteria) audits git reality, confirms completeness,
performs a **real local fresh clone**, and **runs the product from that clone** (`/readyz`
ready=true), then asserts the MP-4 change set is governance-only. `tests/test_mp4_source_of_truth.py`
adds filesystem/import/repo-integrity tests.

## 3. Consequences

- `python -m scripts.verify_mp4_source_of_truth` → **ALL 15 CRITERIA PASS**.
- The change set is **governance-only**: `REPOSITORY.md`, `scripts/verify_mp4_source_of_truth.py`,
  `tests/test_mp4_source_of_truth.py`, this ADR, and the decisions index. **No** file under
  `ml/ backend/ frontend/ operations/ validation/ certification/` is modified — the product is
  byte-for-byte unchanged (verified by `diff-tree` + a green `tests/test_boundaries.py` and the
  fresh-clone product run).
- Full test suite remains green; no new dependencies.

## 4. Limitation (honest — NR-2)

Setting the GitHub **default branch** to `main` is a repository-settings action performed by a
maintainer (not available to the agent via the API). MP-4 therefore (a) creates the clearly
named authoritative `main` branch, (b) opens the consolidation PR into the current default so
merging it puts the product on the default branch, and (c) documents both paths in
`REPOSITORY.md`. After either action, a plain clone yields the product. No product code is
changed by MP-4.

## 5. Scope guard (explicitly NOT done — NR-13)

No new features, no model retraining, no dataset/inference/model-architecture changes, no
deployment/security/operations-architecture changes, and no new roadmap phases. Repository
truth and consolidation only.
