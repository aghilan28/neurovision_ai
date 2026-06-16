import numpy as np

FEATURES = [
    "mean",
    "std",
    "variance",
    "rms",
    "max",
    "min",
    "ptp",
    "line_length",
    "zero_crossings",
    "iqr",
    "mad",
    "sample_entropy",
    "perm_entropy",
    "higuchi_fd",
    "petrosian_fd",
    "wavelet_energy_0",
    "wavelet_energy_1",
    "wavelet_energy_2",
    "wavelet_energy_3",
    "wavelet_energy_4",
    "wavelet_energy_5",
    "spectral_entropy",
    "delta_power",
    "delta_relative",
    "theta_power",
    "theta_relative",
    "alpha_power",
    "alpha_relative",
    "beta_power",
    "beta_relative",
    "gamma_power",
    "gamma_relative"
]

expanded = []

for f in FEATURES:

    expanded.append(f + "_mean")
    expanded.append(f + "_std")
    expanded.append(f + "_max")

print("=" * 80)
print("PHASE 4A FEATURE FOUNDATION")
print("=" * 80)

print()
print("Base Features :", len(FEATURES))
print("Expanded      :", len(expanded))

print()
print(expanded[:20])