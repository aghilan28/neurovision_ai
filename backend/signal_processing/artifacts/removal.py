"""Deterministic EEG artifact removal / repair engine (P2-F).

Implements the mandated removal methods — **ICA-based removal**, **adaptive
filtering**, **interpolation**, **channel repair**, and **noise suppression** — each
as a deterministic, reproducible, side-effect-free transform: it returns a *new*
array and never mutates its input, so the raw EEG remains immutable and every
modification is auditable.

The ICA is a compact, self-contained FastICA (symmetric, log-cosh) with a fixed
(non-random) initialization, so the decomposition is bit-for-bit reproducible
without any stochastic state or extra dependency.
"""

from __future__ import annotations

import numpy as np

from ..filtering.filters import FilteringEngine
from ..version import SIGNAL_REMOVAL_VERSION

_EPS = 1e-12
_FRONTAL_PREFIXES = ("fp", "af")
_OCULAR_CORR = 0.50


def _frontal_indices(labels: tuple[str, ...]) -> list[int]:
    return [i for i, lab in enumerate(labels) if lab.lower().startswith(_FRONTAL_PREFIXES)]


def _fastica(X: np.ndarray, max_iter: int = 200, tol: float = 1e-5):
    """Deterministic symmetric FastICA. Returns (S, W_white, A_white, mean, ok).

    ``S`` are the estimated sources (n_comp, n_samples); reconstruct feature space
    with ``A_white @ (W.T @ S) + mean`` where rows of ``S`` may be zeroed to drop a
    component. Initialization is the identity (no randomness)."""
    n_features, n_samples = X.shape
    mean = X.mean(axis=1, keepdims=True)
    Xc = X - mean
    cov = (Xc @ Xc.T) / max(1, n_samples)
    eigval, eigvec = np.linalg.eigh(cov)
    order = np.argsort(eigval)[::-1]
    eigval, eigvec = eigval[order], eigvec[:, order]
    keep = eigval > 1e-9
    n_comp = int(np.sum(keep))
    if n_comp < 1:
        return None, None, None, mean, False
    eigval, eigvec = eigval[:n_comp], eigvec[:, :n_comp]
    W_white = (eigvec / np.sqrt(eigval)).T          # (n_comp, n_features)
    A_white = eigvec * np.sqrt(eigval)              # (n_features, n_comp)
    Xw = W_white @ Xc                                # (n_comp, n_samples)

    W = np.eye(n_comp)                               # deterministic init
    for _ in range(max_iter):
        WX = W @ Xw
        g = np.tanh(WX)
        g_prime = 1.0 - g ** 2
        W_new = (g @ Xw.T) / n_samples - (g_prime.mean(axis=1)[:, None] * W)
        # symmetric decorrelation: W = (W Wt)^-1/2 W
        u, s, _ = np.linalg.svd(W_new @ W_new.T)
        W_dec = (u @ np.diag(1.0 / np.sqrt(s + _EPS)) @ u.T) @ W_new
        if np.max(np.abs(np.abs(np.sum(W_dec * W, axis=1)) - 1.0)) < tol:
            W = W_dec
            break
        W = W_dec
    S = W @ Xw
    return (S, W, A_white, mean, True)


