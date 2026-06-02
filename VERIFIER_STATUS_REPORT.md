# Verifier Status Report

Generated: 2026-06-01

## Evidence Sources

- Historical baseline sweep: `certification_evidence_20260601_211116/`
- Closure continuation sweep: `certification_closure_evidence_20260601_221954/`
- Missing verifier continuation run: `certification_closure_evidence_20260601_224927/`

The historical baseline contains pre-remediation failures and is treated as baseline context, not final status. Final status uses the latest successful closure evidence per verifier plus the final missing-verifier continuation run.

## Totals

- Total verifier scripts discovered: 43
- Passed verifiers: 42
- Failed verifiers: 1
- Missing verifiers: 0
- Incomplete verifiers: 0

## Passed Verifiers

Closure evidence from `certification_closure_evidence_20260601_221954/`:

- `verify_dbe1_asgi_entrypoint.py`
- `verify_dbe2_docker_deployment.py`
- `verify_dbe3_duplicate_upload.py`
- `verify_dbe4_persistence.py`
- `verify_dbe5_authentication_reliability.py`
- `verify_drp1_dataset_integration.py`
- `verify_drp2_production_models.py`
- `verify_drp3_serving_platform.py`
- `verify_drp4_persistence_platform.py`
- `verify_drp5_security_platform.py`
- `verify_drp6_clinical_validation.py`
- `verify_mp1_model_provisioning.py`
- `verify_mp3_model_lifecycle.py`
- `verify_mp4_source_of_truth.py`
- `verify_productization_p1.py`
- `verify_productization_p10.py`
- `verify_productization_p2.py`
- `verify_productization_p3.py`
- `verify_productization_p4.py`
- `verify_productization_p5.py`
- `verify_productization_p6.py`
- `verify_productization_p7.py`
- `verify_productization_p8.py`
- `verify_productization_p9.py`
- `verify_track1_real_data.py`
- `verify_track2_real_models.py`
- `verify_track3_application.py`
- `verify_track4_operations.py`
- `verify_v1.py`
- `verify_v1_p5_p6.py`
- `verify_v2.py`

Continuation evidence from `certification_closure_evidence_20260601_224927/`:

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

## Failed Verifiers

- `verify_v4_p9_p10.py`
  - Evidence: `certification_closure_evidence_20260601_224927/verifier_verify_v4_p9_p10.txt`
  - Exit code: 1
  - Runtime: 222.7 seconds
  - Failure: readiness assessment incomplete; eight readiness domains failed with score `0.00`.

## Missing Verifiers

None.

## Incomplete Verifiers

None after the continuation run. Earlier interruption evidence is superseded by `certification_closure_evidence_20260601_224927/`.
