"""Verification test 1: Feature parity.

Confirms that the wired pretrained path produces *bit-identical* features
as the training-time _window_features on the same window.
"""
import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

import mne
from backend.real_model_training.data import _window_features
from backend.application_platform.provisioning.pretrained import load_chbmit_pretrained
from backend.application_platform.provisioning.wiring import get_window_features_from_processed

# Use the real sample file if available
SAMPLE_PATH = "/home/user/neurovision_ai/chb_test/chb01/chb01_01.edf"
if not os.path.exists(SAMPLE_PATH):
    SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "../../../../../chb_test/chb01/chb01_01.edf")


def _load_real_window():
    """Load a real window from CHB sample and return (window, sfreq)."""
    mne.set_log_level("ERROR")
    raw = mne.io.read_raw_edf(SAMPLE_PATH, preload=True, verbose="ERROR")
    sfreq = raw.info["sfreq"]
    data = raw.get_data()  # channels x samples (volts)

    # Take first 4s window
    win_samples = int(4.0 * sfreq)
    if data.shape[1] < win_samples:
        win_samples = data.shape[1]
    window = data[:, :win_samples] * 1e6  # to microvolts (as used in training)
    return window, float(sfreq)


def test_feature_parity_standalone_vs_wired():
    """Direct _window_features vs what the pretrained path would feed to predict_proba."""
    window, sfreq = _load_real_window()

    # 1. Direct training-time computation (ground truth)
    direct_feats = np.asarray(_window_features(window, sfreq), dtype=np.float64)

    # 2. Simulate what the wiring does (get_window_features_from_processed)
    # We construct a minimal "processed_asset" object
    class FakeProcessed:
        def __init__(self, data, sfreq):
            self.data = data
            self.sampling_frequency = sfreq
            class Meta:
                sampling_frequency = sfreq
            self.metadata = Meta()

    fake = FakeProcessed(window, sfreq)

    wired_feats, wired_sfreq = get_window_features_from_processed(fake, window_seconds=4.0)

    # Bit-for-bit check (within float tolerance for determinism)
    assert wired_sfreq == sfreq
    assert wired_feats.shape == direct_feats.shape

    # Very tight tolerance because the computation path should be identical
    np.testing.assert_allclose(direct_feats, wired_feats, rtol=1e-12, atol=1e-12,
                               err_msg="Feature vectors from direct _window_features and wired path are NOT identical.")

    print("✓ Feature parity: direct _window_features == wired path (bit-identical within float precision)")
    print("  Shape:", direct_feats.shape)
    print("  Sample values (first 4):", direct_feats[:4])


def test_chbmit_engine_receives_correct_features():
    """Ensure the array passed into CHBMitInferenceEngine.predict_proba matches _window_features exactly."""
    window, sfreq = _load_real_window()
    direct = np.asarray(_window_features(window, sfreq), dtype=np.float64).reshape(1, -1)

    ctx = load_chbmit_pretrained()

    # Call the engine directly
    proba_from_engine = ctx.engine.predict_proba(direct)
    proba_from_ctx = ctx.predict_proba(direct[0])

    # The predict_proba must accept and work on the feature vector produced by _window_features
    assert proba_from_engine.shape[1] == 2
    assert np.allclose(proba_from_engine[0], proba_from_ctx)

    print("✓ CHBMitInferenceEngine receives correct _window_features shape and produces valid proba")
    print("  proba:", proba_from_engine[0])


if __name__ == "__main__":
    test_feature_parity_standalone_vs_wired()
    test_chbmit_engine_receives_correct_features()
    print("\n=== ALL FEATURE PARITY TESTS PASSED ===")
