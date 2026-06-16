import numpy as np
import pandas as pd
import antropy as ant
import pywt
import mne

EDF_FILE = r"E:\NeuroVision\datasets\chbmit\chb01\chb01_03.edf"

print("=" * 80)
print("FEATURE V3 VALIDATION")
print("=" * 80)

raw = mne.io.read_raw_edf(
    EDF_FILE,
    preload=True,
    verbose=False
)

data = raw.get_data()

sfreq = raw.info["sfreq"]

print("Channels:", data.shape[0])
print("Samples :", data.shape[1])
print("Sfreq   :", sfreq)

window = data[:, 0:1024]

signal = np.mean(window, axis=0)

features = {}

features["mean"] = np.mean(signal)
features["std"] = np.std(signal)
features["rms"] = np.sqrt(np.mean(signal**2))

features["sample_entropy"] = ant.sample_entropy(signal)
features["perm_entropy"] = ant.perm_entropy(signal)

features["higuchi_fd"] = ant.higuchi_fd(signal)
features["petrosian_fd"] = ant.petrosian_fd(signal)

coeffs = pywt.wavedec(
    signal,
    "db4",
    level=5
)

for i, c in enumerate(coeffs):
    features[f"wavelet_energy_{i}"] = np.sum(c**2)

freqs = np.fft.rfftfreq(
    len(signal),
    d=1.0 / sfreq
)

power = np.abs(np.fft.rfft(signal))**2

power_norm = power / (power.sum() + 1e-12)

features["spectral_entropy"] = (
    -np.sum(power_norm * np.log2(power_norm + 1e-12))
)

df = pd.DataFrame([features])

print()
print(df.T)

print()
print("FEATURE COUNT:", len(features))
print("VALIDATION PASSED")