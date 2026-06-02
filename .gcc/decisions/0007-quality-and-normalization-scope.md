# DR-0007 · Quality assessed pre-normalization; per-window normalization deferral

- **Status:** Accepted · **Phase:** V1-P2 · **Date:** caller-supplied

## Context
The directive's stage order is: …montage → normalization → windowing → output
validation → artifact (quality) reporting. But amplitude-based quality checks
(saturation, line noise) are meaningless after z-score normalization, and the
`per_channel_window` normalization scope logically happens during windowing.

## Decision
- **Quality is computed on the post-filter/montage, _pre-normalization_ signal** so
  amplitude/line-noise checks remain meaningful, while the quality *stage* is still
  reported at the directive's position (after output validation).
- **Per-window normalization** is applied *inside* the windowing stage; the
  normalization stage then records itself as `skipped` with an explicit deferral
  note (no hidden steps).

## Alternatives considered
1. **Assess quality on the normalized signal** — would defeat amplitude thresholds.
   Rejected.
2. **Forbid per-window normalization** — reduces flexibility for no benefit.
   Rejected; deferral keeps it explicit and recorded.

## Consequences
- Quality findings stay scientifically meaningful; normalization scope is explicit
  and fully captured in stage results + lineage.

## Rules / principles invoked
AP-3, AP-5, AP-6, NR-9; quality is **report-only** (never mutates data).
