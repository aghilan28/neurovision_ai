from pathlib import Path

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

for patient in sorted(DATASET_ROOT.glob("chb*")):

    summaries = list(patient.glob("*summary*.txt"))

    if not summaries:
        summaries = list(patient.glob("*.txt"))

    if not summaries:
        continue

    summary = summaries[0]

    print("=" * 80)
    print(patient.name)
    print(summary.name)
    print("=" * 80)

    text = summary.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    lines = text.splitlines()

    for line in lines[:120]:
        print(line)

    print("\n\n")