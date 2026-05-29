"""Pipeline configuration for the offline inference platform.

A ``PipelineConfig`` pins every input that affects an inference: the dataset source
(synthetic config), the split, preprocessing, the selected model + training config,
and the conformal risk level ``alpha``. Its content hash is the pipeline signature.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from datasets import SyntheticConfig, SplitConfig          # allowed: backend -> datasets
from preprocessing import PreprocessingConfig               # allowed: backend -> preprocessing
from ml.training import TrainingConfig                      # allowed: backend -> ml
from ml.provenance import hash_obj

from ..version import PIPELINE_VERSION


@dataclass
class PipelineConfig:
    """Pinned configuration for one offline inference run."""

    synthetic: SyntheticConfig = field(default_factory=SyntheticConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    model_name: str = "tcn"
    model_seed: int = 7
    alpha: float = 0.1
    owner: str = "neurovision-offline"
    pipeline_version: str = PIPELINE_VERSION

    def as_dict(self) -> dict:
        return {
            "pipeline_version": self.pipeline_version,
            "synthetic": self.synthetic.as_dict(),
            "split": self.split.as_dict(),
            "preprocessing": self.preprocessing.as_dict(),
            "training": self.training.as_dict(),
            "model_name": self.model_name,
            "model_seed": self.model_seed,
            "alpha": self.alpha,
        }

    def signature(self) -> str:
        return hash_obj(self.as_dict())
