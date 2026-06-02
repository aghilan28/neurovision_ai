"""Tests for montage definitions, mapping, and application."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing.montages import (
    apply_montage,
    check_compatibility,
    get_montage,
    normalize_label,
    resolve_alias,
)
from preprocessing.montages.apply import MontageError
from preprocessing.schemas.enums import MissingChannelPolicy


def test_label_normalization_and_alias():
    assert normalize_label("EEG Fp1-REF") == "FP1"
    assert resolve_alias("T3") == "T7"
    assert resolve_alias("T5") == "P7"


def test_referential_identity_is_passthrough():
    sig = np.arange(12, dtype=float).reshape(3, 4)
    out, names, result = apply_montage(sig, ("FP1", "C3", "O1"), get_montage("identity"))
    assert np.array_equal(out, sig)
    assert names == ("FP1", "C3", "O1")
    assert result.montage_type == "referential"


def test_average_reference_zero_mean_across_channels():
    sig = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    out, names, _ = apply_montage(sig, ("FP1", "C3", "O1"), get_montage("average_reference"))
    assert np.allclose(out.mean(axis=0), 0.0)
    assert all(n.endswith("-AVG") for n in names)


def test_bipolar_computes_differences():
    names_in = ("FP1", "F7", "T7", "P7", "O1")
    sig = np.array([[10.0], [4.0], [1.0], [0.5], [0.0]])
    out, names, result = apply_montage(
        sig, names_in, get_montage("longitudinal_bipolar_double_banana"),
        missing_policy=MissingChannelPolicy.SKIP,
    )
    # FP1-F7 derivation == 10 - 4 == 6
    idx = names.index("FP1-F7")
    assert out[idx, 0] == pytest.approx(6.0)
    # Derivations needing absent channels are skipped, not fabricated.
    assert "F7-T7" in names  # all present here
    assert result.skipped_derivations  # e.g. FP1-F3 needs F3 which is absent


def test_bipolar_alias_resolution_matches_old_naming():
    # Old 10-20 names (T3/T5) must resolve to canonical (T7/P7) used by the montage.
    names_in = ("F7", "T3", "T5", "O1")
    sig = np.array([[5.0], [3.0], [2.0], [1.0]])
    out, names, _ = apply_montage(
        sig, names_in, get_montage("longitudinal_bipolar_double_banana"),
        missing_policy=MissingChannelPolicy.SKIP,
    )
    assert "F7-T7" in names  # F7 - T3(=T7)
    assert out[names.index("F7-T7"), 0] == pytest.approx(2.0)


def test_missing_policy_error_raises():
    names_in = ("FP1", "F7")  # insufficient for the full montage
    sig = np.zeros((2, 4))
    with pytest.raises(MontageError):
        apply_montage(
            sig, names_in, get_montage("longitudinal_bipolar_double_banana"),
            missing_policy=MissingChannelPolicy.ERROR,
        )


def test_compatibility_reports_missing():
    ok, missing = check_compatibility(("FP1", "F7"), get_montage("longitudinal_bipolar_double_banana"))
    assert not ok
    assert "C3" in missing
