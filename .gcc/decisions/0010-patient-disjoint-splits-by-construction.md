# DR-0010 · Patient-disjoint splits by construction + deterministic seeding

- **Status:** Accepted · **Phase:** V1-P4 · **Date:** caller-supplied

## Context
Patient-disjoint validation is the platform's cardinal guarantee (AP-2, NR-3).
Splitting must make leakage *structurally impossible*, and must be reproducible.

## Decision
- Splits partition **patients**, not recordings; records inherit their patient's
  partition. A patient therefore cannot span partitions **by construction**.
- The shuffle is seeded deterministically from the population fingerprint + base
  seed + generator version (`derive_seed`), so the same inputs reproduce the same
  split. The base seed is always recorded in the split spec.
- Apportionment uses largest-remainder with a guaranteed minimum of one patient per
  partition (a 3-patient set yields 1/1/1).
- The leakage gate (`evaluation.validation`) **independently verifies**
  disjointness on any split (defense in depth), and a leaky split **blocks** the
  evaluation run (no metrics, no benchmark).

## Alternatives considered
1. **Record-level splitting with a post-hoc patient check** — easy to get wrong;
   leakage becomes a detection problem rather than an impossibility. Rejected.
2. **Unseeded/random splitting** — not reproducible (violates NR-10). Rejected.

## Consequences
- Leakage is structurally prevented and additionally verified; splits are
  reproducible and content-addressed.

## Rules / principles invoked
AP-2 (patient-disjoint), AP-3/AP-6 (determinism/reproducibility), NR-3, NR-9, NR-10.
