# FINAL CERTIFICATION REPORT

Certification decision: `NOT CERTIFIED`

Decision basis: runtime audit evidence collected in `certification_evidence_20260601_211116/`.

This was an audit-only execution. No code, tests, configuration, datasets, or existing reports were modified.

## Repository Truth

Status: `FAIL`

Evidence:

- `certification_evidence_20260601_211116/phase01_repository_truth.txt`

Runtime facts:

- Current branch: `main`
- Current commit: `923443b9f58acf7247b1bac14249f4611d76e51f`
- `origin/main`: `923443b9f58acf7247b1bac14249f4611d76e51f`
- `origin/HEAD`: `refs/remotes/origin/main`
- HEAD matches `origin/main`: `true`
- Repository clean: `false`

Observed dirty working tree:

```text
 M validation/benchmarking/__init__.py
 M validation/harness.py
 M validation/util.py
?? REAL_CORPUS_FAILURE_REPORT.md
?? REAL_CORPUS_REMEDIATION_REPORT.md
?? REAL_CORPUS_ROOT_CAUSE_REPORT.md
?? runtime_evidence_real_corpus/
?? valid_edf_base64.txt
```

The commit is aligned with `origin/main`, but repository cleanliness fails.

## Fresh Operator Validation

Status: `PARTIAL PASS`

Evidence:

- `certification_evidence_20260601_211116/phase02_fresh_clone_install_startup.txt`
- `certification_evidence_20260601_211116/phase02_startup_shutdown_restart.txt`
- `certification_evidence_20260601_211116/phase02_09_12_server_restart_operator_probe_corrected.json`

Runtime facts:

- Fresh clone succeeded.
- Checkout on `main` succeeded.
- Fresh virtual environment was created.
- Dependency installation completed.
- Server-factory startup and restart probes passed:
  - `/health`: `status=ok`
  - `/livez`: `status=alive`
  - `/readyz`: `ready=true`
  - model recovered after restart with `identity_continuous=true`

Limitation:

- A bare `create_app(ApplicationPlatformService(...))` operator path without server startup provisioning produced HTTP `500` on upload because no model was prepared. Evidence: `phase02_09_12_server_restart_operator_probe.json`.

## Dependency Validation

Status: `PASS`

Evidence:

- `certification_evidence_20260601_211116/phase03_python_version.txt`
- `certification_evidence_20260601_211116/phase03_pip_freeze.txt`

Runtime facts:

- Python: `Python 3.12.10`
- Installed dependency set captured in `pip freeze`.
- Required pinned packages observed:
  - `numpy==2.4.6`
  - `mne==1.12.1`
  - `scipy==1.17.1`
  - `pytest==9.0.3`
  - `ruff==0.15.15`
  - `fastapi==0.121.2`
  - `uvicorn==0.34.3`
  - `httpx==0.28.1`

## Pytest Validation

Status: `FAIL`

Evidence:

- `certification_evidence_20260601_211116/phase04_pytest_full.txt`

Fresh operator command:

```text
python -m pytest
```

Runtime result:

- Exit code: `2`
- Duration: `15.448` seconds
- Pass count: `0`
- Fail count: `0`
- Error count: `1`
- Skip count: `0`
- Warning count: `0`

Collection error:

```text
ERROR collecting tests/test_validation.py
ModuleNotFoundError: No module named 'resource'
```

This is a certification blocker.

## Verifier Validation

Status: `FAIL`

Evidence:

- `certification_evidence_20260601_211116/phase05_verifier_summary.json`
- `certification_evidence_20260601_211116/phase05_verifier_summary.txt`
- Individual verifier logs: `certification_evidence_20260601_211116/phase05_verifier_*.txt`

Runtime result:

- Total verifier scripts executed: `43`
- Passed: `24`
- Failed: `19`

Failed verifier scripts:

- `verify_drp2_production_models.py`
- `verify_mp4_source_of_truth.py`
- `verify_productization_p10.py`
- `verify_productization_p9.py`
- `verify_v1.py`
- `verify_v1_p5_p6.py`
- `verify_v2.py`
- `verify_v2_p3_p4.py`
- `verify_v2_p5_p6.py`
- `verify_v2_p7_p8.py`
- `verify_v3_p1_p2.py`
- `verify_v3_p3_p4.py`
- `verify_v3_p5_p6.py`
- `verify_v3_p7_p8.py`
- `verify_v4_p1_p2.py`
- `verify_v4_p3_p4.py`
- `verify_v4_p5_p6.py`
- `verify_v4_p7_p8.py`
- `verify_v4_p9_p10.py`

