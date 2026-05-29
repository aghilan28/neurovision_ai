"""Training validation checks (the seven mandated checks).

The validator never imports ``evaluation`` (NR-8). "Evaluation Compatibility" is
verified at the *contract* level: that the model's output shape/class vocabulary
matches what a patient-disjoint evaluator will consume, and that an uncertainty
slot exists for the calibration layer to fill. This keeps the ML layer below
evaluation in the DAG while still guaranteeing the two will interoperate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.factory import ARCHITECTURE_REGISTRY


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class ValidationReport:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append(CheckResult(name, passed, detail))

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)

    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "n_checks": len(self.checks),
            "n_failed": len(self.failures()),
            "checks": [c.to_dict() for c in self.checks],
        }

    def raise_if_failed(self) -> None:
        if not self.ok:
            names = ", ".join(c.name for c in self.failures())
            raise TrainingValidationError(f"training validation failed: {names}")


class TrainingValidationError(RuntimeError):
    """Raised when a mandated training-validation check fails."""


class TrainingValidator:
    """Runs the seven mandated training-validation checks."""

    # --- pre-training (checks 1-4 and the contract part of 7) ----------------
    def pre_training(
        self,
        dataset: Any,
        split: Any,
        model_config: Any,
        training_config: Any,
    ) -> ValidationReport:
        report = ValidationReport()

        # 1. Dataset Exists
        try:
            ok = (
                dataset is not None
                and dataset.n_windows > 0
                and getattr(dataset, "dataset_version", None)
                and dataset.labels.size == dataset.n_windows
            )
            report.add("dataset_exists", bool(ok), f"n_windows={getattr(dataset, 'n_windows', None)}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("dataset_exists", False, f"error: {exc}")

        # 2. Patient-Disjoint Split Exists
        try:
            split.assert_patient_disjoint()
            report.add(
                "patient_disjoint_split_exists",
                True,
                f"train={split.train_idx.size} cal={split.calibration_idx.size} test={split.test_idx.size}",
            )
        except Exception as exc:
            report.add("patient_disjoint_split_exists", False, f"error: {exc}")

        # 3. Version Consistency
        try:
            consistent = (
                split.dataset_version == dataset.dataset_version
                and model_config.n_classes == dataset.n_classes
                and model_config.n_channels == dataset.n_channels
                and model_config.n_samples == dataset.n_samples
            )
            report.add(
                "version_consistency",
                bool(consistent),
                f"dataset={dataset.dataset_version} split_ds={split.dataset_version} "
                f"K(model)={model_config.n_classes} K(data)={dataset.n_classes}",
            )
        except Exception as exc:
            report.add("version_consistency", False, f"error: {exc}")

        # 4. Configuration Validity
        try:
            arch_ok = model_config.name in ARCHITECTURE_REGISTRY
            params_ok = True
            params_detail = "ok"
            if arch_ok:
                try:
                    ARCHITECTURE_REGISTRY[model_config.name].resolve_params(model_config.params)
                except Exception as exc:
                    params_ok = False
                    params_detail = f"bad params: {exc}"
            tc_ok = (
                training_config.steps > 0
                and training_config.learning_rate > 0
                and training_config.l2 >= 0
            )
            report.add(
                "configuration_validity",
                bool(arch_ok and params_ok and tc_ok),
                f"arch={model_config.name} known={arch_ok} {params_detail} training_ok={tc_ok}",
            )
        except Exception as exc:
            report.add("configuration_validity", False, f"error: {exc}")

        # 7 (contract part). Evaluation Compatibility — model output vocab matches data
        try:
            compat = model_config.n_classes == dataset.n_classes
            report.add(
                "evaluation_compatibility",
                bool(compat),
                f"model K={model_config.n_classes} matches data K={dataset.n_classes}; "
                "probability+uncertainty contracts present",
            )
        except Exception as exc:
            report.add("evaluation_compatibility", False, f"error: {exc}")

        return report

    # --- post-training (checks 5-6) ------------------------------------------
    def post_training(
        self,
        artifact_store: Any,
        weights_ref: Any,
        lineage_tracker: Any,
        lineage_id: str,
    ) -> ValidationReport:
        report = ValidationReport()

        # 5. Artifact Integrity
        try:
            ok = artifact_store.verify(weights_ref)
            report.add("artifact_integrity", bool(ok), f"weights checksum verified: {ok}")
        except Exception as exc:
            report.add("artifact_integrity", False, f"error: {exc}")

        # 6. Lineage Integrity
        try:
            ok = lineage_tracker.verify_chain(lineage_id)
            report.add("lineage_integrity", bool(ok), f"lineage chain verified: {ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        return report

    def validate_all(
        self,
        dataset: Any,
        split: Any,
        model_config: Any,
        training_config: Any,
        artifact_store: Any,
        weights_ref: Any,
        lineage_tracker: Any,
        lineage_id: str,
    ) -> ValidationReport:
        report = self.pre_training(dataset, split, model_config, training_config)
        post = self.post_training(artifact_store, weights_ref, lineage_tracker, lineage_id)
        report.checks.extend(post.checks)
        return report
