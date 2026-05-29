"""Metric registry: metadata, dispatch, and per-result provenance (lineage)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from evaluation._canonical import array_fingerprint
from evaluation.metrics import classification as cls
from evaluation.metrics import ranking as rank
from evaluation.metrics.calibration import coverage, expected_calibration_error
from evaluation.metrics.schemas import MetricDefinition, MetricKind, MetricResult

#: Version of the metrics framework (recorded on every result).
METRICS_VERSION = "1.0.0"


class MetricNotFound(KeyError):
    """Raised when an unknown metric name is requested."""


class MetricRegistry:
    """A registry of metric definitions + their compute functions."""

    def __init__(self) -> None:
        self._defs: dict[str, MetricDefinition] = {}
        self._fns: dict[str, Callable[..., MetricResult]] = {}

    def register(self, definition: MetricDefinition, fn: Callable[..., MetricResult]) -> None:
        self._defs[definition.name] = definition
        self._fns[definition.name] = fn

    def get(self, name: str) -> MetricDefinition:
        try:
            return self._defs[name]
        except KeyError as exc:
            raise MetricNotFound(name) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._defs))

    def definitions(self) -> tuple[MetricDefinition, ...]:
        return tuple(self._defs[n] for n in self.names())

    def compute(
        self,
        name: str,
        *,
        y_true: np.ndarray,
        y_pred: np.ndarray | None = None,
        y_score: np.ndarray | None = None,
        labels: tuple[int, ...] | None = None,
    ) -> MetricResult:
        definition = self.get(name)
        if definition.placeholder:
            # Calling a placeholder is an explicit error (see calibration.py).
            self._fns[name](y_true=y_true, y_pred=y_pred, y_score=y_score, labels=labels)
        return self._fns[name](y_true=y_true, y_pred=y_pred, y_score=y_score, labels=labels)

    def compute_suite(
        self,
        names: Sequence[str],
        *,
        y_true: np.ndarray,
        y_pred: np.ndarray | None = None,
        y_score: np.ndarray | None = None,
        labels: tuple[int, ...] | None = None,
        skip_placeholders: bool = True,
    ) -> dict[str, MetricResult]:
        """Compute several metrics; placeholders are skipped by default."""
        out: dict[str, MetricResult] = {}
        for name in names:
            definition = self.get(name)
            if definition.placeholder and skip_placeholders:
                continue
            out[name] = self.compute(
                name, y_true=y_true, y_pred=y_pred, y_score=y_score, labels=labels
            )
        return out


# --- result helpers ----------------------------------------------------------
def _scope(y_true: np.ndarray, labels: tuple[int, ...] | None) -> str:
    observed = {int(v) for v in np.unique(np.asarray(y_true))}
    if labels is not None:
        observed |= {int(v) for v in labels}
    return "binary" if observed <= {0, 1} else "multiclass"


def _result(
    definition: MetricDefinition,
    *,
    value: float | None,
    values: dict | None,
    n_samples: int,
    fingerprint: str,
    scope: str,
) -> MetricResult:
    return MetricResult(
        name=definition.name,
        kind=definition.kind,
        version=definition.version,
        value=value,
        values=values,
        n_samples=n_samples,
        inputs_fingerprint=fingerprint,
        scope=scope,
    )


def default_metric_registry() -> MetricRegistry:
    """Build the standard metric registry for V1-P4."""
    registry = MetricRegistry()

    def _scalar_cls(name, kind, desc, func, value_range=(0.0, 1.0)):
        definition = MetricDefinition(
            name=name, kind=kind, version=METRICS_VERSION, description=desc,
            inputs=("y_true", "y_pred"), output="scalar", value_range=value_range,
        )

        def fn(*, y_true, y_pred, y_score=None, labels=None):  # noqa: ARG001
            if y_pred is None:
                raise cls.MetricInputError(f"{name} requires y_pred")
            value = func(y_true, y_pred, labels)
            return _result(
                definition, value=float(value), values=None, n_samples=int(np.size(y_true)),
                fingerprint=array_fingerprint(np.asarray(y_true), np.asarray(y_pred)),
                scope=_scope(y_true, labels),
            )

        registry.register(definition, fn)

    _scalar_cls("accuracy", MetricKind.CLASSIFICATION, "Overall accuracy.",
                lambda yt, yp, labels: cls.accuracy(yt, yp))
    _scalar_cls("balanced_accuracy", MetricKind.CLASSIFICATION,
                "Mean per-class recall (imbalance-robust).",
                lambda yt, yp, labels: cls.balanced_accuracy(yt, yp, labels=labels))
    _scalar_cls("precision_macro", MetricKind.CLASSIFICATION, "Macro-averaged precision.",
                lambda yt, yp, labels: cls.precision_recall(yt, yp, labels=labels)["macro"]["precision"])
    _scalar_cls("recall_macro", MetricKind.CLASSIFICATION, "Macro-averaged recall.",
                lambda yt, yp, labels: cls.precision_recall(yt, yp, labels=labels)["macro"]["recall"])
    _scalar_cls("f1_macro", MetricKind.CLASSIFICATION, "Macro-averaged F1.",
                lambda yt, yp, labels: cls.f1_score(yt, yp, labels=labels))

    # Confusion matrix (matrix output).
    cm_def = MetricDefinition(
        name="confusion_matrix", kind=MetricKind.CONFUSION, version=METRICS_VERSION,
        description="Confusion matrix counts.", inputs=("y_true", "y_pred"), output="matrix",
        value_range=None,
    )

    def _cm(*, y_true, y_pred, y_score=None, labels=None):  # noqa: ARG001
        if y_pred is None:
            raise cls.MetricInputError("confusion_matrix requires y_pred")
        label_arr = cls.resolve_labels(
            np.asarray(y_true).astype(np.int64), np.asarray(y_pred).astype(np.int64), labels
        )
        matrix = cls.confusion_matrix(y_true, y_pred, labels=labels)
        return _result(
            cm_def, value=None,
            values={"labels": [int(x) for x in label_arr], "matrix": matrix.tolist()},
            n_samples=int(np.size(y_true)),
            fingerprint=array_fingerprint(np.asarray(y_true), np.asarray(y_pred)),
            scope=_scope(y_true, labels),
        )

    registry.register(cm_def, _cm)

    # Per-class precision/recall/f1 (per_class output).
    pc_def = MetricDefinition(
        name="precision_recall_per_class", kind=MetricKind.CLASSIFICATION, version=METRICS_VERSION,
        description="Per-class precision/recall/F1 + macro.", inputs=("y_true", "y_pred"),
        output="per_class", value_range=(0.0, 1.0),
    )

    def _pc(*, y_true, y_pred, y_score=None, labels=None):  # noqa: ARG001
        if y_pred is None:
            raise cls.MetricInputError("precision_recall_per_class requires y_pred")
        values = cls.precision_recall(y_true, y_pred, labels=labels)
        return _result(
            pc_def, value=None, values=values, n_samples=int(np.size(y_true)),
            fingerprint=array_fingerprint(np.asarray(y_true), np.asarray(y_pred)),
            scope=_scope(y_true, labels),
        )

    registry.register(pc_def, _pc)

    # Sensitivity / specificity (binary).
    ss_def = MetricDefinition(
        name="sensitivity_specificity", kind=MetricKind.CLASSIFICATION, version=METRICS_VERSION,
        description="Binary sensitivity & specificity.", inputs=("y_true", "y_pred"),
        output="per_class", value_range=(0.0, 1.0),
    )

    def _ss(*, y_true, y_pred, y_score=None, labels=None):  # noqa: ARG001
        if y_pred is None:
            raise cls.MetricInputError("sensitivity_specificity requires y_pred")
        values = cls.sensitivity_specificity(y_true, y_pred)
        return _result(
            ss_def, value=None, values=values, n_samples=int(np.size(y_true)),
            fingerprint=array_fingerprint(np.asarray(y_true), np.asarray(y_pred)), scope="binary",
        )

    registry.register(ss_def, _ss)

    # Ranking metrics (binary, require scores).
    def _ranking(name, desc, func):
        definition = MetricDefinition(
            name=name, kind=MetricKind.RANKING, version=METRICS_VERSION, description=desc,
            inputs=("y_true", "y_score"), output="scalar", value_range=(0.0, 1.0),
        )

        def fn(*, y_true, y_pred=None, y_score=None, labels=None):  # noqa: ARG001
            if y_score is None:
                raise cls.MetricInputError(f"{name} requires y_score")
            value = func(y_true, y_score)
            return _result(
                definition, value=None if value is None else float(value), values=None,
                n_samples=int(np.size(y_true)),
                fingerprint=array_fingerprint(np.asarray(y_true), np.asarray(y_score)),
                scope="binary",
            )

        registry.register(definition, fn)

    _ranking("auroc", "Area under the ROC curve (binary).", rank.auroc)
    _ranking("auprc", "Average precision / area under PR (binary).", rank.auprc)

    # Calibration / clinical placeholders (registered, not computed in V1).
    for name, kind, desc, func in (
        ("expected_calibration_error", MetricKind.CALIBRATION,
         "PLACEHOLDER — calibration owned by the future uncertainty phase.",
         expected_calibration_error),
        ("coverage", MetricKind.CALIBRATION,
         "PLACEHOLDER — conformal coverage owned by the future uncertainty phase.", coverage),
    ):
        ph_def = MetricDefinition(
            name=name, kind=kind, version=METRICS_VERSION, description=desc,
            inputs=("y_true", "y_score"), output="scalar", value_range=(0.0, 1.0),
            placeholder=True,
        )

        def _ph(*, y_true, y_pred=None, y_score=None, labels=None, _func=func):  # noqa: ARG001
            _func()  # raises CalibrationNotAvailable

        registry.register(ph_def, _ph)

    return registry
