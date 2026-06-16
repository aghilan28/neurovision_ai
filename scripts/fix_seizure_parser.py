import re
from pathlib import Path
from collections import defaultdict
import json

DATASET = Path(r"E:\NeuroVision\datasets\chbmit")

patient_counts = defaultdict(int)

total_events = 0

for summary in DATASET.rglob("*summary.txt"):

    text = summary.read_text(
        errors="ignore",
        encoding="utf-8"
    )

    patient = summary.parent.name

    matches = re.findall(
        r"Number of Seizures in File:\s*(\d+)",
        text,
        flags=re.IGNORECASE
    )

    for m in matches:
        total_events += int(m)
        patient_counts[patient] += int(m)

print("=" * 80)
print("SEIZURE EVENT RECONSTRUCTION")
print("=" * 80)

for patient in sorted(patient_counts):
    print(
        patient,
        patient_counts[patient]
    )

print()
print("TOTAL EVENTS:", total_events)

with open(
    "SEIZURE_RECONSTRUCTION.json",
    "w"
) as f:

    json.dump(
        {
            "total_events": total_events,
            "patients": patient_counts
        },
        f,
        indent=2
    )