# REAL CORPUS REMEDIATION REPORT

Repository truth:

- Branch: `main`
- Commit: `923443b9f58acf7247b1bac14249f4611d76e51f`
- Runtime Python: `C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe`
- Evidence directory: `runtime_evidence_real_corpus/`

## Acquisition Evidence

Evidence files:

- `runtime_evidence_real_corpus/remediation_phase2_acquire_rerun.txt`
- `runtime_evidence_real_corpus/remediation_phase2_track1_probe.txt`

Existing Track 1 acquisition flow was used:

```text
python -m scripts.acquire_real_dataset --source chb_mit --timeout 900
```

Runtime acquisition output:

```text
Acquisition - chb_mit  (attempted=True)
chb01/chb01-summary.txt        downloaded           5355  already present
chb01/chb01_01.edf             downloaded       42399744  already present
chb01/chb01_03.edf             downloaded       42399744  already present
```

Runtime file/EDF evidence:

```json
{
  "file_exists": true,
  "file_size": 42399744,
  "edf_readable": true,
  "edf_error": null,
  "edf_n_channels": 23,
  "edf_sampling_frequency": 256.0,
  "edf_duration_seconds": 3600.0,
  "summary_exists": true,
  "summary_has_chb01_03": true
}
```

Acquisition-path inspection evidence:

- Existing downloader writes to `dest + ".part"` and completes with `os.replace(tmp, dest)`.
- Present non-empty files are reused with note `already present`.
- Missing files with `allow_download=False` are reported unavailable with note `download disabled (allow_download=False)`.
- The earlier partial state was consistent with integration being run while download was disabled and only the `.part` artifact existed.
- No separate resume logic exists in the downloader; the authoritative acquisition flow reconciles by downloading/reusing the final EDF path.

## Track 1 Evidence

Evidence files:

- `runtime_evidence_real_corpus/remediation_phase2_acquire_rerun.txt`
- `runtime_evidence_real_corpus/remediation_phase2_track1_probe.txt`
- `runtime_evidence_real_corpus/remediation_phase4_dataset_acquisition_test.txt`
- `runtime_evidence_real_corpus/remediation_phase9_verify_track1_real_data.txt`

Track 1 runtime output:

```text
availability        : verified (3/3 verified)
patients/recordings : 1 / 2
labels (scheme)     : 2 (chb_mit_seizure); coverage=1.0 classes=['background', 'seizure']
validation ok       : True
lineage verified    : True
audit verified      : True
READINESS           : READY_FOR_TRAINING (score=1.0)
```

Structured Track 1 evidence:

```json
{
  "availability_state": "verified",
  "n_items": 3,
  "n_acquired": 3,
  "ready_for_training": true,
  "readiness_classification": "READY_FOR_TRAINING",
  "readiness_score": 1.0,
  "n_patients": 1,
  "n_recordings": 2,
  "n_labels": 2,
  "label_classes": ["background", "seizure"],
  "registry_lineage_verified": true,
  "audit_verified": true
}
```

Focused test:

```text
tests/test_dataset_acquisition.py::test_real_chb_mit_corpus_when_available PASSED
1 passed in 4.68s
```

Verify script:

```text
TRACK 1 - REAL DATA ACQUISITION & INTEGRATION - FINAL VALIDATION
[PASS] 14. Real dataset support exists -- availability=verified acquired=3 real_recordings=2
[PASS] 15. Track 1 completed -- real CHB-MIT acquired, validated, labelled, inventoried, READY_FOR_TRAINING
RESULT: ALL CRITERIA PASS
```

## Track 2 Evidence

Evidence files:

- `runtime_evidence_real_corpus/remediation_phase5_track2_probe.txt`
- `runtime_evidence_real_corpus/remediation_phase5_real_model_training_test.txt`
- `runtime_evidence_real_corpus/remediation_phase9_verify_track2_real_models.txt`

Structured Track 2 evidence:

```json
{
  "dataset_bundle": "DatasetBundle",
  "dataset_id": "dataset+bd6b07d768eb9e94",
  "n_classes": 2,
  "class_names": ["background", "seizure"],
  "class_distribution": {"background": 84, "seizure": 21},
  "n_patients": 1,
  "n_recordings": 2,
  "n_windows": 105,
  "training_ready": true,
  "n_ready_models": 5,
  "recommended_model_id": "production_model+516df1ac262417f4"
}
```

Focused test:

```text
tests/test_real_model_training.py::test_real_chb_mit_corpus_when_available PASSED
1 passed in 16.98s
```

Verify script:

```text
TRACK 2 - REAL MODEL TRAINING & BENCHMARK - FINAL VALIDATION
[PASS] 1. Real dataset training works -- windows=105 models=5 (real CHB-MIT)
[PASS] 6. Readiness scoring works -- ready_for_serving=5/5
[PASS] 15. Track 2 completed -- real CHB-MIT trained -> evaluated -> benchmarked -> compared -> READY_FOR_SERVING
RESULT: ALL CRITERIA PASS
```

## Track 3 Evidence

Evidence files:

