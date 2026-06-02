# DR-0009 · Annotation-text → class mapping for distribution *analysis*

- **Status:** Accepted · **Phase:** V1-P3 · **Date:** caller-supplied

## Context
The Dataset Intelligence Layer must analyze class distribution (SZ / IIC /
background), but EDF/EDF+ files carry **free-text annotations**, not formal labels.
A mapping from text to canonical classes is needed to *count* classes — without
introducing hidden labelling assumptions or modifying data.

## Decision
Provide an explicit, ordered keyword ruleset (`distributions/labels.py`,
`DEFAULT_LABEL_MAPPING`) mapping annotation text to ACNS-aligned
`EegClass` values (SZ/LPD/GPD/LRDA/GRDA/Other/Background). The mapping is
configurable and fully recorded in the report. Class counts are at the
*annotation* level; `labeled_record_fraction` measures coverage.
**No balancing, no relabeling, no modification of the underlying data.**

## Alternatives considered
1. **Assume a formal label field** — none exists in EDF/EDF+; would be a hidden
   assumption. Rejected.
2. **Skip class analysis entirely** — the directive requires class-distribution and
   imbalance analysis. Rejected.
3. **Hard-code an opaque mapping** — would hide assumptions; rejected in favour of
   an explicit, overridable, recorded ruleset.

## Consequences
- Class distribution is analyzable and reproducible, with the exact mapping
  transparent and configurable.
- Mapping changes are governance events (they change reported distributions).

## Rules / principles invoked
AP-6 (reproducibility), NR-11 (traceability), NR-13 (analysis only — no modelling /
no balancing), I2/I12 (ACNS terminology).
