from pathlib import Path
import mne
import json
import traceback
from collections import defaultdict

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

report = {
    "patients": {},
    "totals": {
        "patients": 0,
        "edf_files": 0,
        "readable_edf": 0,
        "failed_edf": 0,
        "total_duration_hours": 0.0,
        "sampling_rates": {},
        "channel_counts": {},
    }
}

sampling_rates = defaultdict(int)
channel_counts = defaultdict(int)

print("=" * 80)
print("NEUROVISION OMEGA CORPUS AUDIT")
print("=" * 80)

patients = sorted(
    [p for p in DATASET_ROOT.iterdir() if p.is_dir() and p.name.startswith("chb")]
)

report["totals"]["patients"] = len(patients)

for patient_dir in patients:

    patient = patient_dir.name

    print(f"\n[{patient}]")

    edfs = sorted(patient_dir.glob("*.edf"))

    patient_info = {
        "edf_count": len(edfs),
        "readable": 0,
        "failed": 0,
        "duration_hours": 0.0,
        "sampling_rates": {},
        "channel_counts": {},
    }

    for edf in edfs:

        report["totals"]["edf_files"] += 1

        try:

            raw = mne.io.read_raw_edf(
                str(edf),
                preload=False,
                verbose=False
            )

            sfreq = float(raw.info["sfreq"])
            channels = len(raw.ch_names)
            duration = float(raw.n_times / sfreq)

            patient_info["readable"] += 1
            report["totals"]["readable_edf"] += 1

            patient_info["duration_hours"] += duration / 3600.0
            report["totals"]["total_duration_hours"] += duration / 3600.0

            sampling_rates[str(sfreq)] += 1
            channel_counts[str(channels)] += 1

            raw.close()

        except Exception:

            patient_info["failed"] += 1
            report["totals"]["failed_edf"] += 1

            print(f"FAILED: {edf.name}")
            traceback.print_exc()

    report["patients"][patient] = patient_info

    print(
        f"EDF={patient_info['edf_count']} | "
        f"READABLE={patient_info['readable']} | "
        f"FAILED={patient_info['failed']} | "
        f"HOURS={patient_info['duration_hours']:.2f}"
    )

report["totals"]["sampling_rates"] = dict(sampling_rates)
report["totals"]["channel_counts"] = dict(channel_counts)

with open("CORPUS_AUDIT_REPORT.json", "w") as f:
    json.dump(report, f, indent=2)

print("\n")
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(f"Patients             : {report['totals']['patients']}")
print(f"EDF Files            : {report['totals']['edf_files']}")
print(f"Readable EDF         : {report['totals']['readable_edf']}")
print(f"Failed EDF           : {report['totals']['failed_edf']}")
print(f"Total Hours          : {report['totals']['total_duration_hours']:.2f}")

print("\nSampling Rates")
for k, v in sorted(sampling_rates.items()):
    print(f"{k} Hz : {v}")

print("\nChannel Counts")
for k, v in sorted(channel_counts.items()):
    print(f"{k} channels : {v}")

print("\nAudit report written:")
print("CORPUS_AUDIT_REPORT.json")