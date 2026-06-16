import re
import json
from pathlib import Path

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

FILE_RE = re.compile(r"File Name:\s*(\S+)", re.I)
START_RE = re.compile(r"Seizure(?:\s+\d+)?\s+Start Time:\s*(\d+)", re.I)
END_RE = re.compile(r"Seizure(?:\s+\d+)?\s+End Time:\s*(\d+)", re.I)

database = {}

total_events = 0

for summary_file in DATASET_ROOT.glob("chb*/chb*-summary.txt"):

    patient = summary_file.parent.name

    text = summary_file.read_text(
        errors="ignore",
        encoding="utf-8"
    )

    current_edf = None
    starts = []
    ends = []

    patient_db = {}

    def flush():

        global total_events

        if current_edf is None:
            return

        intervals = []

        for s, e in zip(starts, ends):
            intervals.append([int(s), int(e)])

        if intervals:
            patient_db[current_edf] = intervals
            total_events += len(intervals)

    for line in text.splitlines():

        m = FILE_RE.search(line)

        if m:

            flush()

            current_edf = m.group(1).strip()

            starts = []
            ends = []

            continue

        m = START_RE.search(line)

        if m:
            starts.append(int(m.group(1)))
            continue

        m = END_RE.search(line)

        if m:
            ends.append(int(m.group(1)))
            continue

    flush()

    database[patient] = patient_db

print("=" * 80)
print("SEIZURE INTERVAL DATABASE")
print("=" * 80)
print("Patients:", len(database))
print("Events:", total_events)

with open(
    "SEIZURE_INTERVAL_DATABASE.json",
    "w"
) as f:

    json.dump(
        database,
        f,
        indent=2
    )

print()
print("Saved:")
print("SEIZURE_INTERVAL_DATABASE.json")