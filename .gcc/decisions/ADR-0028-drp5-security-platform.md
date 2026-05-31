# ADR-0028 — DRP-5: Security Hardening & Access Control Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Remediation Program DRP-5 (post-audit remediation)
> **Builds on:** ADR-0001 … ADR-0027 (Productization P1–P10 + DRP-1 … DRP-4)
> **Resolves:** Audit blocker — *INSUFFICIENT SECURITY READINESS* (insufficient access control /
> credential management / authorization evidence / security auditability)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse), AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

After DRP-1 … DRP-4, the Independent Production Reality Audit's remaining blocker was
**insufficient security readiness**: no first-class authentication, authorization, access
control, credential protection, or security auditability. DRP-5 adds the governed security
platform. The scope is strictly security: no model / training / inference / serving /
persistence / deployment / monitoring changes (NR-13).

## 2. Decisions

### D1 — A new governed `backend/security_platform` subsystem
Adds authentication, authorization, credentials, access control, policies, validation,
readiness, registry, audit, lineage, reports, schemas, and a service hub. It secures the
platform; it changes no business logic. As a `backend` package it obeys the import DAG (imports
`ml` + sibling `backend`, never `frontend`; enforced by `tests/test_boundaries.py`).

### D2 — Reuse the platform's PBKDF2 + entropy primitives (no reinvented crypto)
Credential hashing reuses `backend.application_backend.auth` (PBKDF2-HMAC-SHA256 + injectable
entropy + constant-time verify). A credential stores a salted hash + salt — **never** the
plaintext password — and a session stores only a token fingerprint. Secrets never enter a
content hash, report, or the audit/lineage trail.

### D3 — RBAC, explicit permissions only, default-deny
A declarative policy is `(role, resource_type, action) -> effect`. Evaluation denies on any
DENY match, permits on an ALLOW match, and **denies when nothing matches**. A PERMITTED decision
always cites ≥ 1 matched policy. Access control enforces least privilege over the protected
resource types (dataset / model / serving / persistence / administrative): access requires a
valid session **and** an authorization grant.

### D4 — Reuse the shared audit + lineage (no parallel systems)
Security events are appended to the shared hash-chained `ImmutableAuditLog`; security lineage
nodes are recorded in the single `ml.lineage` tracker. The chain
`User -> Credential -> Authentication -> Authorization -> Access Decision -> Resource Access`
`verify_chain`s to the user root, and (when the accessed resource exposes a lineage node) to the
patient.

### D5 — Deterministic security with quarantined secrets
The only non-deterministic inputs (salt, session token) come from an injectable entropy source
— deterministic by default *here* so the flow reproduces in tests/verification, secure-by-
default in production — and are quarantined from every content hash. Session expiry is a
deterministic logical-step window (no wall-clock). Identical inputs reproduce the same access id
+ version + credential id.

### D6 — Security readiness with a hard gate
Seven weighted dimensions (authentication / authorization / policy / registry / audit / lineage
/ validation) → score + findings + NOT_READY / PARTIALLY_READY / READY. `READY` requires
authentication + authorization + access control + a policy engine to exist, validation to pass,
and registry + audit + lineage + a readiness score to exist.

## 3. Consequences

- `python -m scripts.verify_drp5_security_platform` → **ALL 15 CRITERIA PASS** (stable across
  repeated runs); a user authenticates, is authorized (permit) / denied (default-deny) /
  rejected (bad credentials), access is controlled, audited, traced (User → … → Resource
  Access, reaching the patient via the real serving resource), and scored **READY**.
- The new suite adds 19 tests; the full repository suite is **927 passed** (was 908). `ruff`
  clean on all new code; `tests/test_boundaries.py` green; prior verify scripts unaffected.
- No new runtime dependencies; the platform runs offline and deterministically.

## 4. Scope guard (explicitly NOT built — NR-13)

Frontend changes, model retraining, inference changes, serving changes, persistence changes,
deployment changes, monitoring changes, clinical validation, DRP-6+. No TLS / secrets-manager /
network firewalls / deployment hardening (deployment concerns).

## 5. Honesty statement (NR-2)

DRP-5 adds **application-level** authentication, RBAC authorization, access control, credential
protection (PBKDF2, no plaintext), and tamper-evident security auditing in-process. It does not
add transport security (TLS), a secrets-management service, or deployment/network hardening
(deployment concerns, out of scope / later phases). The default entropy source is deterministic
so the flow reproduces in tests/verification; production injects a secure entropy source. This
closes the *application security-readiness* blocker — authentication, authorization, access
control, and security auditability now exist, are traceable, and score READY.
