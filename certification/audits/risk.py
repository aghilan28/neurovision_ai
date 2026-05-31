"""Risk assessment (P10-E).

Builds a deterministic risk register from the evidence + the disclosed inherited gaps,
across the mandated categories (operational / model / data / security / deployment) and
severities (CRITICAL / HIGH / MEDIUM / LOW), each with a mitigation **recommendation**
(recommendations only — no mitigation is implemented).
"""

from __future__ import annotations

from ..util import fingerprint
from ..version import CERTIFICATION_RISK_VERSION

CRITICAL, HIGH, MEDIUM, LOW = "CRITICAL", "HIGH", "MEDIUM", "LOW"


class RiskAssessment:
    def run(self, bundle: dict) -> dict:
        risks = []

        def risk(rid, category, severity, description, mitigation, clinical_only=False):
            risks.append({"id": rid, "category": category, "severity": severity,
                          "description": description, "mitigation_recommendation": mitigation,
                          "clinical_deployment_only": clinical_only})

        # --- data ---
        risk("RISK-DATA-01", "data", CRITICAL,
             "Models trained/validated on synthetic deterministic fixtures only (G1); no real "
             "clinical EEG.",
             "Acquire governed real EEG datasets (TUH/CHB-MIT/etc.) and re-validate before any "
             "clinical use.", clinical_only=True)

        # --- model ---
        model_acc = {a: m["metrics"]["accuracy"]
                     for a, m in bundle["validation"]["model_benchmark"].get("models", {}).items()}
        risk("RISK-MODEL-01", "model", HIGH,
             f"Baselines are untuned reference models; measured accuracy varies on the synthetic "
             f"cohort ({model_acc}).",
             "Train/tune production models on real data with a held-out clinical benchmark; "
             "this is out of certification scope.", clinical_only=True)

        # --- deployment ---
        risk("RISK-DEPLOY-01", "deployment", HIGH,
             "Persistence is in-memory (registries) + local content-addressed stores (G3); a "
             "restart loses registry state unless backed up.",
             "Introduce durable persistence (database/object store) behind the existing store "
             "interfaces; schedule the existing backup routine.")
        risk("RISK-DEPLOY-02", "deployment", MEDIUM,
             "No long-running HTTP serving transport; the deployable unit is a CLI/batch "
             "application (operations.cli).",
             "Add an HTTP transport over the existing ApplicationAPI contract in a later phase.")

        # --- security ---
        if not bundle.get("production_secrets_injected"):
            risk("RISK-SEC-01", "security", MEDIUM,
                 "Production secrets are not injected in-repo (templates use placeholders); a "
                 "deploy without injected secrets would fail config validation.",
                 "Inject NV_AUTH_SECRET_KEY / NV_ADMIN_BOOTSTRAP_PASSWORD via env or a mounted "
                 "secrets file at deploy time.")
        risk("RISK-SEC-02", "security", MEDIUM,
             "Auth is local PBKDF2 only; no TLS termination, rate limiting, or external IdP.",
             "Front the service with TLS + a rate-limiting gateway; integrate an IdP if required.")

        # --- operational ---
        risk("RISK-OPS-01", "operational", LOW,
             "Governance (.gcc) is documented but not mechanized in CI (G2).",
             "Wire the documented governance checks into the CI pipeline.")
        # any phase not ready is an operational risk surfaced from evidence
        scards = bundle["validation"]["scorecards"]["scorecards"]
        for key, card in scards.items():
            if key != "overall_product_readiness" and not card.get("ready"):
                risk(f"RISK-OPS-{key}", "operational", HIGH,
                     f"Readiness scorecard '{key}' is not ready.",
                     "Investigate the failing criteria before deployment.")

        by_sev = {s: [r["id"] for r in risks if r["severity"] == s]
                  for s in (CRITICAL, HIGH, MEDIUM, LOW)}
        return {
            "risk_version": CERTIFICATION_RISK_VERSION,
            "n_risks": len(risks), "by_severity": by_sev,
            "critical": by_sev[CRITICAL], "high": by_sev[HIGH],
            "risks": risks,
            "open_critical_non_clinical": [r["id"] for r in risks
                                           if r["severity"] == CRITICAL and not r["clinical_deployment_only"]],
            "signature": fingerprint([(r["id"], r["severity"]) for r in risks]),
        }


__all__ = ["RiskAssessment", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
