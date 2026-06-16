import antropy as ant
import pywt
import numpy as np


def wavelet_energy(signal):

    coeffs = pywt.wavedec(
        signal,
        "db4",
        level=5
    )

    energies = []

    for c in coeffs:
        energies.append(
            np.sum(c**2)
        )

    return energies


def nonlinear_features(signal):

    return {
        "sample_entropy":
            ant.sample_entropy(signal),

        "perm_entropy":
            ant.perm_entropy(signal),

        "higuchi_fd":
            ant.higuchi_fd(signal),

        "petrosian_fd":
            ant.petrosian_fd(signal),
    }