# Security Platform — Design (DRP-5)

## Objective

Provide the security hardening the audit found missing: authentication, authorization, access
control, credential protection, security auditing, and security validation. Strictly security —
no model / training / inference / serving / persistence / deployment / monitoring changes.

## Package layout

```
backend/security_platform/
  version.py            component versions + DETERMINISTIC_EPOCH + salt/token widths
  models/domain.py      closed vocabularies + 13 records (DRP5-B)
  identity/             mints security_user / credential / session / authentication /
                        authorization / access_control / security_policy / readiness ids
  credentials/          CredentialManager — salted PBKDF2 (reused); no plaintext (DRP5-C)
  authentication/       AuthenticationEngine — verify + session create/validate/revoke (DRP5-C)
  authorization/        AuthorizationEngine — RBAC, default-deny (DRP5-D)
  access_control/       AccessControlEngine — least privilege over protected resources (DRP5-E)
  policies/             PolicyEngine — register/evaluate/validate/version (DRP5-F)
  registry/             SecurityRegistry (DRP5-G)
  audit/                make_security_audit_log (shared ImmutableAuditLog) (DRP5-H)
  lineage/              security lineage helpers (shared ml.lineage) (DRP5-I)
  validation/           content validators + integrity validator (DRP5-J; ml.validation)
  readiness/            SecurityReadinessEngine — 7 dimensions (DRP5-K)
  reports/              nine deterministic report builders (DRP5-L)
  schemas/contracts.py  entity contracts (DRP5-M)
  service.py            SecurityPlatformService — the governed orchestration hub
```

## Credential protection (DRP5-C)

Reuses the platform's PBKDF2-HMAC-SHA256 hashing + injectable entropy
(`backend.application_backend.auth`). A `CredentialRecord` stores a salted hash + salt
(verification material) and **never** the plaintext password; a session stores only a token
*fingerprint*. Secrets never enter a content hash, report, or the audit/lineage trail.

## Authorization (DRP5-D) + policies (DRP5-F)

RBAC with **explicit permissions only** and **default-deny**: a declarative policy is
`(role, resource_type, action) -> effect`. Evaluation denies on any DENY match, permits on an
ALLOW match, and **denies when no policy matches**. A PERMITTED decision always cites ≥ 1
matched policy.

## Determinism

The only non-deterministic inputs are the salt + session token; they come from an injectable
entropy source (deterministic by default here so the flow reproduces; secure-by-default in
production) and are quarantined from every content hash. Session expiry is a deterministic
logical-step window (no wall-clock). Identical inputs reproduce the same access id + version +
credential id.

## Lineage chain (DRP5-I)

```
User -> Credential -> Authentication -> Authorization -> Access Decision -> Resource Access
```

`verify_chain(resource_access)` reaches the user root; when the accessed resource exposes a
lineage node (a DRP-3 serving execution / DRP-4 persistence record), the resource-access node
also parents it, so the access additionally traces to the patient.

## Readiness criteria

`READY` ⇔ authentication + authorization + access control + a policy engine exist ∧ validation
passes ∧ registry + audit + lineage + a readiness score exist. Otherwise `PARTIALLY_READY`
(score ≥ 0.5, validation ok) or `NOT_READY`.

## Out of scope (forbidden in DRP-5)

Frontend changes, model retraining, inference changes, serving changes, persistence changes,
deployment changes, monitoring changes, clinical validation, DRP-6+.
