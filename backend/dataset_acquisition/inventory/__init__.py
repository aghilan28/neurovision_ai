"""``backend/dataset_acquisition/inventory`` — Recording Inventory (T1-F).

Builds the deterministic dataset / patient / recording / session / label / duration /
channel inventories with **actual counts** from the connected real dataset, and folds
them into a single ``InventoryRecord`` stored in the registry.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import InventoryRecord


class InventoryBuilder:
    """Computes the real-dataset inventory from a ``ConnectorResult`` (deterministic)."""

    def build(self, result) -> InventoryRecord:
        recordings = list(result.recordings)
        labels = list(result.labels)

        sessions = sorted({r.session_id for r in recordings})
        ch_dist: dict[str, int] = {}
        for r in recordings:
            key = str(r.n_channels)
            ch_dist[key] = ch_dist.get(key, 0) + 1
        sampling = tuple(sorted({round(r.sampling_frequency, 6) for r in recordings
                                 if r.sampling_frequency > 0}))
        total_duration = round(sum(r.duration_seconds for r in recordings), 6)
        total_bytes = sum(r.file_size_bytes for r in recordings)

        label_dist: dict[str, int] = {}
        for label in labels:
            label_dist[label.value.value] = label_dist.get(label.value.value, 0) + 1

        inventory_id = "inventory+" + hash_obj({
            "source": result.source.value, "n_recordings": len(recordings),
            "n_patients": len(result.patients), "n_sessions": len(sessions),
            "n_labels": len(labels), "channel_distribution": dict(sorted(ch_dist.items())),
            "sampling": list(sampling), "label_distribution": dict(sorted(label_dist.items())),
        })

        return InventoryRecord(
            inventory_id=inventory_id, source=result.source,
            n_patients=len(result.patients), n_sessions=len(sessions),
            n_recordings=len(recordings), n_labels=len(labels),
            n_channels_distribution=ch_dist, sampling_frequencies=sampling,
            total_duration_seconds=total_duration, total_bytes=total_bytes,
            label_distribution=label_dist)


__all__ = ["InventoryBuilder"]
