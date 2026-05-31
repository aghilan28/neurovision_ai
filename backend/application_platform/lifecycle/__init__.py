"""``backend/application_platform/lifecycle`` — persistent model lifecycle & recovery (MP-3).

MP-1 made a fresh deploy *immediately usable* by **provisioning** a deterministic model on
startup. MP-3 makes that model **survive the realities of deployment**: a restart must
*recover* the model and *continue service* — automatically, with honest readiness and
objective evidence — rather than leaving the model in an unknown state.

What this module is (and is not):

* It is the **single authoritative model-recovery step** that the one existing application
  startup lifecycle (``server.factory.build_application`` lifespan) runs. It is **not** a
  parallel recovery system: it *reuses* the MP-1 ``provision_model`` (deterministic
  reconstruction of the same ``model_id``) and the DBE-4 ``ApplicationStateStore`` (the same
  ``persistence_platform.StorageEngine``). It introduces no new model framework, retrains
  nothing new, changes no datasets / security / operations / deployment architecture.
* It adds three things MP-1 lacked:
  1. a **durable model identity** (the ``model_id`` / architecture / lineage id — *not* the
     weights), persisted on the shared StorageEngine so it genuinely survives a cold restart;
  2. an explicit, observable :class:`ModelRecoveryReport` (was it recovered? is the model
     available? did identity stay continuous across the restart?);
  3. an honest recovery-readiness signal keyed on the **authoritative** usable-model signal
     (``backend.model_context``) — not the ``_model_info`` snapshot — closing the latent
     false-positive where a restored snapshot could report "ready" with no usable model.

Determinism: the model is reconstructed by the deterministic MP-1 bootstrap path, so the
recovered ``model_id`` equals the previously-persisted one. The recovery step verifies that
continuity instead of merely assuming it; a discontinuity is surfaced (and makes readiness
honest) rather than hidden.

Boundary (NR-8): part of the ``backend`` Application layer — imports ``ml`` + sibling
``backend`` only (here, only intra-package relatives + the MP-1 provisioning path). Never
imports ``frontend``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..version import APP_MODEL_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH


@dataclass(frozen=True)
class ModelRecoveryReport:
    """Deterministic record of what model recovery did at startup (no wall-clock).

    ``recovered`` is the honest, conservative verdict: a model is usable in *this* process
    **and** its identity is continuous with what was durably persisted (when a prior identity
    existed) **and** persistence (if configured) is healthy.
    """

    recovered: bool
    model_available: bool
    model_id: Optional[str]
    architecture: Optional[str]
    source: str  # "bootstrap_cohort" | "already_present" | "not_provisioned" | "failed"
    persistence_available: bool
    persistence_ok: bool
    recovered_from_persistence: bool
    identity_continuous: bool
    identity_persisted: bool
    registered: bool
    lineage_ok: bool
    audit_ok: bool
    findings: tuple = ()
    version: str = APP_MODEL_LIFECYCLE_VERSION

    @property
    def ok(self) -> bool:
        return self.recovered

    def to_dict(self) -> dict:
        return {"recovered": self.recovered, "model_available": self.model_available,
                "model_id": self.model_id, "architecture": self.architecture,
                "source": self.source, "persistence_available": self.persistence_available,
                "persistence_ok": self.persistence_ok,
                "recovered_from_persistence": self.recovered_from_persistence,
                "identity_continuous": self.identity_continuous,
                "identity_persisted": self.identity_persisted, "registered": self.registered,
                "lineage_ok": self.lineage_ok, "audit_ok": self.audit_ok,
                "findings": list(self.findings), "version": self.version}


def model_available(service) -> bool:
    """The **authoritative** usable-model signal: the backend inference context is set.

    This is the same condition the MP-1 provisioner keys off — a model can actually serve a
    prediction — as opposed to the lighter ``service._model_info`` snapshot, which persistence
    can restore *without* a usable inference context.
    """
    backend = getattr(service, "backend", None)
    return getattr(backend, "model_context", None) is not None


def current_model_identity(service) -> Optional[dict]:
    """Identity of the model currently usable in this process (or ``None`` if none).

    Reads the authoritative ``backend.model_context.model_record`` (id + lineage) and the
    architecture from the service's ``_model_info`` snapshot (set by ``prepare_model``).
    """
    backend = getattr(service, "backend", None)
    ctx = getattr(backend, "model_context", None)
    if ctx is None or getattr(ctx, "model_record", None) is None:
        return None
    mr = ctx.model_record
    info = getattr(service, "_model_info", {}) or {}
    return {"model_id": mr.model_id,
            "architecture": info.get("architecture") or _arch_value(mr),
            "lineage_id": getattr(mr, "lineage_id", None),
            "dataset_key": getattr(ctx, "dataset_key", None),
            "readiness": info.get("readiness")}


def _arch_value(model_record) -> Optional[str]:
    arch = getattr(model_record, "architecture", None)
    return getattr(arch, "value", arch) if arch is not None else None


def _identity_payload(identity: dict, *, source: str, created_at: str) -> dict:
    return {"model_id": identity.get("model_id"),
            "architecture": identity.get("architecture"),
            "lineage_id": identity.get("lineage_id"),
            "dataset_key": identity.get("dataset_key"),
            "source": source, "version": APP_MODEL_LIFECYCLE_VERSION,
            "created_at": created_at}


def _registered(service, identity: Optional[dict]) -> tuple[bool, bool]:
    """``(registered, lineage_ok)`` — the recovered model has a lineage node and it verifies.

    The model is registered (model_foundation) with a lineage id on the shared tracker; after
    a deterministic re-provision the same node id is recreated, so ``verify_chain`` from it
    holds across the restart. Proves "registry + lineage survive restart".
    """
    if not identity:
        return False, False
    lineage_id = identity.get("lineage_id")
    if not lineage_id:
        return False, False
    tracker = getattr(service, "lineage", None)
    try:
        exists = bool(tracker and tracker.exists(lineage_id))
        chain_ok = bool(tracker and tracker.verify_chain(lineage_id)) if exists else False
    except Exception:  # noqa: BLE001
        return True, False
    return exists, chain_ok


def recover_model(service, *, provision: bool = True, force: bool = False,
                  created_at: str = DETERMINISTIC_EPOCH) -> ModelRecoveryReport:
    """Recover (or first-time establish) a usable model — automatic, idempotent, never raises.

    The single authoritative model-recovery step run by the startup lifespan:

    1. Load the **durably persisted** model identity (survives the cold restart), if any.
    2. Ensure a usable model in *this* process by reusing the MP-1 ``provision_model``
       (deterministic reconstruction -> identical ``model_id``). Skipped when ``provision`` is
       False (operator injects a model context out-of-band); recovery is then assessed as-is.
    3. **Verify identity continuity**: the freshly-available ``model_id`` must equal the
       persisted one (when a prior identity existed). A mismatch is a finding and makes the
       recovery verdict honest (not recovered) instead of silently continuing.
    4. **Re-persist** the (now-authoritative) model identity so the *next* restart can verify
       continuity against it. Idempotent (deterministic content).

    Returns a :class:`ModelRecoveryReport`. Also stashed on ``service._model_recovery`` so the
    API / operations layers can read it without reaching into ``app.state``.
    """
    findings: list[str] = []
    store = getattr(service, "_state_store", None)
    persistence_available = store is not None

    # 1. Durable prior identity (the thing that genuinely survives a restart).
    prior = None
    if persistence_available:
        prior = store.load_model_identity()  # never raises (returns None on corrupt/absent)

    # 2. Ensure a usable model (reuse MP-1; deterministic). Out-of-scope to retrain anew.
    source = "not_provisioned"
    if provision:
        from ..provisioning import provision_model as _provision
        prov = _provision(service, force=force, created_at=created_at)
        source = prov.source
        if not prov.ok:
            findings.extend(prov.findings or ("model provisioning failed",))

    available = model_available(service)
    identity = current_model_identity(service)
    current_id = identity.get("model_id") if identity else None

    # 3. Identity continuity across the restart.
    recovered_from_persistence = bool(prior and prior.get("model_id"))
    identity_continuous = True
    if recovered_from_persistence and current_id and current_id != prior.get("model_id"):
        identity_continuous = False
        findings.append(
            f"identity_discontinuity: persisted={prior.get('model_id')} current={current_id}")
    elif recovered_from_persistence and not current_id:
        # a prior model was persisted but none is usable now -> recovery is incomplete
        identity_continuous = False
        findings.append("identity_lost: a model identity was persisted but none is now usable")

    # 4. Re-persist the durable identity + probe persistence health (honest readiness input).
    identity_persisted = False
    persistence_ok = True
    if persistence_available:
        persistence_ok = store.health_ok()
        if available and current_id:
            try:
                store.persist_model_identity(
                    _identity_payload(identity, source=source, created_at=created_at))
                identity_persisted = True
            except Exception as exc:  # noqa: BLE001 — surfaced; never crash startup
                persistence_ok = False
                findings.append(f"identity_persist_error: {type(exc).__name__}: {exc}")

    registered, lineage_ok = _registered(service, identity)
    audit_ok = _audit_ok(service)

    recovered = bool(available and identity_continuous and persistence_ok)
    report = ModelRecoveryReport(
        recovered=recovered, model_available=available, model_id=current_id,
        architecture=(identity or {}).get("architecture"), source=source,
        persistence_available=persistence_available, persistence_ok=persistence_ok,
        recovered_from_persistence=recovered_from_persistence,
        identity_continuous=identity_continuous, identity_persisted=identity_persisted,
        registered=registered, lineage_ok=lineage_ok, audit_ok=audit_ok,
        findings=tuple(findings))
    # Stash on the service so the API / operations layers can read it without app.state.
    try:
        service._model_recovery = report
    except Exception:  # noqa: BLE001 — never let bookkeeping break recovery
        pass
    return report


def _audit_ok(service) -> bool:
    audit = getattr(service, "audit", None)
    try:
        return bool(audit and audit.verify())
    except Exception:  # noqa: BLE001
        return False


def assess_recovery_readiness(*, startup_ok: bool, recovery: ModelRecoveryReport):
    """Honest readiness verdict: ``(ready, reasons)``.

    ``ready`` is True **only** when startup validated, a usable model is available, model
    identity is continuous across the restart, and (if configured) persistence is healthy.
    No false positives (a restored snapshot without a usable model never reports ready) and no
    false negatives (an ephemeral deploy with no persistence is allowed — that is a valid
    historical mode; persistence is required to be *healthy* only when it is configured).
    """
    reasons: list[str] = []
    if not startup_ok:
        reasons.append("startup_validation_failed")
    if not recovery.model_available:
        reasons.append("model_unavailable")
    if not recovery.identity_continuous:
        reasons.append("model_identity_discontinuous")
    if recovery.persistence_available and not recovery.persistence_ok:
        reasons.append("persistence_unavailable")
    ready = (startup_ok and recovery.model_available and recovery.identity_continuous
             and (recovery.persistence_ok or not recovery.persistence_available))
    return ready, reasons


__all__ = ["ModelRecoveryReport", "model_available", "current_model_identity", "recover_model",
           "assess_recovery_readiness"]
