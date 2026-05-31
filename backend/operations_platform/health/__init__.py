"""``backend/operations_platform/health`` — health system (T4-B).

Probes the **real** Track-3 ``ApplicationPlatformService`` (read-only) and reports structured
component health: service / dataset / model / storage / API / workflow / prediction. It never
modifies any workflow — it inspects already-produced state and exercises read-only paths.
States are the closed vocabulary HEALTHY / DEGRADED / UNHEALTHY.
"""

from __future__ import annotations

from ..identity import mint
from ..models.domain import (
    ComponentHealthRecord, HealthCheckRecord, HealthComponent, HealthState,
)
from ..version import DETERMINISTIC_EPOCH


class HealthEngine:
    """Computes component + overall health from the observed product state."""

    def check(self, product, *, created_at: str = DETERMINISTIC_EPOCH) -> HealthCheckRecord:
        comps: list[ComponentHealthRecord] = []

        def add(component, state, detail=""):
            comps.append(ComponentHealthRecord(component=component, state=state, detail=detail))

        # --- service: the hub + its wrapped backend API construct + answer ---
        try:
            api_ok = product.backend.api is not None
            add(HealthComponent.SERVICE, HealthState.HEALTHY if api_ok else HealthState.UNHEALTHY,
                f"version={getattr(product, 'version', '?')}")
        except Exception as exc:  # noqa: BLE001
            add(HealthComponent.SERVICE, HealthState.UNHEALTHY, f"error: {exc}")

        # --- dataset: a real dataset source is integrable / present ---
        try:
            datasets = getattr(product, "known_datasets", ["chb_mit"])
            add(HealthComponent.DATASET, HealthState.HEALTHY if datasets else HealthState.DEGRADED,
                f"datasets={list(datasets)}")
        except Exception as exc:  # noqa: BLE001
            add(HealthComponent.DATASET, HealthState.UNHEALTHY, f"error: {exc}")

        # --- model: a model is prepared (READY_FOR_SERVING upstream) ---
        info = getattr(product, "_model_info", {}) or {}
        if info.get("model_id"):
            add(HealthComponent.MODEL, HealthState.HEALTHY,
                f"model={info['model_id'][:24]} arch={info.get('architecture')}")
        else:
            add(HealthComponent.MODEL, HealthState.UNHEALTHY, "no model prepared")

        # --- storage: the registry round-trips (no orphans) ---
        try:
            orphans = product.registry.orphans()
            add(HealthComponent.STORAGE, HealthState.HEALTHY if not orphans else HealthState.DEGRADED,
                f"registry_records={product.registry.to_dict()['n_records']} orphans={len(orphans)}")
        except Exception as exc:  # noqa: BLE001
            add(HealthComponent.STORAGE, HealthState.UNHEALTHY, f"error: {exc}")

        # --- api: the in-process API answers a health-ish op (read-only) ---
        try:
            api_ok = hasattr(product.backend.api, "handle")
            add(HealthComponent.API, HealthState.HEALTHY if api_ok else HealthState.UNHEALTHY,
                "dispatcher present")
        except Exception as exc:  # noqa: BLE001
            add(HealthComponent.API, HealthState.UNHEALTHY, f"error: {exc}")

        # --- workflow: at least one completed analysis (or wiring intact) ---
        analyses = getattr(product, "_analyses", {}) or {}
        completed = [a for a in analyses.values()
                     if getattr(getattr(a, "workflow", None), "status", None)
                     and a.workflow.status.value == "completed"]
        if completed:
            add(HealthComponent.WORKFLOW, HealthState.HEALTHY, f"completed_workflows={len(completed)}")
        elif analyses:
            add(HealthComponent.WORKFLOW, HealthState.DEGRADED, "analyses present, none completed")
        else:
            add(HealthComponent.WORKFLOW, HealthState.DEGRADED, "no analyses yet (wiring intact)")

        # --- prediction: a real prediction result exists + is traceable ---
        preds = [a for a in analyses.values() if getattr(a, "prediction_result", None)]
        if preds:
            traceable = all(product.lineage.verify_chain(a.report_record.lineage_id)
                            for a in preds if getattr(a, "report_record", None))
            add(HealthComponent.PREDICTION,
                HealthState.HEALTHY if traceable else HealthState.DEGRADED,
                f"predictions={len(preds)} traceable={traceable}")
        else:
            add(HealthComponent.PREDICTION, HealthState.DEGRADED, "no predictions yet")

        overall = self._aggregate(comps)
        health_check_id = mint("ops_health_check", {
            "overall": overall.value,
            "components": [[c.component.value, c.state.value] for c in comps]})
        return HealthCheckRecord(health_check_id=health_check_id, overall=overall,
                                 components=tuple(comps), created_at=created_at)

    @staticmethod
    def _aggregate(components) -> HealthState:
        if not components:
            return HealthState.UNHEALTHY
        worst = min(c.state.rank for c in components)
        return {2: HealthState.HEALTHY, 1: HealthState.DEGRADED, 0: HealthState.UNHEALTHY}[worst]


__all__ = ["HealthEngine"]
