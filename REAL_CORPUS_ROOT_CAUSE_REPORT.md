# REAL CORPUS ROOT CAUSE REPORT

Scope: Sections 3 through 8 only. No code was modified. No tests were changed. No fixes were implemented.

Evidence used:

- `REAL_CORPUS_FAILURE_REPORT.md`
- `runtime_evidence_real_corpus/failure1_application_platform.txt`
- `runtime_evidence_real_corpus/failure2_dataset_acquisition.txt`
- `runtime_evidence_real_corpus/failure3_operations_platform.txt`
- `runtime_evidence_real_corpus/failure4_real_model_training.txt`
- `runtime_evidence_real_corpus/runtime_state_probe2.txt`

## 1. Failure Classification Table

| Failure | Test | Classification | Runtime Evidence |
|---|---|---|---|
| FAILURE 1 | `tests/test_application_platform_e2e.py::test_real_corpus_user_workflow_when_available` | C. Corpus acquisition failure | Test opens `data\real\chb_mit\chb01\chb01_03.edf` and receives `FileNotFoundError`. Probe shows `chb01_03.edf` does not exist while `chb01_03.edf.part` exists. |
| FAILURE 2 | `tests/test_dataset_acquisition.py::test_real_chb_mit_corpus_when_available` | C. Corpus acquisition failure | Dataset acquisition reports `n_items=3`, `n_acquired=2`; `chb01/chb01_03.edf` state is `unavailable` with note `download disabled (allow_download=False)`. Dataset readiness is `PARTIALLY_READY`, not ready for training. |
| FAILURE 3 | `tests/test_operations_platform.py::test_real_corpus_qualification_when_available` | C. Corpus acquisition failure | Test opens `data\real\chb_mit\chb01\chb01_03.edf` and receives `FileNotFoundError`. Probe shows only `chb01_01.edf` is visible as an EDF, and `chb01_03.edf` is absent. |
| FAILURE 4 | `tests/test_real_model_training.py::test_real_chb_mit_corpus_when_available` | C. Corpus acquisition failure | Track 2 dataset is built from one recording with `n_classes=1`, `class_names=["background"]`, `patient_disjoint=false`, and `training_ready_models=[]`. Upstream Track 1 evidence shows the expected seizure recording `chb01_03.edf` is unavailable. |

## 2. Architecture Divergence Analysis

### Track 1: Dataset Acquisition

Inputs observed:

```text
real_chb_mit_root = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real
local_root = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real\chb_mit
```

Filesystem state observed:

```text
chb01_exists = true
chb01_entries = ["chb01-summary.txt", "chb01_01.edf", "chb01_03.edf.part"]
chb01_edf_files = ["chb01_01.edf"]
exists:chb_mit\chb01\chb01_01.edf = true
size:chb_mit\chb01\chb01_01.edf = 42399744
exists:chb_mit\chb01\chb01_03.edf = false
```

Outputs observed:

```text
dataset_id = real_dataset+909a54a42800eeb4
availability_state = partially_downloaded
n_patients = 1
n_recordings = 1
n_labels = 1
content_fingerprint = 3d436921604dddb5
```

Readiness observed:

```text
readiness_id = training_readiness+519227fe95ff05f7
classification = PARTIALLY_READY
score = 0.7205
findings = ["acquisition=0.3", "labels=0.5", "training=0.67"]
```

Lineage/audit observed:

```text
lineage_id = lineage+fa3e66d1b847fda2
registry_lineage_id = lineage+b8166b58ff641002
audit_head = 46234beef5fd2035
```

Divergence point:

```text
The acquisition record expects 3 items but only 2 are acquired. The missing item is chb01/chb01_03.edf.
```

### Track 2: Real Model Training

Inputs observed:

```text
source_dataset_id = real_dataset+909a54a42800eeb4
source = chb_mit
```

Dataset bundle observed:

```text
dataset_id = dataset+328437171d44e7d5
n_windows = 1799
n_features = 11
n_classes = 1
class_names = ["background"]
class_distribution = {"background": 1799}
patient_ids = ["chb01"]
recording_ids = ["recording+89a0fcc51602b3ce"]
patient_disjoint = false
n_train = 1079
n_val = 360
n_test = 360
```

