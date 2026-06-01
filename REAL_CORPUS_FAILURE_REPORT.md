# REAL CORPUS FAILURE REPORT

Scope: Section 2 only. This report records runtime reproduction evidence for the four real-corpus failures. No diagnosis, classification, or fixes are included.

Evidence directory:

`runtime_evidence_real_corpus/`

Runtime:

`C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe`

Working directory:

`C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai`

## FAILURE 1

Test:

`tests/test_application_platform_e2e.py::test_real_corpus_user_workflow_when_available`

Exact command:

```text
C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe -m pytest -vv -s --tb=long tests/test_application_platform_e2e.py::test_real_corpus_user_workflow_when_available
```

Exit code:

```text
1
```

Stdout/stderr and traceback:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\\Users\\AKILA\\OneDrive\\\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\\neurovision\\neurovision_ai
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/test_application_platform_e2e.py::test_real_corpus_user_workflow_when_available FAILED

================================== FAILURES ===================================
________________ test_real_corpus_user_workflow_when_available ________________

    def test_real_corpus_user_workflow_when_available():
        root = real_chb_mit_root()
        if root is None:
            pytest.skip("real CHB-MIT corpus not acquired locally")
        # prepare a model from bounded segments of the genuine PhysioNet recordings
        svc = ApplicationPlatformService(analysis_seconds=20.0)
        chb = os.path.join(root, "chb_mit", "chb01")
        segs = []
        cohort = []
        for i, name in enumerate(("chb01_01.edf", "chb01_03.edf")):
>           with open(os.path.join(chb, name), "rb") as fh:
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\AKILA\\\\OneDrive\\\\\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\\\\neurovision\\\\neurovision_ai\\\\data\\\\real\\\\chb_mit\\\\chb01\\\\chb01_03.edf'

tests\test_application_platform_e2e.py:68: FileNotFoundError
=========================== short test summary info ===========================
FAILED tests/test_application_platform_e2e.py::test_real_corpus_user_workflow_when_available
============================== 1 failed in 7.79s ==============================
```

Dataset path used:

```text
C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real\chb_mit\chb01
```

Runtime state captured:

```text
real_chb_mit_root = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real
chb01_exists = true
chb01_entries = ["chb01-summary.txt", "chb01_01.edf", "chb01_03.edf.part"]
chb01_edf_files = ["chb01_01.edf"]
exists:chb_mit\chb01\chb01_01.edf = true
size:chb_mit\chb01\chb01_01.edf = 42399744
exists:chb_mit\chb01\chb01_03.edf = false
```

Readiness, registry, lineage, audit state if present:

```text
No application readiness, registry, lineage, or audit state was emitted before the FileNotFoundError.
```

Full raw log:

`runtime_evidence_real_corpus/failure1_application_platform.txt`

## FAILURE 2

Test:

`tests/test_dataset_acquisition.py::test_real_chb_mit_corpus_when_available`

Exact command:

```text
C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe -m pytest -vv -s --tb=long tests/test_dataset_acquisition.py::test_real_chb_mit_corpus_when_available
```

Exit code:

```text
1
```

Stdout/stderr and traceback:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\\Users\\AKILA\\OneDrive\\\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\\neurovision\\neurovision_ai
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/test_dataset_acquisition.py::test_real_chb_mit_corpus_when_available FAILED

================================== FAILURES ===================================
___________________ test_real_chb_mit_corpus_when_available ___________________

    def test_real_chb_mit_corpus_when_available():
        root = real_chb_mit_root()
        if root is None:
            pytest.skip("real CHB-MIT corpus not acquired locally (run scripts.acquire_real_dataset)")
        svc = RealDatasetService(data_root=root)
        out = svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
>       assert out.ready_for_training
E       AssertionError: assert False
E        +  where False = RealDatasetOutcome(...).ready_for_training

tests\test_dataset_acquisition.py:243: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_dataset_acquisition.py::test_real_chb_mit_corpus_when_available
============================== 1 failed in 6.15s ==============================
```

Assertion failure:

```text
expected: out.ready_for_training truthy
actual: False
```

Dataset path used:

```text
C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real\chb_mit
```

Dataset state captured:

```json
{
  "dataset_id": "real_dataset+909a54a42800eeb4",
  "source": "chb_mit",
  "name": "CHB-MIT Scalp EEG Database",
  "local_root": "C:\\Users\\AKILA\\OneDrive\\ドキュメント\\neurovision\\neurovision_ai\\data\\real\\chb_mit",
  "content_fingerprint": "3d436921604dddb5",
  "n_patients": 1,
  "n_recordings": 1,
  "n_labels": 1,
  "availability_state": "partially_downloaded",
  "validation_id": "validation+21225a03239c4e97",
  "label_verification_id": "label_verification+2836247bddbea20f",
  "inventory_id": "inventory+a5250e1b32a9ca4a",
  "readiness_id": "training_readiness+519227fe95ff05f7",
  "source_id": "dataset_source+ad9f8ac81573e223",
  "acquisition_signature": "ab8be9becfb053d1",
  "owner": "dataset-ops",
  "created_at": "1970-01-01T00:00:00Z",
  "lineage_id": "lineage+fa3e66d1b847fda2",
  "registry_lineage_id": "lineage+b8166b58ff641002",
  "audit_head": "46234beef5fd2035",
  "domain_version": "acquisition-domain@1.0.0"
}
```

