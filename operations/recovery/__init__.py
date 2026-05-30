"""``operations/recovery`` — restore + recovery validation (P8-H).

Restores a backup written by :mod:`operations.backups` and validates it bit-for-bit
against its checksummed manifest: every component/artifact must still hash to its recorded
sha256, the registry must reload, and the restored registry must be orphan-free. Recovery
is therefore *verified*, not assumed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from ..util import file_sha256
from ..version import OPERATIONS_RECOVERY_VERSION


@dataclass(frozen=True)
class RecoveryCheck:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class RestoreResult:
    ok: bool
    manifest: dict
    registry: Optional[dict]
    config: Optional[dict]
    checks: tuple

    def to_dict(self) -> dict:
        return {
            "recovery_version": OPERATIONS_RECOVERY_VERSION, "ok": self.ok,
            "backup_id": self.manifest.get("backup_id"),
            "checks": [c.to_dict() for c in self.checks],
            "registry_records": (self.registry or {}).get("n_records"),
        }


class RestoreManager:
    """Reads a backup directory, verifies it against its manifest, and reloads state."""

    def restore(self, backup_dir: str) -> RestoreResult:
        checks: list[RecoveryCheck] = []
        manifest_path = os.path.join(backup_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return RestoreResult(False, {}, None, None,
                                 (RecoveryCheck("manifest_present", False, "manifest.json missing"),))
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        checks.append(RecoveryCheck("manifest_present", True, manifest.get("backup_id", "")))

        # verify every component + artifact checksum
        registry = config = None
        all_items = list(manifest.get("components", [])) + list(manifest.get("artifacts", []))
        mismatches = 0
        for item in all_items:
            abspath = os.path.join(backup_dir, item["path"])
            if not os.path.exists(abspath):
                mismatches += 1
                continue
            if file_sha256(abspath) != item["sha256"]:
                mismatches += 1
        checks.append(RecoveryCheck("checksums_match", mismatches == 0,
                                    f"{len(all_items) - mismatches}/{len(all_items)} verified"))

        # reload registry + config components (defensively — a corrupted/tampered file
        # must surface as a failed check, never an uncaught exception)
        for comp in manifest.get("components", []):
            abspath = os.path.join(backup_dir, comp["path"])
            try:
                if comp["name"] == "registry" and os.path.exists(abspath):
                    with open(abspath, "r", encoding="utf-8") as fh:
                        registry = json.load(fh)
                elif comp["name"] == "config" and os.path.exists(abspath):
                    with open(abspath, "r", encoding="utf-8") as fh:
                        config = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue
        checks.append(RecoveryCheck("registry_reloaded", registry is not None,
                                    f"records={None if registry is None else registry.get('n_records')}"))

        # restored registry must be orphan-free (no record without audit + lineage)
        orphans = []
        if registry is not None:
            for eid, rec in (registry.get("records", {}) or {}).items():
                if not rec.get("lineage_id") or not rec.get("audit_state"):
                    orphans.append(eid)
        checks.append(RecoveryCheck("no_orphans", not orphans, f"orphans={len(orphans)}"))

        # config must contain no secret values (only redacted/structure)
        secret_safe = True
        if config is not None:
            for k in config.get("secret_keys", []):
                if config.get("values", {}).get(k) not in (None, "***redacted***"):
                    secret_safe = False
        checks.append(RecoveryCheck("backup_secret_safe", secret_safe, "no secret values in backup"))

        ok = all(c.passed for c in checks)
        return RestoreResult(ok, manifest, registry, config, tuple(checks))


def build_recovery_report(result: RestoreResult) -> dict:
    return {"report_type": "recovery", **result.to_dict()}


__all__ = ["RestoreManager", "RestoreResult", "RecoveryCheck", "build_recovery_report"]
