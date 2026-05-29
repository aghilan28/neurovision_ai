# Extension Points (documented, not built)

Per Rule **NR-13** (stay in scope) and **NR-5** (recorded decisions), these are
**deliberately not implemented** in V1-P2. They are the seams where later work
attaches **without reshaping** the stage contracts or the pipeline (Principle
**AP-1**). Activating any requires a recorded governance decision.

## 1. Additional filters
- **Where:** `preprocessing/filters/` — add a design + apply module and extend the
  filter chain order explicitly.
- **Examples (not built):** adaptive/Wiener denoising, ICA-based artifact removal,
  re-referencing filters, wavelet denoising. ICA in particular is stateful/fit-based
  and would need its own determinism + fit/transform contract.

## 2. Additional montages
- **Where:** `preprocessing/montages/definitions.py` — register a new
  `MontageDefinition` (e.g. transverse bipolar, circumferential, source montages).
- **Invariant:** derivations use canonical electrode names + alias resolution;
  missing channels handled explicitly.

## 3. Additional normalization methods / scopes
- **Where:** `preprocessing/normalization/` — add a method to the enum + a
  deterministic implementation. Any fit-based scaler (e.g. dataset-level stats)
  must record its fitted parameters in lineage and respect patient-disjoint
  boundaries (no leakage across splits) — that coupling is why it is deferred.

## 4. Spectral / feature transforms (PSD, spectrograms)
- **Where:** a new stage or a sibling module; would extend `WindowSet` consumers.
  Kept out of V1-P2 to keep the foundation to *signal standardization* only.

## 5. Streaming / chunked processing (V3)
- **Where:** a streaming front-end that feeds fixed-size buffers into the same
  stage functions; must preserve determinism and per-window semantics.

---

**Default-deny.** Anything not implemented and not listed here is out of scope until
a governance decision adds it.
