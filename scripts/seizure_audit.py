from pathlib import Path
import json
import re
import csv
from collections import defaultdict

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

report = {
    "totals": {
        "patients": 0,
        "summary_files": 0,
        "seizure_events": 0,
        "seizure_edfs": 0,
        "non_seizure_edfs": 0,
    },
    "patients": {}
}

patient_rows = []
edf_rows = []

patients = sorted(
    [p for p in DATASET_ROOT.iterdir()
     if p.is_dir() and p.name.startswith("chb")]
)

report["totals"]["patients"] = len(patients)

print("=" * 80)
print("NEUROVISION OMEGA SEIZURE FORENSICS AUDIT")
print("=" * 80)

for patient_dir in patients:

    patient = patient_dir.name

    summary_files = list(patient_dir.glob("*summary*.txt"))

    if not summary_files:
        summary_files = list(patient_dir.glob("*.txt"))

    seizure_events = 0
    seizure_edfs = set()

    for summary in summary_files:

        report["totals"]["summary_files"] += 1

        try:

            text = summary.read_text(
                errors="ignore",
                encoding="utf-8"
            )

            current_file = None

            for line in text.splitlines():

                line = line.strip()

                if "File Name:" in line:

                    current_file = (
                        line.split("File Name:")[-1]
                        .strip()
                    )

                if "Number of Seizures in File:" in line:

                    try:

                        count = int(
                            re.findall(r"\d+", line)[0]
                        )

                        seizure_events += count

                        if count > 0 and current_file:
                            seizure_edfs.add(current_file)

                    except Exception:
                        pass

        except Exception as e:

            print(
                f"FAILED SUMMARY: "
                f"{summary.name} -> {e}"
            )

    edfs = list(patient_dir.glob("*.edf"))

    seizure_edf_count = len(seizure_edfs)
    non_seizure_count = max(
        0,
        len(edfs) - seizure_edf_count
    )

    report["totals"]["seizure_events"] += seizure_events
    report["totals"]["seizure_edfs"] += seizure_edf_count
    report["totals"]["non_seizure_edfs"] += non_seizure_count

    report["patients"][patient] = {
        "edf_count": len(edfs),
        "seizure_events": seizure_events,
        "seizure_edfs": seizure_edf_count,
        "non_seizure_edfs": non_seizure_count,
    }

    patient_rows.append([
        patient,
        len(edfs),
        seizure_events,
        seizure_edf_count,
        non_seizure_count
    ])

    for edf in sorted(edfs):

        edf_rows.append([
            patient,
            edf.name,
            (
                "SEIZURE"
                if edf.name in seizure_edfs
                else "NON_SEIZURE"
            )
        ])

    print(
        f"{patient} | "
        f"EDF={len(edfs)} | "
        f"SEIZURES={seizure_events} | "
        f"SEIZURE_EDF={seizure_edf_count}"
    )

with open(
    "SEIZURE_AUDIT_REPORT.json",
    "w"
) as f:

    json.dump(
        report,
        f,
        indent=2
    )

with open(
    "PATIENT_SEIZURE_DISTRIBUTION.csv",
    "w",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "patient",
        "edf_count",
        "seizure_events",
        "seizure_edfs",
        "non_seizure_edfs"
    ])

    writer.writerows(patient_rows)

with open(
    "EDF_SEIZURE_INVENTORY.csv",
    "w",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "patient",
        "edf_file",
        "class"
    ])

    writer.writerows(edf_rows)

print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(
    f"Patients            : "
    f"{report['totals']['patients']}"
)

print(
    f"Summary Files       : "
    f"{report['totals']['summary_files']}"
)

print(
    f"Total Seizure Events: "
    f"{report['totals']['seizure_events']}"
)

print(
    f"Seizure EDFs        : "
    f"{report['totals']['seizure_edfs']}"
)

print(
    f"Non-Seizure EDFs    : "
    f"{report['totals']['non_seizure_edfs']}"
)

print()
print("Generated Files:")
print("SEIZURE_AUDIT_REPORT.json")
print("PATIENT_SEIZURE_DISTRIBUTION.csv")
print("EDF_SEIZURE_INVENTORY.csv")