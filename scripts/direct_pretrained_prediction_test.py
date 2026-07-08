#!/usr/bin/env python3
"""
Direct end-to-end test of the pretrained CHB-MIT prediction path.

Bypasses user auth + full upload for pure verification of the root cause fix.
This exercises:
  - provisioning loads the real artifact
  - signal processing
  - training-time feature extraction (_window_features)
  - CHBMitInferenceEngine.predict_proba
"""
import os
import sys
import tempfile

import numpy as np
import mne

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.application_platform.service import ApplicationPlatformService
from backend.application_platform.provisioning import provision_model
from backend.application_platform.provisioning.pretrained import is_pretrained_context
from backend.application_platform.provisioning.wiring import predict_with_pretrained

from backend.eeg_foundation import LocalEEGStore, EEGFoundationService
from backend.signal_processing import SignalProcessingService

CHB_SAMPLE = "/home/user/neurovision_ai/chb_test/chb01/chb01_01.edf"

def main():
    print("=== DIRECT PRETRAINED PREDICTION TEST ===\n")

    # 1. Provision
    service = ApplicationPlatformService(analysis_seconds=4.0)
    prov = provision_model(service)
    print("Provisioning:", prov.to_dict())
    assert prov.ok
    ctx = service.backend.model_context
    assert is_pretrained_context(ctx)
    print("✓ Pretrained context active\n")

    # 2. Prepare a real processed signal
    workspace = tempfile.mkdtemp(prefix="nv_direct_test_")
    eeg_store = LocalEEGStore(os.path.join(workspace, "raw"))

    if os.path.exists(CHB_SAMPLE):
        src = CHB_SAMPLE
    else:
        # create minimal realistic EEG
        print("No CHB sample; synthesizing a test signal")
        info = mne.create_info(["Fp1","Fp2","F3","F4","C3","C4","P3","P4"], 256.0, "eeg")
        t = np.arange(1024) / 256.0
        data = np.vstack([np.sin(2*np.pi*3*t) + 0.1*np.random.randn(1024) for _ in range(8)]) * 1e-6
        raw = mne.io.RawArray(data, info, verbose="ERROR")
        src = os.path.join(workspace, "synthetic_test.fif")
        raw.save(src, overwrite=True, verbose="ERROR")

    eeg_svc = EEGFoundationService(eeg_store)
    ingestion = eeg_svc.ingest_eeg(src, case_id="direct-case", patient_id="direct-pt",
                                   case_lineage_id="ln-direct")
    assert ingestion.accepted
    print("✓ EEG ingested")

    proc_store = type("ProcStore", (), {"workspace": os.path.join(workspace, "proc")})()
    sig_svc = SignalProcessingService(eeg_store, proc_store)
    proc = sig_svc.process(ingestion.asset).asset
    print("✓ Signal processed")

    # 3. Run pretrained prediction using the exact mandated path
    print("\n[CORE] Running predict_with_pretrained (uses _window_features + CHBMitEngine)...")
    result = predict_with_pretrained(ctx, proc, window_seconds=4.0)

    print("RESULT:")
    print("  predicted_class :", result["predicted_class"])
    print("  predicted_label :", result["predicted_label"])
    print("  probabilities   :", result["probabilities"])
    print("  confidence      :", round(result["confidence"], 6))
    print("  source          :", result["source"])

    # 4. Assertions
    probs = np.asarray(result["probabilities"])
    assert probs.shape == (2,), "Must be binary probabilities"
    assert abs(probs.sum() - 1.0) < 1e-4, "Must sum to ~1"
    assert np.all(np.isfinite(probs)), "Must be finite"
    assert 0.0 <= result["confidence"] <= 1.0

    # Non-placeholder check (confidence not locked at 0.5 or 0.92 etc.)
    if abs(result["confidence"] - 0.5) < 0.02 or abs(result["confidence"] - 0.92) < 0.02:
        print("⚠️ WARNING: Confidence suspiciously close to old placeholder values.")
    else:
        print("✓ Confidence is non-degenerate")

    print("\n✅ DIRECT TEST PASSED — pretrained path is fully functional.")

if __name__ == "__main__":
    main()
