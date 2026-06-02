# DR-0003 · `preprocessing` defines its own `RawRecording` input contract

- **Status:** Accepted · **Phase:** V1-P2 · **Date:** caller-supplied

## Context
The preprocessing pipeline needs an input type (signal + channels + sampling rate).
`preprocessing` is the dependency-graph **leaf** and must import no internal module
(Rule D / NR-8). It therefore cannot import a data-layer type.

## Decision
`preprocessing` defines its own minimal input contract,
`preprocessing.schemas.signal.RawRecording`. The `datasets` layer (which sits above
preprocessing and *may* import it) is responsible for adapting its EDF reading into
a `RawRecording` when it needs DSP.

## Alternatives considered
1. **Share a common type from a new leaf module** — would change the architecture
   (a new shared module) and needs its own governance decision; premature for V1.
2. **Import a `datasets` type into preprocessing** — directly violates NR-8.
   Rejected.
3. **Preprocessing owns its input (chosen)** — small, self-contained, preserves the
   acyclic graph. Cost: a little conceptual duplication of "signal + channels + fs".

## Consequences
- `preprocessing` stays a pure leaf (verified by `tests/test_boundaries.py`).
- A thin adapter belongs in `datasets`/`ml` when they call preprocessing (future).

## Rules / principles invoked
AP-7 (boundaries), NR-8 (import rules / acyclic graph), AP-1 (no premature
architecture change).
