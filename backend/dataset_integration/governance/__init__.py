"""``backend/dataset_integration/governance`` — dataset governance metadata (DRP1-F).

Records governance *metadata* for a dataset: license name/type, usage + research
restrictions, attribution, ownership, source, and compliance metadata. **Metadata only** —
it makes **no legal interpretation and no compliance claim**; it simply captures what the
dataset's manifest declares so the lifecycle is traceable.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import (
    DatasetGovernanceRecord, GovernanceStatus, LicenseType,
)


def _coerce_license_type(value) -> LicenseType:
    try:
        return LicenseType(str(value))
    except ValueError:
        return LicenseType.UNKNOWN


class DatasetGovernance:
    """Extracts governance metadata from a manifest into a governed record."""

    def extract(self, manifest: dict) -> DatasetGovernanceRecord:
        gov = dict(manifest.get("governance", {}) or {})
        license_name = str(gov.get("license_name", ""))
        attribution = str(gov.get("attribution", ""))
        source_url = str(gov.get("source_url", ""))
        owner = str(gov.get("owner", ""))

        # status reflects how completely governance is *documented* (not legal validity)
        documented = sum(1 for v in (license_name, attribution, source_url, owner) if v)
        if documented == 4:
            status = GovernanceStatus.DOCUMENTED
        elif documented >= 1:
            status = GovernanceStatus.INCOMPLETE
        else:
            status = GovernanceStatus.MISSING

        governance_id = "governance+" + hash_obj(
            {"license": license_name, "owner": owner, "source": source_url,
             "attribution": attribution})
        return DatasetGovernanceRecord(
            governance_id=governance_id, license_name=license_name,
            license_type=_coerce_license_type(gov.get("license_type")),
            usage_restrictions=tuple(gov.get("usage_restrictions", []) or ()),
            research_restrictions=tuple(gov.get("research_restrictions", []) or ()),
            attribution=attribution, owner=owner, source_url=source_url,
            compliance_metadata=dict(gov.get("compliance_metadata", {}) or {}), status=status)


__all__ = ["DatasetGovernance"]