Representative runtime failures:

```text
verify_drp2_production_models.py
[FAIL] 11. Determinism preserved -- same model id + version across instances
RESULT: FAILURES PRESENT
```

```text
verify_mp4_source_of_truth.py
[FAIL] 14. Repository integrity preserved -- import error: No module named 'ml'
[FAIL] 15. MP-4 completed
RESULT: FAILURES PRESENT
```

```text
verify_productization_p9.py
ModuleNotFoundError: No module named 'resource'
```

```text
verify_v1.py
ModuleNotFoundError: No module named 'datasets'
```

This is a certification blocker.

## Docker Validation

Status: `PASS`

Evidence:

- `certification_evidence_20260601_211116/phase06_docker_direct_build_run.txt`
- `certification_evidence_20260601_211116/phase05_verifier_verify_dbe2_docker_deployment.txt`

Runtime facts:

- Docker: `Docker version 29.4.3, build 055a478`
- Docker Compose: `Docker Compose version v5.1.3`
- Backend image build exit code: `0`
- Direct container run exit code: `0`
- `/health`: HTTP response body reported `status=ok`
- `/readyz`: HTTP response body reported `ready=true`
- `/openapi.json`: HTTP `200`, `7007` bytes
- Docker restart completed and `/health` still reported `status=ok`
- Container shutdown completed

## Authentication Validation

Status: `PARTIAL PASS`

Evidence:

- `certification_evidence_20260601_211116/phase07_08_09_10_11_12_api_runtime_audit.json`
- `certification_evidence_20260601_211116/phase05_verifier_verify_dbe5_authentication_reliability.txt`

Runtime facts:

- Registration status: `201`
- Login status: `200`
- Token generated: `true`
- Missing token upload status: `401`
- DBE-5 verifier passed and reported invalid-token classes return `[401, 403]` with no `500`.

Limitations:

- The ad hoc `/v1/auth/me` token-validation probe returned `404` because that endpoint does not exist.
- Authentication reliability is better represented by the protected upload endpoint and DBE-5 verifier evidence.

## EEG Workflow Validation

Status: `PASS`

Evidence:

- `certification_evidence_20260601_211116/phase07_08_09_10_11_12_api_runtime_audit.json`
- `certification_evidence_20260601_211116/phase05_verifier_verify_track3_application.txt`

Runtime facts:

- Real EDF: `data/real/chb_mit/chb01/chb01_03.edf`
- Upload status: `201`
- Upload accepted: `true`
- Channels: `23`
- Sampling frequency: `256.0`
- Prediction status: `200`
- JSON report status: `200`
- PDF report status: `200`
- PDF magic: `%PDF-`
- Readiness: `READY_FOR_USERS`

## Model Lifecycle Validation

Status: `PASS WITH LIMITATION`

Evidence:

- `certification_evidence_20260601_211116/phase02_09_12_server_restart_operator_probe_corrected.json`
- `certification_evidence_20260601_211116/phase13_baseline_runtime_ids.json`
- `certification_evidence_20260601_211116/phase05_verifier_verify_mp3_model_lifecycle.txt`

Runtime facts:

- Server startup model: `model+3d6723d7655aa857`
- Startup `/readyz`: `ready=true`
- Restart `/readyz`: `ready=true`
- Restart recovery:
  - `model_available=true`
  - `registered=true`
  - `audit_ok=true`
  - `lineage_ok=true`
  - `identity_continuous=true`
  - `recovered=true`
  - `recovered_from_persistence=true`

Limitation:

- Baseline ID probe without a configured persistence workspace reported `identity_persisted=false` and `persistence_available=false`, while still reporting `persistence_ok=true`.

## Operations Validation

Status: `PASS`

Evidence:

- `certification_evidence_20260601_211116/phase07_08_09_10_11_12_api_runtime_audit.json`
- `certification_evidence_20260601_211116/phase05_verifier_verify_track4_operations.txt`