Training/model readiness observed:

```text
training_ready_models = []
training_model_records = []
```

Benchmark outputs observed:

```text
training_benchmarks count = 5
benchmark model ids:
- production_model+ed829c08a156906a
- production_model+d8ec639c27438b5e
- production_model+86157fe1d0d49d2e
- production_model+80fc50ffecea0b3a
- production_model+e1d240785eeec4f0
```

Benchmark lineage observed:

```text
lineage+fca609368dca45ad
lineage+80c1baf61ee3bedd
lineage+c3dca638a4001f84
lineage+87b24a6caee38179
lineage+663408c156cb8525
```

Divergence point:

```text
Track 2 receives the same partial corpus reality from Track 1: one available recording, one class ("background"), and no ready models.
```

### Track 3: Application Platform

Inputs observed:

```text
root = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real
chb = root\chb_mit\chb01
required files in test loop = ("chb01_01.edf", "chb01_03.edf")
```

Failure observed:

```text
FileNotFoundError: chb01_03.edf
```

Application outputs observed:

```text
No upload, analysis, prediction, report, readiness, registry, lineage, or audit output was emitted before the file-open failure.
```

Divergence point:

```text
Track 3 attempts to consume the same absent corpus file reported unavailable by Track 1.
```

### Track 4: Operations Qualification

Inputs observed:

```text
root = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real
chb = root\chb_mit\chb01
required files in test loop = ("chb01_01.edf", "chb01_03.edf")
```

Failure observed:

```text
FileNotFoundError: chb01_03.edf
```

Operations outputs observed:

```text
No qualification, health, diagnostics, deployment readiness, registry, lineage, or audit output was emitted before the file-open failure.
```

Divergence point:

```text
Track 4 attempts to consume the same absent corpus file reported unavailable by Track 1.
```

## 3. Dataset Forensics

Dataset discovery:

```text
real_chb_mit_root = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real
root_exists = true
chb01_path = C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai\data\real\chb_mit\chb01
chb01_exists = true
```

EDF visibility:

```text
chb01_edf_files = ["chb01_01.edf"]
exists:chb_mit\chb01\chb01_01.edf = true
exists:chb_mit\chb01\chb01_03.edf = false
```

Summary visibility:

```text
chb01_entries includes "chb01-summary.txt"
```

Partial file visibility:

```text
chb01_entries includes "chb01_03.edf.part"
```

Acquisition record:

```text
n_items = 3
n_acquired = 2
item chb01/chb01-summary.txt state = downloaded
item chb01/chb01_01.edf state = downloaded
item chb01/chb01_03.edf state = unavailable
item chb01/chb01_03.edf note = download disabled (allow_download=False)
```

Inventory:

```text
inventory_id = inventory+a5250e1b32a9ca4a
n_patients = 1
n_sessions = 1
n_recordings = 1
n_labels = 1
total_duration_seconds = 3600.0
total_bytes = 42399744
label_distribution = {"background": 1}
```

Labels:

```text
verification_id = label_verification+2836247bddbea20f
n_recordings = 1
n_labeled = 1
coverage = 1.0
consistent = true
n_classes = 1
classes = ["background"]
class_distribution = {"background": 1}
```

Readiness:

```text
readiness_id = training_readiness+519227fe95ff05f7
score = 0.7205
classification = PARTIALLY_READY
dimensions:
  acquisition = 0.3
  labels = 0.5
  metadata = 1.0
  registry = 1.0
  training = 0.67
  validation = 1.0
findings:
  acquisition=0.3
  labels=0.5
  training=0.67
```

Registry/lineage/audit:

```text
dataset_id = real_dataset+909a54a42800eeb4
lineage_id = lineage+fa3e66d1b847fda2
registry_lineage_id = lineage+b8166b58ff641002
audit_head = 46234beef5fd2035
dataset_audit_verify = null
```

Dataset forensics conclusion:

```text
The corpus is discovered, but it is not complete. The runtime inventory contains one EDF recording and a partial `.part` file for the second expected EDF.
```

## 4. Training Forensics

Dataset bundle:

