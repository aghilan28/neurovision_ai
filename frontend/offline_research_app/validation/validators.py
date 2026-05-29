"""Application-side consistency validation (presentation integrity).

The app must never display anything that isn't backed by a consistent set of
registered artifacts. These checks compare cross-references between the index,
outputs, reports, and registries. Pure stdlib; no domain imports.
"""

from __future__ import annotations

import os

from ..schemas import ValidationReport
from ..state import AppState


class AppValidator:
    def validate(self, state: AppState) -> ValidationReport:
        report = ValidationReport()
        idx = state.index

        # 1. artifact consistency — every referenced path exists on disk
        missing = []
        for group in ("outputs", "reports", "registries"):
            for name, rel in idx.get(group, {}).items():
                if not os.path.exists(os.path.join(state.run_dir, rel)):
                    missing.append(f"{group}/{name}")
        report.add("artifact_consistency", not missing, f"missing={missing}")

        # 2. registry consistency — inference id present in the inference registry
        inf_reg = state.registries.get("inference_registry", {}).get("inferences", {})
        report.add("registry_consistency", idx["inference_id"] in inf_reg,
                   f"inference_id in registry: {idx['inference_id'] in inf_reg}")

        # 3. output consistency — prediction / probability / clinical counts agree
        pred = state.outputs.get("prediction", {})
        prob = state.outputs.get("probability", {})
        clinical = state.outputs.get("clinical", {})
        n = pred.get("n")
        prob_n = (prob.get("shape") or [None])[0]
        out_ok = n is not None and n == prob_n == clinical.get("n")
        report.add("output_consistency", bool(out_ok),
                   f"prediction={n} probability={prob_n} clinical={clinical.get('n')}")

        # 4. version consistency — index bundle matches summary output bundle
        idx_vb = idx.get("version_bundle", {})
        summary_vb = state.outputs.get("summary", {}).get("version_bundle", {})
        keys = ["dataset_version", "preprocessing_version", "split_version",
                "model_version", "evaluation_version", "calibration_version", "conformal_version"]
        mism = [k for k in keys if idx_vb.get(k) != summary_vb.get(k)]
        report.add("version_consistency", not mism, f"mismatched={mism}")

        # 5. lineage consistency — index lineage id present in lineage registry
        lineage_records = state.registries.get("lineage", {}).get("records", {})
        report.add("lineage_consistency", idx["lineage_id"] in lineage_records,
                   f"lineage_id in registry: {idx['lineage_id'] in lineage_records}")

        return report