Runtime facts:

- Health: `HEALTHY`
- Diagnostics: `ok=true`
- Diagnostic root causes: `[]`
- Qualification: `QUALIFIED`
- Deployment readiness: `READY_FOR_DEPLOYMENT`
- Ready for deployment: `true`
- Audit verified: `true`
- Lineage verified: `true`

## Hostile Testing Validation

Status: `FAIL`

Evidence:

- `certification_evidence_20260601_211116/phase07_08_09_10_11_12_api_runtime_audit.json`
- `certification_evidence_20260601_211116/phase02_09_12_server_restart_operator_probe.json`
- `certification_evidence_20260601_211116/phase05_verifier_verify_dbe3_duplicate_upload.txt`
- `certification_evidence_20260601_211116/phase05_verifier_verify_dbe5_authentication_reliability.txt`

Controlled-failure evidence:

- Invalid EDF upload status: `422`
- Corrupted EDF upload status: `422`
- Duplicate upload statuses: `[200, 200]`
- Missing token status: `401`
- Repeated prediction statuses: `[200, 200]`
- DBE-3 duplicate upload verifier passed with no `500`.
- DBE-5 authentication verifier passed with no `500`.

Failure evidence:

```text
independent_operator_bare_app.upload_status_without_hidden_model_prep = 500
upload_body_prefix = Internal Server Error
```

The hostile/operator rule requires controlled failures and no `500s`; this phase fails.

## Independent Operator Validation

Status: `MIXED / FAIL`

Evidence:

- `certification_evidence_20260601_211116/phase02_09_12_server_restart_operator_probe.json`
- `certification_evidence_20260601_211116/phase02_09_12_server_restart_operator_probe_corrected.json`

Passing server-factory journey:

- `/readyz` before upload: `ready=true`
- Register: `201`
- Login: `200`
- Token generated: `true`
- Upload: `201`
- Upload accepted: `true`
- Prediction: `200`
- Report: `200`

Failing bare-app journey:

- Health: `200`
- Register: `201`
- Login: `200`
- Model status before upload: `prepared=false`
- Upload without hidden model preparation: `500`
- Body prefix: `Internal Server Error`

Because an independent operator path can hit a `500` without hidden model-preparation knowledge, this phase fails.

## Release Baseline

Status: `CAPTURED`

Baseline artifact:

- `RELEASE_BASELINE.md`

Baseline evidence:

- `certification_evidence_20260601_211116/phase13_release_baseline_inputs.txt`
- `certification_evidence_20260601_211116/phase13_baseline_runtime_ids.json`

## Known Limitations

- Current audited workspace is dirty.
- Fresh operator `pytest` fails on Windows due to `ModuleNotFoundError: No module named 'resource'`.
- 19 of 43 verifier scripts failed in the fresh operator execution.
- Some verifier scripts fail when executed as direct script files because repository imports such as `datasets`, `backend`, `scripts`, or `ml` are unavailable in that invocation mode.
- DRP-2 production-model verifier reports determinism failure.
- MP-4 source-of-truth verifier reports repository integrity failure.
- Bare `create_app(ApplicationPlatformService(...))` path can produce HTTP `500` if upload is attempted before model preparation.
- Ad hoc `/v1/auth/me` token-validation endpoint does not exist; protected upload endpoint evidence was used for token behavior.
- Real EEG data was copied into the fresh clone's runtime `data/real` directory to execute the required real EDF workflow.

## Certification Decision

Allowed outcome selected: `NOT CERTIFIED`

Reason:

NeuroVision cannot be honestly classified as `CERTIFIED` or `CONDITIONALLY CERTIFIED` under this directive because multiple certification-blocking runtime failures remain:

- Repository truth cleanliness failed.
- Fresh operator `pytest` failed during collection.
- 19 verifier scripts failed.
- Hostile/operator testing found an HTTP `500` path.
- Independent operator validation is mixed and includes a failing bare-app journey.

The release has strong passing evidence for Docker, server-factory startup/restart, Track 1-4 real-corpus workflows, authentication reliability verifiers, operations qualification, and the real EEG workflow. Those passes do not override the certification blockers above.
