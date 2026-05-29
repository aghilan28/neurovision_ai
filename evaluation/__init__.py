"""``evaluation/`` — Validation & Truth Layer (Version 1).

This package decides **whether a result is real**. It owns the project's single
most important guarantee — **patient-disjoint validation** (AP-2, NR-3) — and the
scientific machinery every future model depends on: dataset understanding,
leakage-safe splitting, metrics, benchmarking, and full provenance.

Phase ownership
---------------
* **V1-P3 — Dataset Intelligence Layer** (:mod:`evaluation.dataset_intelligence`):
  understand a dataset (profiling, distributions, patient/channel/recording
  analysis, quality, and leakage *risk*) **without training a model**.
* **V1-P4 — Evaluation Foundation** (:mod:`evaluation.splits`,
  :mod:`evaluation.metrics`, :mod:`evaluation.benchmarking`,
  :mod:`evaluation.registry`, :mod:`evaluation.lineage`,
  :mod:`evaluation.validation`, :mod:`evaluation.framework`,
  :mod:`evaluation.reports`): the leakage-safe split + metric + benchmark
  framework that no model result may bypass.

Boundary contract (docs/architecture/IMPORT_RULES.md)
-----------------------------------------------------
* MAY import :mod:`ml`, :mod:`datasets`, :mod:`preprocessing`, and pinned
  numeric/stat libraries.
* MUST NOT import ``backend``, ``frontend``, ``monitoring`` or ``deployment``
  (Rule NR-8), and is **never** imported by ``ml`` (no cycle).

Scope guardrails (NR-13)
------------------------
These phases **do not** train models, run inference, or implement EEGNet/TCN/
Mamba/Conformal Prediction. They build *understanding* and *truth*; modelling is a
later V1 phase.
"""

from __future__ import annotations

from evaluation._version import EVALUATION_VERSION

#: Re-exported for convenience; canonical definition lives in ``evaluation._version``.
__all__ = ["EVALUATION_VERSION"]
