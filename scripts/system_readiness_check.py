import multiprocessing
import psutil
import shutil
from pathlib import Path

print("="*80)
print("NEUROVISION SYSTEM READINESS")
print("="*80)

print("CPU Threads:", multiprocessing.cpu_count())

ram = psutil.virtual_memory().total / (1024**3)
print("RAM GB:", round(ram,2))

for drive in ["C:\\","D:\\","E:\\"]:
    try:
        total, used, free = shutil.disk_usage(drive)
        print(
            drive,
            "FREE:",
            round(free/(1024**3),2),
            "GB"
        )
    except:
        pass

dataset = Path(r"E:\NeuroVision\datasets\chbmit")

edf_count = len(list(dataset.rglob("*.edf")))

print("EDF FILES:", edf_count)

print("\nREADY")