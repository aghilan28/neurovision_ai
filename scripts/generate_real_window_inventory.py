from pathlib import Path
import re
import json
import csv
import mne

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

WINDOW_CONFIGS = [
    (4, 2),
    (8, 4),
    (16, 8)
]

def count_overlap_windows(duration_sec, seizure_intervals, window_sec, stride_sec):
    seizure_windows = 0
    background_windows = 0

    if duration_sec < window_sec:
        return 0, 0

    start = 0

    while start + window_sec <= duration_sec:

        end = start + window_sec

        is_seizure = False

        for sz_start, sz_end in seizure_intervals:

            if start < sz_end and end > sz_start:
                is_seizure = True
                break

        if is_seizure:
            seizure_windows += 1
        else:
            background_windows += 1

        start += stride_sec

    return seizure_windows, background_windows


def parse_summary(summary_file):

    text = summary_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    seizure_map = {}

    current_file = None

    lines = text.splitlines()

    i = 0

    while i < len(lines):

        line = lines[i].strip()

        if line.startswith("File Name:"):

            current_file = line.split("File Name:")[1].strip()

            seizure_map.setdefault(current_file, [])

        if "Seizure Start Time:" in line and "Seizure " not in line:

            start = int(re.findall(r"\d+", line)[0])

            if i + 1 < len(lines):
                end_line = lines[i + 1]

                if "Seizure End Time:" in end_line:

                    end = int(re.findall(r"\d+", end_line)[0])

                    seizure_map[current_file].append(
                        (start, end)
                    )

        numbered = re.match(
            r"Seizure\s+(\d+)\s+Start Time:",
            line
        )

        if numbered:

            start = int(re.findall(r"\d+", line)[1])

            if i + 1 < len(lines):

                end_line = lines[i + 1]

                if "End Time:" in end_line:

                    nums = re.findall(r"\d+", end_line)

                    end = int(nums[-1])

                    seizure_map[current_file].append(
                        (start, end)
                    )

        i += 1

    return seizure_map


print("=" * 80)
print("NEUROVISION OMEGA REAL WINDOW INVENTORY")
print("=" * 80)

patients = sorted(
    [
        p for p in DATASET_ROOT.iterdir()
        if p.is_dir() and p.name.startswith("chb")
    ]
)

global_seizure_events = 0
global_edfs = 0
global_hours = 0

global_counts = {
    "4s": {"sz": 0, "bg": 0},
    "8s": {"sz": 0, "bg": 0},
    "16s": {"sz": 0, "bg": 0}
}

patient_rows = []
edf_rows = []

for patient_dir in patients:

    patient = patient_dir.name

    print(f"Scanning {patient}")

    summary_files = list(patient_dir.glob("*summary*.txt"))

    if not summary_files:
        continue

    seizure_map = parse_summary(summary_files[0])

    patient_stats = {
        "4s": {"sz": 0, "bg": 0},
        "8s": {"sz": 0, "bg": 0},
        "16s": {"sz": 0, "bg": 0}
    }

    patient_hours = 0
    patient_seizures = 0

    for edf_file in sorted(patient_dir.glob("*.edf")):

        try:

            raw = mne.io.read_raw_edf(
                str(edf_file),
                preload=False,
                verbose=False
            )

            sfreq = float(raw.info["sfreq"])

            duration_sec = raw.n_times / sfreq

            raw.close()

            patient_hours += duration_sec / 3600.0

            global_hours += duration_sec / 3600.0

            global_edfs += 1

            seizures = seizure_map.get(
                edf_file.name,
                []
            )

            patient_seizures += len(seizures)

            global_seizure_events += len(seizures)

            row = [
                patient,
                edf_file.name,
                round(duration_sec, 2),
                len(seizures)
            ]

            for win, stride in WINDOW_CONFIGS:

                sz, bg = count_overlap_windows(
                    duration_sec,
                    seizures,
                    win,
                    stride
                )

                row.extend([sz, bg])

                key = f"{win}s"

                patient_stats[key]["sz"] += sz
                patient_stats[key]["bg"] += bg

                global_counts[key]["sz"] += sz
                global_counts[key]["bg"] += bg

            edf_rows.append(row)

        except Exception as e:

            print(
                f"FAILED {edf_file.name}: {e}"
            )

    patient_rows.append([
        patient,
        patient_hours,
        patient_seizures,
        patient_stats["4s"]["sz"],
        patient_stats["4s"]["bg"],
        patient_stats["8s"]["sz"],
        patient_stats["8s"]["bg"],
        patient_stats["16s"]["sz"],
        patient_stats["16s"]["bg"]
    ])

report = {
    "patients": len(patients),
    "edf_files": global_edfs,
    "recording_hours": round(global_hours, 2),
    "seizure_events": global_seizure_events,
    "window_counts": global_counts
}

with open(
    "WINDOW_INVENTORY_FINAL.json",
    "w"
) as f:
    json.dump(report, f, indent=2)

with open(
    "PATIENT_WINDOW_COUNTS.csv",
    "w",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "patient",
        "hours",
        "seizures",
        "4s_sz",
        "4s_bg",
        "8s_sz",
        "8s_bg",
        "16s_sz",
        "16s_bg"
    ])

    writer.writerows(patient_rows)

with open(
    "EDF_WINDOW_COUNTS.csv",
    "w",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "patient",
        "edf",
        "duration_sec",
        "seizures",
        "4s_sz",
        "4s_bg",
        "8s_sz",
        "8s_bg",
        "16s_sz",
        "16s_bg"
    ])

    writer.writerows(edf_rows)

print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(f"Patients         : {len(patients)}")
print(f"EDF Files        : {global_edfs}")
print(f"Recording Hours  : {global_hours:.2f}")
print(f"Seizure Events   : {global_seizure_events}")

print()

for key in ["4s", "8s", "16s"]:

    print(
        f"{key} seizure windows     : "
        f"{global_counts[key]['sz']:,}"
    )

    print(
        f"{key} background windows  : "
        f"{global_counts[key]['bg']:,}"
    )

    print()

print("Generated:")
print("WINDOW_INVENTORY_FINAL.json")
print("PATIENT_WINDOW_COUNTS.csv")
print("EDF_WINDOW_COUNTS.csv")