Acquisition state captured:

```json
{
  "source": "chb_mit",
  "spec_signature": "ab8be9becfb053d1",
  "attempted": true,
  "access_requirement": "open",
  "n_items": 3,
  "n_acquired": 2,
  "local_root": "C:\\Users\\AKILA\\OneDrive\\ドキュメント\\neurovision\\neurovision_ai\\data\\real\\chb_mit",
  "note": "acquired minimal real subset",
  "items": [
    {
      "relative_path": "chb01/chb01-summary.txt",
      "state": "downloaded",
      "size_bytes": 5355,
      "checksum_sha256": "77e86183845192d147c88a9bb4263c2b4a32e936c6236029770f86ca2ea023db",
      "note": "already present"
    },
    {
      "relative_path": "chb01/chb01_01.edf",
      "state": "downloaded",
      "size_bytes": 42399744,
      "checksum_sha256": "92ec026f633dca94ee74c2e2b67cf9d58aa50da700b650a1696cf497dac073e3",
      "note": "already present"
    },
    {
      "relative_path": "chb01/chb01_03.edf",
      "state": "unavailable",
      "size_bytes": 0,
      "checksum_sha256": "",
      "note": "download disabled (allow_download=False)"
    }
  ]
}
```

Validation state captured:

```json
{
  "validation_id": "validation+21225a03239c4e97",
  "ok": true,
  "n_checks": 9,
  "n_blocking_failed": 0,
  "signature": "e0d7bde33c2a8e4c"
}
```

Readiness state captured:

```json
{
  "readiness_id": "training_readiness+519227fe95ff05f7",
  "score": 0.7205,
  "classification": "PARTIALLY_READY",
  "dimensions": {
    "acquisition": 0.3,
    "labels": 0.5,
    "metadata": 1.0,
    "registry": 1.0,
    "training": 0.67,
    "validation": 1.0
  },
  "findings": [
    "acquisition=0.3",
    "labels=0.5",
    "training=0.67"
  ],
  "readiness_version": "acquisition-readiness@1.0.0"
}
```

Inventory state captured:

```json
{
  "inventory_id": "inventory+a5250e1b32a9ca4a",
  "source": "chb_mit",
  "n_patients": 1,
  "n_sessions": 1,
  "n_recordings": 1,
  "n_labels": 1,
  "n_channels_distribution": {
    "23": 1
  },
  "sampling_frequencies": [
    256.0
  ],
  "total_duration_seconds": 3600.0,
  "total_bytes": 42399744,
  "label_distribution": {
    "background": 1
  },
  "inventory_version": "acquisition-inventory@1.0.0"
}
```

Lineage and audit state captured:

```text
dataset_lineage_id = lineage+fa3e66d1b847fda2
dataset_registry_lineage_id = lineage+b8166b58ff641002
dataset_audit_head = 46234beef5fd2035
dataset_audit_verify = null
```

Full raw log:

`runtime_evidence_real_corpus/failure2_dataset_acquisition.txt`

## FAILURE 3

Test:

`tests/test_operations_platform.py::test_real_corpus_qualification_when_available`

Exact command:

```text
C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe -m pytest -vv -s --tb=long tests/test_operations_platform.py::test_real_corpus_qualification_when_available
```

Exit code:

```text
1
```

Stdout/stderr and traceback:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\\Users\\AKILA\\OneDrive\\\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\\neurovision\\neurovision_ai
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/test_operations_platform.py::test_real_corpus_qualification_when_available FAILED

================================== FAILURES ===================================
________________ test_real_corpus_qualification_when_available ________________

    def test_real_corpus_qualification_when_available():
        from _track3_helpers import real_chb_mit_root
        import base64
        import os
        root = real_chb_mit_root()
        if root is None:
            pytest.skip("real CHB-MIT corpus not acquired locally")
        from backend.application_platform import ApplicationPlatformService as APS
        from backend.application_platform.uploads import prepare_bounded_segment
        from backend.application_platform import create_app
        from backend.model_foundation import ModelArchitecture
        from fastapi.testclient import TestClient

        svc = APS(analysis_seconds=20.0)
        chb = os.path.join(root, "chb_mit", "chb01")
        segs, cohort = [], []
        for i, name in enumerate(("chb01_01.edf", "chb01_03.edf")):
>           with open(os.path.join(chb, name), "rb") as fh:
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\AKILA\\\\OneDrive\\\\\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\\\\neurovision\\\\neurovision_ai\\\\data\\\\real\\\\chb_mit\\\\chb01\\\\chb01_03.edf'