```text
dataset_id = dataset+328437171d44e7d5
source_dataset_id = real_dataset+909a54a42800eeb4
n_windows = 1799
n_features = 11
n_classes = 1
class_names = ["background"]
class_distribution = {"background": 1799}
patient_ids = ["chb01"]
recording_ids = ["recording+89a0fcc51602b3ce"]
```

Window generation:

```text
window_seconds = 4.0
stride_seconds = 2.0
sampling_frequency = 256.0
n_samples_per_window = 1024
background_per_seizure = 4
n_train = 1079
n_val = 360
n_test = 360
```

Splits:

```text
split_strategy = window_stratified
patient_disjoint = false
```

Labels:

```text
n_classes = 1
class_names = ["background"]
class_distribution = {"background": 1799}
```

Training readiness:

```text
training_ready_models = []
training_model_records = []
```

Evaluation/benchmark readiness:

```text
training_benchmarks count = 5
benchmark n_samples = 360 for each captured benchmark
benchmark n_classes = 2 for each captured benchmark
benchmark lineage ids present for all 5 captured benchmarks
```

Track 2 same-reality determination:

```text
Track 2 sees the same partial corpus reality as Track 1: one available recording, one patient, and only "background" labels.
```

## 5. Application Forensics

Upload:

```text
No upload occurred in FAILURE 1. The failure happened before upload construction, while opening chb01_03.edf.
```

Analysis:

```text
No analysis occurred in FAILURE 1.
```

Prediction:

```text
No prediction occurred in FAILURE 1.
```

Report generation:

```text
No report generation occurred in FAILURE 1.
```

Workflow readiness:

```text
No workflow readiness was emitted in FAILURE 1.
```

Track 3 same-reality determination:

```text
Track 3 sees the same corpus path as Track 1 and fails on the same missing file, chb01_03.edf.
```

## 6. Operations Forensics

Qualification:

```text
No operations qualification occurred in FAILURE 3. The failure happened before qualification, while opening chb01_03.edf.
```

Health:

```text
No operations health output was emitted in FAILURE 3.
```

Diagnostics:

```text
No diagnostics output was emitted in FAILURE 3.
```

Deployment readiness:

```text
No deployment readiness output was emitted in FAILURE 3.
```

Track 4 same-reality determination:

```text
Track 4 sees the same corpus path as Track 1 and fails on the same missing file, chb01_03.edf.
```

## 7. Proven Root Cause

The proven root cause is incomplete CHB-MIT corpus acquisition.

Runtime evidence:

```text
chb01_entries = ["chb01-summary.txt", "chb01_01.edf", "chb01_03.edf.part"]
chb01_edf_files = ["chb01_01.edf"]
exists:chb_mit\chb01\chb01_03.edf = false
```

Acquisition evidence:

```text
n_items = 3
n_acquired = 2
chb01/chb01_03.edf state = unavailable
chb01/chb01_03.edf note = download disabled (allow_download=False)
availability_state = partially_downloaded
```

Readiness evidence:

```text
dataset_ready_for_training = false
readiness classification = PARTIALLY_READY
findings = ["acquisition=0.3", "labels=0.5", "training=0.67"]
```

Downstream evidence:

```text
Track 2: n_classes = 1, class_names = ["background"], training_ready_models = []
Track 3: FileNotFoundError for chb01_03.edf before upload/analysis/prediction/reporting
Track 4: FileNotFoundError for chb01_03.edf before operations qualification
```

## 8. Recommended Remediation

Recommended remediation, without implementation in this report:

1. Complete acquisition of the missing real CHB-MIT recording:

```text
chb01/chb01_03.edf
```

2. Ensure the partial artifact is reconciled by the authoritative acquisition path:

```text
chb01/chb01_03.edf.part
```

3. Re-run the authoritative dataset acquisition/integration path so runtime evidence changes from:

```text
n_acquired = 2
availability_state = partially_downloaded
readiness classification = PARTIALLY_READY
```

to a complete acquisition/readiness state produced by the existing readiness engine.

4. Re-run Track 2 so the dataset bundle is generated from the completed corpus and produces runtime evidence for:

```text
n_classes > 1
ready_models not empty
```

5. Re-run Track 3 and Track 4 real-corpus workflows after the completed corpus is present, preserving existing upload, analysis, prediction, report, qualification, readiness, lineage, and audit paths.

