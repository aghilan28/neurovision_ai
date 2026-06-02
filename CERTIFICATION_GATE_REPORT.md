# Certification Gate Report

Generated: 2026-06-01

## Gate Results

| Gate | Result | Evidence |
|---|---:|---|
| Pytest | PASS | `py -3.12 -m pytest -q` completed successfully; all tests passed with scipy runtime warnings only. |
| Test collection | PASS | `py -3.12 -m pytest --collect-only -q` collected tests successfully across the full suite. |
| All verifier scripts | FAIL | 42/43 verifiers passed; `verify_v4_p9_p10.py` failed. |
| Import integrity | PASS | Imported `backend`, `datasets`, `ml`, `validation`, `operations`, `certification`, `preprocessing`, `backend.application_platform.api`, `validation.harness`, and `validation.util`. |
| Package integrity | FAIL | `py -3.12 -m pip check` reported `roboflow 1.3.8` requires `opencv-python-headless==4.10.0.84`, but `4.11.0.86` is installed. `pip show neurovision-ai` did not find an installed distribution in the active environment. |
| Determinism | PASS | Covered by passing determinism criteria in productization, track, V1, V2, V3, and V4 verifier evidence except the V4-P10 readiness gap. |
| Platform compatibility | PARTIAL | Windows import/resource issues are remediated enough for closure verifiers and pytest to pass; package environment conflict remains. |
| API readiness handling | PASS | Covered by passing DBE, application platform, Track 3, and pytest evidence. |
| Dataset identity stability | PASS | Covered by passing DRP-1, DRP-2, Track 1, Track 2, and related real-corpus evidence. |
| Release workflows | FAIL | Release certification cannot pass while `verify_v4_p9_p10.py` and package integrity remain failing. |

## Runtime Evidence

- Full pytest: pass, runtime approximately 214 seconds.
- Import integrity probe: pass.
- Package integrity probe: fail due dependency conflict.
- Final missing verifier run: `certification_closure_evidence_20260601_224927/missing_verifier_summary.json`.
- Failing verifier log: `certification_closure_evidence_20260601_224927/verifier_verify_v4_p9_p10.txt`.

## Gate Decision

Certification gate is not fully satisfied. Runtime proof supports a strong remediation posture, but one certification verifier and one package integrity check remain failing.