tests\test_operations_platform.py:208: FileNotFoundError
=========================== short test summary info ===========================
FAILED tests/test_operations_platform.py::test_real_corpus_qualification_when_available
============================== 1 failed in 8.90s ==============================
```

Dataset path used:

```text
C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real\chb_mit\chb01
```

Runtime state captured:

```text
real_chb_mit_root = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real
chb01_exists = true
chb01_entries = ["chb01-summary.txt", "chb01_01.edf", "chb01_03.edf.part"]
chb01_edf_files = ["chb01_01.edf"]
exists:chb_mit\chb01\chb01_01.edf = true
size:chb_mit\chb01\chb01_01.edf = 42399744
exists:chb_mit\chb01\chb01_03.edf = false
```

Readiness, registry, lineage, audit state if present:

```text
No operations qualification readiness, registry, lineage, or audit state was emitted before the FileNotFoundError.
```

Full raw log:

`runtime_evidence_real_corpus/failure3_operations_platform.txt`

## FAILURE 4

Test:

`tests/test_real_model_training.py::test_real_chb_mit_corpus_when_available`

Exact command:

```text
C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe -m pytest -vv -s --tb=long tests/test_real_model_training.py::test_real_chb_mit_corpus_when_available
```

Exit code:

```text
1
```

Stdout/stderr and traceback:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\AKILA\AppData\Local\Temp\nv_runtime2_dep_CcxEF8\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\\Users\\AKILA\\OneDrive\\\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\\neurovision\\neurovision_ai
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/test_real_model_training.py::test_real_chb_mit_corpus_when_available FAILED

================================== FAILURES ===================================
___________________ test_real_chb_mit_corpus_when_available ___________________

    def test_real_chb_mit_corpus_when_available():
        root = real_chb_mit_root()
        if root is None:
            pytest.skip("real CHB-MIT corpus not acquired locally")
        svc = RealModelTrainingService(data_root=root)
        out = svc.develop(allow_download=False, window_seconds=4.0, background_per_seizure=4)
        assert out.dataset_record.n_windows >= 10
        assert out.dataset_record.windowing.sampling_frequency == 256.0
        ready = out.ready_models()
>       assert ready, "expected READY_FOR_SERVING models on the real corpus"
E       AssertionError: expected READY_FOR_SERVING models on the real corpus
E       assert []

tests\test_real_model_training.py:223: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_real_model_training.py::test_real_chb_mit_corpus_when_available
============================= 1 failed in 12.86s ==============================
```

Assertion failure:

```text
expected: ready truthy ("expected READY_FOR_SERVING models on the real corpus")
actual: []
```

Dataset/training state captured:

```json
{
  "dataset_id": "dataset+328437171d44e7d5",
  "source_dataset_id": "real_dataset+909a54a42800eeb4",
  "source": "chb_mit",
  "n_windows": 1799,
  "n_features": 11,
  "n_classes": 1,
  "class_names": [
    "background"
  ],
  "class_distribution": {
    "background": 1799
  },
  "patient_ids": [
    "chb01"
  ],
  "recording_ids": [
    "recording+89a0fcc51602b3ce"
  ],
  "split_strategy": "window_stratified",
  "patient_disjoint": false,
  "n_train": 1079,
  "n_val": 360,
  "n_test": 360,
  "windowing": {
    "window_seconds": 4.0,
    "stride_seconds": 2.0,
    "sampling_frequency": 256.0,
    "n_samples_per_window": 1024,
    "background_per_seizure": 4
  },
  "feature_names": [
    "rel_delta",
    "rel_theta",
    "rel_alpha",
    "rel_beta",
    "rel_gamma",
    "total_power_log",
    "std",
    "rms",
    "mean_abs",
    "zero_crossing_rate",
    "line_length"
  ],
  "data_fingerprint": "a541dff6b299a60f",
  "created_at": "1970-01-01T00:00:00Z",
  "lineage_id": null,
  "audit_state": null,
  "dataset_version": "rmt-dataset@1.0.0"
}
```

Training readiness/model state captured:

```text
training_ready_models = []
training_model_records = []
```

Benchmark state captured:

```text
training_benchmarks count = 5
benchmark model ids:
- production_model+ed829c08a156906a
- production_model+d8ec639c27438b5e
- production_model+86157fe1d0d49d2e
- production_model+80fc50ffecea0b3a
- production_model+e1d240785eeec4f0
```

Benchmark lineage ids captured:

```text
lineage+fca609368dca45ad
lineage+80c1baf61ee3bedd
lineage+c3dca638a4001f84
lineage+87b24a6caee38179
lineage+663408c156cb8525
```

Audit state captured:

```text
training_audit_verify = null
```

Full raw log:

`runtime_evidence_real_corpus/failure4_real_model_training.txt`

## Runtime State Probe

Exact probe file:

`runtime_evidence_real_corpus/runtime_state_probe2.py`

Probe output:

`runtime_evidence_real_corpus/runtime_state_probe2.txt`

Probe exit:

```text
0
```

