"""Acquire a real EEG corpus locally and report its training readiness (Track 1).

Downloads the minimal real subset of an OPEN corpus (default: CHB-MIT from PhysioNet, no
account required) into the gitignored data root (``data/real`` or ``$NV_DATASET_ROOT``),
then runs the Real Dataset Platform over the **actual files** and prints the readiness.

    python -m scripts.acquire_real_dataset                # CHB-MIT
    python -m scripts.acquire_real_dataset --source chb_mit --no-download   # use local files

Approval-gated corpora (TUH, Temple/TUSZ) are never auto-downloaded — their acquisition
plan is reported instead.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    sys.path.insert(0, str(REPO))
    from backend.dataset_acquisition import DatasetSource, RealDatasetService

    parser = argparse.ArgumentParser(description="Acquire a real EEG corpus (Track 1).")
    parser.add_argument("--source", default="chb_mit",
                        choices=[s.value for s in DatasetSource if s != DatasetSource.OTHER])
    parser.add_argument("--data-root", default=None, help="override the local data root")
    parser.add_argument("--no-download", action="store_true",
                        help="do not fetch; only process files already present locally")
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)

    source = DatasetSource(args.source)
    svc = RealDatasetService(data_root=args.data_root)

    acq = svc.acquire(source, allow_download=not args.no_download, timeout=args.timeout)
    print(f"\nAcquisition — {source.value}  (attempted={acq.attempted})  root={acq.local_root}")
    for item in acq.items:
        print(f"  {item.relative_path:30s} {item.state.value:14s} "
              f"{item.size_bytes:>10d}  {item.note}")

    out = svc.integrate(source, allow_download=False)
    rd = out.dataset_record
    print(f"\nIntegration — {source.value}")
    print(f"  availability        : {out.availability.state.value} "
          f"({out.availability.n_verified}/{out.availability.n_files} verified)")
    print(f"  patients/recordings : {rd.n_patients} / {rd.n_recordings}")
    print(f"  labels (scheme)     : {rd.n_labels} ({out.label_verification.scheme.value}); "
          f"coverage={out.label_verification.coverage} classes={list(out.label_verification.classes)}")
    print(f"  validation ok       : {out.validation.ok}")
    print(f"  lineage verified    : {svc.lineage.verify_chain(out.registry_lineage_id)}")
    print(f"  audit verified      : {svc.audit_log_for(out.dataset_id).verify()}")
    print(f"  READINESS           : {out.readiness.classification.value} "
          f"(score={out.readiness.score})")
    return 0 if out.ready_for_training else 2


if __name__ == "__main__":
    raise SystemExit(main())
