# RELEASE BASELINE

Certification timestamp: `2026-06-01T21:38:53.2376327+05:30`

Evidence directory:

`certification_evidence_20260601_211116/`

## Repository

- Branch: `main`
- Commit SHA: `923443b9f58acf7247b1bac14249f4611d76e51f`
- Origin main: `923443b9f58acf7247b1bac14249f4611d76e51f`
- Origin HEAD: `refs/remotes/origin/main`
- Fresh operator clone: `C:\Users\AKILA\AppData\Local\Temp\nv_final_cert_operator_20260601_211233\neurovision_ai`

Repository truth evidence:

- `certification_evidence_20260601_211116/phase01_repository_truth.txt`
- `certification_evidence_20260601_211116/phase02_fresh_clone_install_startup.txt`

## Runtime

- Python: `Python 3.12.10`
- Docker: `Docker version 29.4.3, build 055a478`
- Docker Compose: `Docker Compose version v5.1.3`

Runtime evidence:

- `certification_evidence_20260601_211116/phase03_python_version.txt`
- `certification_evidence_20260601_211116/phase06_docker_direct_build_run.txt`

## Dependency Versions

Dependency freeze evidence:

- `certification_evidence_20260601_211116/phase03_pip_freeze.txt`

Key pinned package versions observed:

- `numpy==2.4.6`
- `mne==1.12.1`
- `scipy==1.17.1`
- `pytest==9.0.3`
- `ruff==0.15.15`
- `fastapi==0.121.2`
- `uvicorn==0.34.3`
- `httpx==0.28.1`

## Dataset IDs

Runtime ID evidence:

- `certification_evidence_20260601_211116/phase13_baseline_runtime_ids.json`

Observed IDs:

- Track 1 dataset ID: `real_dataset+399b56373ce0f821`
- Track 1 inventory ID: `inventory+e1ae32150592f43d`
- Track 1 availability: `verified`
- Track 2 dataset ID: `dataset+bd6b07d768eb9e94`

## Model IDs

Track 2 production model IDs:

- `production_model+5d968503fe7182ea`
- `production_model+36d40c2a97f279b6`
- `production_model+516df1ac262417f4`
- `production_model+c629d3748cb926f6`
- `production_model+ccc602e35d9dd76c`

Track 2 ready model IDs:

- `production_model+5d968503fe7182ea`
- `production_model+36d40c2a97f279b6`
- `production_model+516df1ac262417f4`
- `production_model+c629d3748cb926f6`
- `production_model+ccc602e35d9dd76c`

Server startup model:

- `model+3d6723d7655aa857`
- Architecture: `eegnet`
- Readiness: `trained`

## Pytest Counts

Evidence:

- `certification_evidence_20260601_211116/phase04_pytest_full.txt`

Observed fresh-operator pytest result:

- Pass count: `0`
- Failure count: `0`
- Error count: `1`
- Skip count: `0`
- Warning count: `0`
- Exit code: `2`
- Duration: `15.448` seconds

Collection error:

```text
tests/test_validation.py
ModuleNotFoundError: No module named 'resource'
```

## Verifier Counts

Evidence:

- `certification_evidence_20260601_211116/phase05_verifier_summary.json`
- `certification_evidence_20260601_211116/phase05_verifier_summary.txt`

Observed verifier results:

- Total verifier scripts: `43`
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
