import numpy as np
import antropy as ant
import pywt

def extract_v3_features(signal, sfreq=256):

    features = {}

    features["mean"] = float(np.mean(signal))
    features["std"] = float(np.std(signal))
    features["rms"] = float(np.sqrt(np.mean(signal**2)))

    features["max"] = float(np.max(signal))
    features["min"] = float(np.min(signal))
    features["ptp"] = float(np.ptp(signal))

    features["variance"] = float(np.var(signal))

    median = np.median(signal)

    features["mad"] = float(
        np.median(np.abs(signal - median))
    )

    q75, q25 = np.percentile(signal,[75,25])

    features["iqr"] = float(q75-q25)

    features["line_length"] = float(
        np.sum(np.abs(np.diff(signal)))
    )

    features["zero_crossings"] = float(
        np.sum(np.diff(np.sign(signal)) != 0)
    )

    features["sample_entropy"] = float(
        ant.sample_entropy(signal)
    )

    features["perm_entropy"] = float(
        ant.perm_entropy(signal)
    )

    features["higuchi_fd"] = float(
        ant.higuchi_fd(signal)
    )

    features["petrosian_fd"] = float(
        ant.petrosian_fd(signal)
    )

    fft = np.abs(np.fft.rfft(signal))**2

    freqs = np.fft.rfftfreq(
        len(signal),
        d=1.0/sfreq
    )

    total_power = fft.sum()+1e-12

    bands = {
        "delta":(0.5,4),
        "theta":(4,8),
        "alpha":(8,13),
        "beta":(13,30),
        "gamma":(30,45)
    }

    for band,(lo,hi) in bands.items():

        mask = (freqs>=lo) & (freqs<hi)

        p = fft[mask].sum()

        features[f"{band}_power"] = float(p)
        features[f"{band}_relative"] = float(p/total_power)

    pnorm = fft/(total_power)

    features["spectral_entropy"] = float(
        -np.sum(pnorm*np.log2(pnorm+1e-12))
    )

    coeffs = pywt.wavedec(
        signal,
        "db4",
        level=5
    )

    for i,c in enumerate(coeffs):

        features[f"wavelet_energy_{i}"] = float(
            np.sum(c**2)
        )

    return features


if __name__ == "__main__":

    test = np.random.randn(1024)

    f = extract_v3_features(test)

    print("="*80)
    print("FEATURE V3 SANDBOX")
    print("="*80)

    print()
    print("FEATURE COUNT:", len(f))
    print()

    for k in sorted(f.keys()):
        print(k)