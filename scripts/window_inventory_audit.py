from pathlib import Path
import json
import re
from collections import defaultdict

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

WINDOW_CONFIGS = [
    (4, 2),
    (8, 4),
    (16, 8),
]

report = {
    "corpus": {},
    "window_configs": {},
    "patients": {}
}

print("=" * 80)
print("NEUROVISION OMEGA WINDOW INVENTORY AUDIT")
print("=" * 80)

patients = sorted(
    [p for p in DATASET_ROOT.iterdir()
     if p.is_dir() and p.name.startswith("chb")]
)

total_edfs = 0
total_seizure_events = 0

for patient_dir in patients:

    patient = patient_dir.name

    summary_files = list(patient_dir.glob("*summary*.txt"))
    if not summary_files:
        summary_files = list(patient_dir.glob("*.txt"))

    seizure_intervals = []

    for summary in summary_files:

        try:
            text = summary.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            current_file = None
            start_time = None

            for line in text.splitlines():

                line = line.strip()

                if "File Name:" in line:
                    current_file = (
                        line.split("File Name:")[-1]
                        .strip()
                    )

                if "Seizure Start Time:" in line:

                    nums = re.findall(r"\d+", line)

                    if nums:
                        start_time = int(nums[0])

                if "Seizure End Time:" in line:

                    nums = re.findall(r"\d+", line)

                    if nums and start_time is not None:

                        end_time = int(nums[0])

                        seizure_intervals.append(
                            (
                                current_file,
                                start_time,
                                end_time
                            )
                        )

                        start_time = None

        except Exception as e:

            print(
                f"FAILED SUMMARY: "
                f"{summary.name} -> {e}"
            )

    edfs = list(patient_dir.glob("*.edf"))

    total_edfs += len(edfs)
    total_seizure_events += len(seizure_intervals)

    seizure_duration = 0

    for _, st, en in seizure_intervals:

        seizure_duration += max(
            0,
            en - st
        )

    report["patients"][patient] = {
        "edf_count": len(edfs),
        "seizure_events": len(seizure_intervals),
        "seizure_duration_seconds": seizure_duration
    }

print()
print("PATIENT SCAN COMPLETE")
print()

report["corpus"] = {
    "patients": len(patients),
    "edf_files": total_edfs,
    "seizure_events": total_seizure_events
}

for window_sec, stride_sec in WINDOW_CONFIGS:

    total_seizure_windows = 0

    for patient in report["patients"].values():

        seizure_seconds = patient[
            "seizure_duration_seconds"
        ]

        if seizure_seconds < window_sec:

            continue

        windows = (
            (seizure_seconds - window_sec)
            // stride_sec
        ) + 1

        total_seizure_windows += windows

    report["window_configs"][
        f"{window_sec}s_{stride_sec}s"
    ] = {
        "estimated_seizure_windows":
            int(total_seizure_windows)
    }

with open(
    "WINDOW_INVENTORY_REPORT.json",
    "w"
) as f:

    json.dump(
        report,
        f,
        indent=2
    )

print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(
    f"Patients        : "
    f"{len(patients)}"
)

print(
    f"EDF Files       : "
    f"{total_edfs}"
)

print(
    f"Seizure Events  : "
    f"{total_seizure_events}"
)

print()

for cfg, stats in report[
    "window_configs"
].items():

    print(
        f"{cfg:<12} "
        f"-> "
        f"{stats['estimated_seizure_windows']:,} "
        f"estimated seizure windows"
    )

print()
print(
    "Generated: WINDOW_INVENTORY_REPORT.json"
)