"""Run the V1 offline inference platform end to end (V1-P7) and optionally render
the offline research application (V1-P8).

This is a thin orchestration entry point (scripts may import any layer). It runs
the 15-stage orchestrator, prints a human-readable trace (the user cannot see the
filesystem), and — with ``--render-app`` — writes the static, offline HTML report
that reads only the registered artifacts.

    python -m scripts.run_offline_inference
    python -m scripts.run_offline_inference --model eegnet --steps 150 --render-app
"""

from __future__ import annotations

import argparse

from datasets import SyntheticConfig
from ml.training import TrainingConfig
from backend.offline_inference import InferenceOrchestrator, PipelineConfig


def run(argv=None) -> dict:
    p = argparse.ArgumentParser(description="Run the NeuroVision AI V1 offline inference platform.")
    p.add_argument("--patients", type=int, default=SyntheticConfig().n_patients)
    p.add_argument("--windows-per-patient", type=int, default=SyntheticConfig().windows_per_patient)
    p.add_argument("--model", default="tcn", choices=["simple_cnn", "eegnet", "tcn"])
    p.add_argument("--steps", type=int, default=TrainingConfig().steps)
    p.add_argument("--alpha", type=float, default=0.1)
    p.add_argument("--output", default=None)
    p.add_argument("--render-app", action="store_true", help="also render the offline research app HTML")
    args = p.parse_args(argv)

    config = PipelineConfig(
        synthetic=SyntheticConfig(n_patients=args.patients, windows_per_patient=args.windows_per_patient),
        training=TrainingConfig(steps=args.steps), model_name=args.model, alpha=args.alpha)
    orch = InferenceOrchestrator(config, output_dir=args.output)
    result = orch.run()

    print("=== NeuroVision AI — Offline Inference Platform (V1-P7) ===")
    print(f"inference_id : {result.inference_id}")
    print(f"output_dir   : {result.output_dir}")
    print(f"lineage_id   : {result.lineage_id}")
    print(f"stages       : {len(result.execution.stages)}/15 ({result.execution.status.value})")
    for s in result.execution.stages:
        print(f"   [{s.status.value:9s}] {s.name}")
    h = result.outputs["summary"]["headline"]
    print(f"headline     : acc={h['accuracy']:.3f} macro_f1={h['macro_f1']:.3f} "
          f"T={h['temperature']:.3f} coverage={h['observed_coverage']:.3f} "
          f"(target {h['target_coverage']}, reliable={h['coverage_reliable']}) "
          f"abstain={h['abstain_rate']:.3f}")
    print(f"validation   : {'OK' if result.validation['ok'] else 'FAILED'} "
          f"({result.validation['n_checks']} checks)")
    print(f"artifacts    : verified={orch and result.registries['inference'].list_inferences()==[result.inference_id]}")

    out = {"inference_id": result.inference_id, "output_dir": result.output_dir,
           "validation_ok": result.validation["ok"]}

    if args.render_app:
        from frontend.offline_research_app import write_app_html
        path = write_app_html(result.output_dir)
        print(f"\n=== Offline Research Application (V1-P8) ===")
        print(f"rendered     : {path}")
        print("open this file in a browser (fully offline; presentation only).")
        out["app_html"] = path

    return out


if __name__ == "__main__":
    run()
