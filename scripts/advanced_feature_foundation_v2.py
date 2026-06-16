import pywt
import antropy as ant
import numpy as np

print("=" * 80)
print("NEUROVISION FEATURE FOUNDATION V2")
print("=" * 80)

print("PyWavelets:", pywt.__version__)
print("Antropy OK")

x = np.random.randn(1024)

print("Sample Entropy:", ant.sample_entropy(x))
print("Permutation Entropy:", ant.perm_entropy(x))

coeffs = pywt.wavedec(x, "db4", level=4)

print("Wavelet Levels:", len(coeffs))

print("\nFOUNDATION READY")