"""Dataset audits and reproducibility verification.

Audits re-verify, after the fact, that a dataset version is exactly what it claims
to be:

* ``verify_dataset_version`` — recompute the manifest fingerprint and compare it to
  the version's certified fingerprint (detects any tampering / drift).
* ``audit_manifest`` — confirm every manifest entry's content hash matches the
  hash known to the record registry (detects content substitution).

These are the operational form of "reproducibility tracking" (AP-6/NR-10): a
reported dataset can be re-checked against pinned content at any later time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets.schemas.dataset_version import DatasetVersion
from datasets.schemas.enums import ValidationSeverity
from datasets.schemas.manifest import DatasetManifest
from datasets.schemas.reports import ValidationIssue


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Outcome of auditing a dataset manifest/version."""

    dataset_id: str
    version: str
    ok: bool
    issues: tuple[ValidationIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "ok": self.ok,
            "issues": [i.to_dict() for i in self.issues],
        }


def verify_dataset_version(version: DatasetVersion, manifest: DatasetManifest) -> bool:
    """True iff ``manifest`` reproduces ``version``'s certified fingerprint."""
    return manifest.content_fingerprint == version.manifest_fingerprint


def audit_manifest(
    manifest: DatasetManifest,
    known_content: dict[str, str],
    *,
    version: DatasetVersion | None = None,
) -> AuditReport:
    """Audit a manifest against known record content hashes.

    Parameters
    ----------
    manifest:
        The manifest to audit.
    known_content:
        Mapping of ``file_id -> content_sha256`` for records known to the system
        (e.g. ``{r.file_id: r.content_sha256 for r in record_registry.records()}``).
    version:
        Optional certified version; when supplied, the fingerprint is also verified.
    """
    issues: list[ValidationIssue] = []

    for entry in manifest.entries:
        known = known_content.get(entry.file_id)
        if known is None:
            issues.append(
                ValidationIssue(
                    code="MANIFEST_RECORD_UNKNOWN",
                    severity=ValidationSeverity.ERROR,
                    message="manifest references a record not present in the registry",
                    context={"file_id": entry.file_id},
                )
            )
        elif known.lower() != entry.content_sha256.lower():
            issues.append(
                ValidationIssue(
                    code="MANIFEST_CONTENT_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    message="manifest content hash does not match the registered record",
                    context={
                        "file_id": entry.file_id,
                        "manifest_sha256": entry.content_sha256,
                        "registry_sha256": known,
                    },
                )
            )

    if version is not None and not verify_dataset_version(version, manifest):
        issues.append(
            ValidationIssue(
                code="FINGERPRINT_MISMATCH",
                severity=ValidationSeverity.ERROR,
                message="recomputed manifest fingerprint does not match the certified version",
                context={
                    "certified": version.manifest_fingerprint,
                    "recomputed": manifest.content_fingerprint,
                },
            )
        )

    ok = not any(i.severity is ValidationSeverity.ERROR for i in issues)
    return AuditReport(
        dataset_id=manifest.dataset_id,
        version=manifest.version,
        ok=ok,
        issues=tuple(issues),
    )