class ArtifactRemovalEngine:
    """Deterministic, side-effect-free artifact removal / repair operations."""

    version = SIGNAL_REMOVAL_VERSION

    def __init__(self) -> None:
        self._filters = FilteringEngine()

    # --- ICA-based ocular/artifact removal ------------------------------------
    def ica_remove(self, data: np.ndarray, sfreq: float, channel_labels: tuple[str, ...],
                   *, corr_threshold: float = _OCULAR_CORR) -> tuple[np.ndarray, dict]:
        """Remove components correlated with frontal (ocular) activity via ICA."""
        X = np.ascontiguousarray(data.astype(np.float64))
        if X.shape[0] < 2 or X.shape[1] < 8:
            return X.copy(), {"method": "ica", "excluded": [], "note": "insufficient data for ICA"}
        try:
            S, W, A_white, mean, ok = _fastica(X)
            if not ok:
                return X.copy(), {"method": "ica", "excluded": [], "note": "ICA did not converge"}
            frontal = _frontal_indices(channel_labels)
            if frontal:
                ref = X[frontal].mean(axis=0)
                ref = ref - ref.mean()
                excluded = []
                for k in range(S.shape[0]):
                    sk = S[k] - S[k].mean()
                    denom = (np.std(sk) * np.std(ref)) + _EPS
                    corr = float(np.abs(np.mean(sk * ref) / denom))
                    if corr >= corr_threshold:
                        excluded.append(k)
            else:
                excluded = []
            S_mod = S.copy()
            for k in excluded:
                S_mod[k] = 0.0
            Xw_recon = W.T @ S_mod
            X_recon = A_white @ Xw_recon + mean
            return np.ascontiguousarray(X_recon), {
                "method": "ica", "n_components": int(S.shape[0]),
                "excluded": [int(k) for k in excluded], "corr_threshold": float(corr_threshold)}
        except np.linalg.LinAlgError as exc:
            return X.copy(), {"method": "ica", "excluded": [], "note": f"linalg error: {exc}"}

    # --- adaptive (regression) filtering --------------------------------------
    def adaptive_filter(self, data: np.ndarray, channel_labels: tuple[str, ...],
                        reference: np.ndarray | None = None) -> tuple[np.ndarray, dict]:
        """Least-squares removal of a reference (default: frontal mean) from each
        non-reference channel — a deterministic adaptive (EOG-regression) canceller."""
        X = np.ascontiguousarray(data.astype(np.float64))
        frontal = _frontal_indices(channel_labels)
        if reference is None:
            if not frontal:
                return X.copy(), {"method": "adaptive_filter", "note": "no reference available"}
            reference = X[frontal].mean(axis=0)
        ref = reference.astype(np.float64)
        ref = ref - ref.mean()
        var = float(np.dot(ref, ref))
        out = X.copy()
        targets = [i for i in range(X.shape[0]) if i not in frontal] or list(range(X.shape[0]))
        if var <= _EPS:
            return out, {"method": "adaptive_filter", "note": "degenerate reference"}
        betas = {}
        for i in targets:
            beta = float(np.dot(X[i] - X[i].mean(), ref) / var)
            out[i] = X[i] - beta * ref
            betas[channel_labels[i] if i < len(channel_labels) else str(i)] = round(beta, 6)
        return out, {"method": "adaptive_filter", "n_targets": len(targets), "betas": betas}

    # --- temporal interpolation of non-finite samples -------------------------
    def interpolation(self, data: np.ndarray) -> tuple[np.ndarray, dict]:
        """Linearly interpolate non-finite samples within each channel (over time)."""
        X = np.ascontiguousarray(data.astype(np.float64))
        n_repaired = 0
        t = np.arange(X.shape[1])
        for i in range(X.shape[0]):
            bad = ~np.isfinite(X[i])
            if bad.any() and (~bad).sum() >= 2:
                X[i, bad] = np.interp(t[bad], t[~bad], X[i, ~bad])
                n_repaired += int(bad.sum())
            elif bad.any():
                X[i, bad] = 0.0
                n_repaired += int(bad.sum())
        return X, {"method": "interpolation", "n_samples_repaired": n_repaired}

    # --- spatial channel repair ------------------------------------------------
    def channel_repair(self, data: np.ndarray, bad_channels: tuple[int, ...]) -> tuple[np.ndarray, dict]:
        """Replace each bad channel by the mean of the remaining good channels."""
        X = np.ascontiguousarray(data.astype(np.float64))
        bad = sorted(set(int(b) for b in bad_channels if 0 <= int(b) < X.shape[0]))
        good = [i for i in range(X.shape[0]) if i not in bad]
        if bad and good:
            repl = X[good].mean(axis=0)
            for b in bad:
                X[b] = repl
        return X, {"method": "channel_repair", "repaired_channels": bad,
                   "used_good_channels": len(good)}

    # --- noise suppression (notch + bandpass) ----------------------------------
    def noise_suppression(self, data: np.ndarray, sfreq: float, *, powerline_hz: float = 60.0,
                          band: tuple[float, float] = (0.5, 40.0)) -> tuple[np.ndarray, dict]:
        """Deterministic noise suppression: powerline notch + in-band bandpass."""
        X = np.ascontiguousarray(data.astype(np.float64))
        nyq = sfreq / 2.0 if sfreq > 0 else 0.0
        applied = []
        if nyq > 0 and powerline_hz < nyq:
            X, _ = self._filters.notch(X, sfreq, powerline_hz)
            applied.append(f"notch@{powerline_hz}")
        lo, hi = band
        if nyq > 0 and 0 < lo < hi < nyq:
            X, _ = self._filters.bandpass(X, sfreq, lo, hi)
            applied.append(f"bandpass[{lo}-{hi}]")
        return X, {"method": "noise_suppression", "applied": applied}
