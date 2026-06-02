# `preprocessing/docs/` — DSP Foundation Documentation (V1-P2)

| Document | Purpose |
|----------|---------|
| [`PIPELINE.md`](./PIPELINE.md) | The pipeline stages, their order, inputs/outputs, and failure behaviour. |
| [`SCIENTIFIC_RATIONALE.md`](./SCIENTIFIC_RATIONALE.md) | Why each default DSP choice was made (resampling rate, filter band, montage, normalization). |
| [`DETERMINISM.md`](./DETERMINISM.md) | How determinism, versioning, and reproducibility are guaranteed. |
| [`EXTENSION_POINTS.md`](./EXTENSION_POINTS.md) | Documented-but-unbuilt seams (future filters/montages/normalization) — built only via governance decision. |

> These describe the implementation; the V0 **constitution/architecture** and the
> module boundary contract (`preprocessing/README.md`) govern intent.