- `runtime_evidence_real_corpus/remediation_phase6_track3_probe.txt`
- `runtime_evidence_real_corpus/remediation_phase6_application_platform_test.txt`
- `runtime_evidence_real_corpus/remediation_phase9_verify_track3_application.txt`

Structured Track 3 evidence:

```json
{
  "upload_http_status": 201,
  "upload_accepted": true,
  "upload_n_channels": 23,
  "upload_sampling_frequency": 256.0,
  "analysis_id": "app_analysis+18861643f1068a4c",
  "prediction_status": 200,
  "prediction_label": "0",
  "report_status": 200,
  "readiness": "READY_FOR_USERS",
  "lineage_verified": true,
  "audit_verified": true
}
```

Focused test:

```text
tests/test_application_platform_e2e.py::test_real_corpus_user_workflow_when_available PASSED
1 passed, 3 warnings in 48.22s
```

Verify script:

```text
TRACK 3 - REAL PRODUCT APPLICATION - FINAL VALIDATION
[PASS] 2. Upload workflow works -- format=edf n_channels=23
[PASS] 4. Prediction workflow works -- label=0 conf=high model=model+7f6388d06a62
[PASS] 5. Reports generate -- JSON + HTML + PDF exported
[PASS] 15. Track 3 completed -- real EEG uploaded -> prediction -> report -> READY_FOR_USERS, traceable
RESULT: ALL CRITERIA PASS
```

## Track 4 Evidence

Evidence files:

- `runtime_evidence_real_corpus/remediation_phase7_track4_probe.txt`
- `runtime_evidence_real_corpus/remediation_phase7_operations_platform_test.txt`
- `runtime_evidence_real_corpus/remediation_phase9_verify_track4_operations.txt`

Structured Track 4 evidence:

```json
{
  "qualification_status": "QUALIFIED",
  "health_overall": "HEALTHY",
  "diagnostic_ok": true,
  "diagnostic_root_causes": [],
  "deployment_readiness": "READY_FOR_DEPLOYMENT",
  "readiness_score": 1.0,
  "ready_for_deployment": true,
  "audit_verified": true,
  "lineage_verified": true
}
```

Focused test:

```text
tests/test_operations_platform.py::test_real_corpus_qualification_when_available PASSED
1 passed, 3 warnings in 48.31s
```

Verify script:

```text
TRACK 4 - OPERATIONAL READINESS & DEPLOYMENT QUALIFICATION - FINAL VALIDATION
[PASS] 1. Health monitoring works -- overall=HEALTHY components=7
[PASS] 3. Diagnostics work -- ok=True findings=5 root_causes=[]
[PASS] 4. Qualification works -- status=QUALIFIED available=7/7
[PASS] 5. Readiness scoring works -- classification=READY_FOR_DEPLOYMENT score=1.0
[PASS] 15. Track 4 completed -- health -> monitor -> diagnose -> qualify -> READY_FOR_DEPLOYMENT, traceable
RESULT: ALL CRITERIA PASS
```

## Pytest Results

Evidence file:

- `runtime_evidence_real_corpus/remediation_phase8_pytest_full.txt`

Full suite result:

```text
1148 passed, 6 warnings in 649.49s (0:10:49)
```

Failure count: `0`

Skip count: `0`

Warnings:

```text
6 RuntimeWarning warnings from scipy.signal._spectral_py.py:2041:
invalid value encountered in divide
```

Failures: none.

## Verify Script Results

Evidence files:

- `runtime_evidence_real_corpus/remediation_phase9_verify_track1_real_data.txt`
- `runtime_evidence_real_corpus/remediation_phase9_verify_track2_real_models.txt`
- `runtime_evidence_real_corpus/remediation_phase9_verify_track3_application.txt`
- `runtime_evidence_real_corpus/remediation_phase9_verify_track4_operations.txt`

Results:

```text
scripts/verify_track1_real_data.py       RESULT: ALL CRITERIA PASS
scripts/verify_track2_real_models.py     RESULT: ALL CRITERIA PASS
scripts/verify_track3_application.py     RESULT: ALL CRITERIA PASS
scripts/verify_track4_operations.py      RESULT: ALL CRITERIA PASS
```

## Certification Status

Certification status: `PASS`

Runtime evidence shows:

- `chb01/chb01_03.edf` exists.
- `chb01/chb01_03.edf` is non-zero size: `42399744` bytes.
- EDF is readable: `23` channels, `256.0 Hz`, `3600.0` seconds.
- Summary labels include `chb01_03.edf`.
- Track 1 acquisition is complete: `n_items=3`, `n_acquired=3`, `availability_state=verified`.
- Track 1 readiness is `READY_FOR_TRAINING`.
- Track 2 has `n_classes=2`, classes `background` and `seizure`, and `5` ready models.
- Track 3 upload, analysis, prediction, and report succeeded.
- Track 4 health, diagnostics, qualification, and deployment readiness succeeded.
- Full pytest passed: `1148 passed`, `0 failed`, `0 skipped`.
- Impacted verify scripts all passed.
