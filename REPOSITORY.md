# NeuroVision AI — Repository Source of Truth

> **Authoritative branch: `main`.** A fresh clone of `main` is the complete, runnable
> NeuroVision product. You do **not** need to understand the historical pull-request stack.
>
> ```bash
> git clone <repo-url> neurovision_ai
> cd neurovision_ai
> git checkout main
> python -m venv .venv && . .venv/bin/activate
> pip install -r requirements.txt          # Python >= 3.11
> python -m scripts.verify_mp4_source_of_truth   # proves the product is present + runs
> uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000
> ```

This document (MP-4 — Source of Truth Consolidation) is **repository governance only**: it
adds no product feature and changes no product behaviour. It records *what the repository is*
and *how to obtain and run the product* — nothing more.

---

## Source Of Truth Guide

- The **single authoritative product state** is the branch **`main`**.
- `main` is a **cumulative, linear** history: every phase from V0 through MP-3 is a commit on
  one spine (no merges, no divergent forks). The tip of `main` *is* the product.
- The historical phase branches and their stacked pull requests (**#21–#51**, plus the merged
  **#15**) are **history**, not separate products. They are preserved for provenance; you never
  need to check any of them out to run NeuroVision.
- If the repository **default branch** still points at `v0/foundation-constitution-architecture`
  (the original constitution/architecture skeleton), it does **not** represent the product.
  Set the default branch to `main` (a one-time maintainer action in the repository settings),
  or merge the MP-4 consolidation pull request into the default branch. Either makes a plain
  `git clone` land on the product.

**How to confirm you are on the source of truth:**
```bash
git rev-parse --abbrev-ref HEAD        # -> main
test -f scripts/verify_mp4_source_of_truth.py && echo "authoritative tree present"
```

---

## Repository Structure Guide

Top-level layout of the authoritative tree (all present and runnable):

| Path | Contents |
|---|---|
| `ml/` | Shared kernel: `lineage` tracker, `ImmutableAuditLog`, `validation`, `provenance`, `version`, determinism, registry, schemas, models, training, uncertainty, benchmarking. |
| `backend/` | **37 governed subsystems** — the product. Notable: `eeg_foundation`, `signal_processing`, `feature_engineering`, `model_foundation`, `inference_foundation`, `application_backend`, **`application_platform`** (the real FastAPI product + `server/`, `provisioning/`, `lifecycle/`, `security/`, `persistence`), `real_model_training`, `serving_platform`, `persistence_platform`, `security_platform`, plus the V2/V3/V4 clinical & operational intelligence layers. |
| `frontend/` | 5 presentation-only frontends (import no domain code — boundary rule). |
| `operations/` | P8 operations foundation (config, deployment assets, health, logging, monitoring, backups, CI). |
| `validation/` | P9 validation & performance-assurance program. |
| `certification/` | P10 deployment-readiness & certification. |
| `scripts/` | Pipeline runners + **42 `verify_*.py`** phase verification scripts. |
| `tests/` | ~90 `test_*.py` modules (full suite green). |
| `.gcc/decisions/` | Architecture Decision Records (ADR-0001 … ADR-0039). |
| `deployment/` | Operator/Docker/compose deployment guide. |
| `requirements.txt`, `pyproject.toml` | Pinned runtime + dev dependencies (Python >= 3.11). |

---

## Repository Reality Report (MP4-A audit, from git)

- Product tip: the head of `main` (the MP-3 commit) — contains **V0 → MP-3** in **44 linear
  commits, 0 merge commits**.
- The original default branch `v0/foundation-constitution-architecture` (`5461e0f`) is an
  **ancestor** of the product tip — the product is **43 commits ahead** of it. Consolidation is
  therefore a pure fast-forward (no conflicts possible).
- Pull requests: **#15 merged** (V3-P1/P2); **#21–#51 open** and stacked cumulatively.
- No tags; no conflict markers in the tree.

### Branch / PR ancestry (the one spine)
```
V0  Constitution + Architecture                      5461e0f
V1  Baseline models / uncertainty / offline / app
V2  Clinical case -> review -> findings -> knowledge -> intelligence -> decision support (cert)
V3  Operational events -> temporal -> workflow -> graph -> analytics -> recommendations (cert)   #15 merged
V4  Goals -> policies -> planning -> tasks -> agents -> execution -> governance -> simulation (cert)
Productization P1..P10  EEG -> signal -> features -> models -> inference -> backend -> frontend
                        -> operations -> validation -> certification                           #24..#33
DRP-1..DRP-6  dataset integration -> production models -> serving -> persistence -> security
              -> clinical validation                                                           #34..#39
Track-1..Track-4  real data -> real model training -> real product app -> operational qual.     #40..#43
DBE-1..DBE-5  ASGI entrypoint -> docker -> duplicate-upload -> persistence wiring -> auth        #44..#48
MP-1  model provisioning foundation                                                             #49
Track-2 data-module fix                                                                         #50
MP-3  persistent model lifecycle & recovery                                                     #51  (product tip)
```

## Product Completeness Report (MP4-C)

Every phase is **COMPLETE** — evidenced by its subsystem code **and** its verification script
existing in the authoritative tree:

| Group | Status | Evidence |
|---|---|---|
| V0–V4 | COMPLETE | `scripts/verify_v1*.py … verify_v4_p9_p10.py` + the clinical/operational/governance `backend/` subsystems |
| Productization P1–P10 | COMPLETE | `verify_productization_p1..p10.py` + `eeg_foundation` … `certification/` |
| DRP-1–DRP-6 | COMPLETE | `verify_drp1..drp6*.py` + `dataset_integration` … `clinical_validation` |
| Track-1–Track-4 | COMPLETE | `verify_track1..track4*.py` + `dataset_acquisition`, `real_model_training`, `application_platform`, `operations_platform` |
| DBE-1–DBE-5 | COMPLETE | `verify_dbe1..dbe5*.py` + `application_platform/server`, deployment assets, persistence wiring, security |
| MP-1, MP-3 | COMPLETE | `verify_mp1_model_provisioning.py`, `verify_mp3_model_lifecycle.py` + `application_platform/provisioning`, `application_platform/lifecycle` |

## Merge Readiness Report (MP4-D)

**Merge-ready.** Linear cumulative history, **0 merge commits**, default branch is an ancestor
of the tip ⇒ fast-forward consolidation with **no conflicts, no dependency violations, and no
duplicate implementations**.

---

## Deployment Branch Guide

| Path | Branch / command |
|---|---|
| **Operator** | `git clone … && git checkout main && pip install -r requirements.txt && uvicorn backend.application_platform.server.app:app` |
| **Developer** | `git checkout main`; create a feature branch **from `main`**; PR back into `main`. |
| **CI** | Run against `main`: `pip install -r requirements.txt` then `pytest -q` and the `scripts/verify_*.py` gates. |
| **Release** | Tag a commit on `main` (e.g. `v1.0.0`); the tag is a frozen, reproducible product snapshot. |

### Operator Onboarding Guide
1. `git clone <repo-url> neurovision_ai && cd neurovision_ai`
2. `git checkout main`
3. `python -m venv .venv && . .venv/bin/activate`
4. `pip install -r requirements.txt`  (Python >= 3.11)
5. `python -m scripts.verify_mp4_source_of_truth`  → expect **ALL CRITERIA PASS**
6. `uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000`
7. `curl http://127.0.0.1:8000/readyz` → `{"ready": true, "model_prepared": true, ...}`

No knowledge of the historical PR stack is required at any step.

### Developer Onboarding Guide
1. Clone + `git checkout main` (the source of truth).
2. `pip install -r requirements.txt` (includes `pytest`, `ruff`).
3. `pytest -q` (full suite) and `ruff check .` must be green.
4. Branch from `main`, implement, add/adjust the relevant `scripts/verify_*.py` gate + tests,
   keep `tests/test_boundaries.py` green, and open a PR **into `main`**.
5. Record significant decisions as an ADR under `.gcc/decisions/`.

---

## Verifying repository truth

```bash
python -m scripts.verify_mp4_source_of_truth      # 15 MP-4 criteria
python -m pytest tests/test_mp4_source_of_truth.py
```

Decision record: `.gcc/decisions/ADR-0039-mp4-source-of-truth-consolidation.md`.
