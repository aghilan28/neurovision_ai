# `backend/security_platform` — Security Hardening & Access Control Platform (DRP-5)

Closes the audit's **insufficient security readiness** blocker: turns the persistent platform
into a **secure platform** with authentication, authorization, access control, credential
protection, security auditing, and security validation. The scope is *security* and nothing
else — no model / training / inference / serving / persistence / deployment / monitoring
changes (all explicitly out of scope).

Decision record:
[`../../.gcc/decisions/ADR-0028`](../../.gcc/decisions/ADR-0028-drp5-security-platform.md).

## What it does

```
register user + credential + policies ->
authenticate (verify credential, issue session) -> authorize (RBAC, default-deny) ->
control access (least privilege) -> validate -> score readiness -> trace -> audit
```

`SecurityPlatformService.secure_access(username, password, resource_type=, resource_id=,
action=)` runs the whole governed flow and returns a `SecurityOutcome` (with the immutable
`AccessControlRecord`).

## Authentication + credential protection (DRP5-C)

Reuses the platform's PBKDF2-HMAC-SHA256 hashing + injectable entropy
(`backend.application_backend.auth` — no reinvented crypto). A credential stores a salted hash
+ salt (verification material) and **never** the plaintext password; rotation supersedes the
old credential. Sessions store only a token **fingerprint** (never the raw token) and expire on
a deterministic logical-step window. Invalid credentials are rejected gracefully (never a crash).

## Authorization + policies (DRP5-D / DRP5-F)

Role-Based Access Control with **explicit permissions only** and **default-deny**. A policy is
declarative data `(role, resource_type, action) -> effect`; evaluation denies on any DENY
match, permits on an ALLOW match, and **denies when nothing matches**. A PERMITTED decision
always cites ≥ 1 matched policy.

## Access control (DRP5-E)

Least privilege over the protected resource types — dataset / model / serving / persistence /
administrative: access is permitted only when the session is valid **and** authorization
permits it.

## Reuse — no parallel systems

Shares the single `ml.lineage.LineageTracker` and the shared `ImmutableAuditLog`; reuses the
PBKDF2 + entropy primitives. The security registry stores only the new security artifacts.

## Traceability (DRP5-I)

A single `verify_chain` from a resource-access record proves

```
User -> Credential -> Authentication -> Authorization -> Access Decision -> Resource Access
```

and, when the accessed resource exposes a lineage node (a DRP-3 serving execution / DRP-4
persistence record), the access additionally reaches the patient.

## Readiness (DRP5-K)

Seven weighted dimensions — authentication / authorization / policy / registry / audit /
lineage / validation. An access can be `READY` only when all of those exist and validation
passes; otherwise `PARTIALLY_READY` or `NOT_READY`.

## Boundary (NR-8)

Imports `ml` + sibling `backend` only; never imports `frontend`. No plaintext credential
storage; secrets never enter a content hash, report, or the audit/lineage trail. Deterministic
throughout: identical inputs reproduce the same access id + version + credential id.

## Run

```bash
python -m scripts.verify_drp5_security_platform     # the 15 final-validation criteria
python -m pytest tests/test_security_platform.py tests/test_security_platform_e2e.py
```

## Honest scope

This adds **application-level** authentication, RBAC authorization, access control, credential
protection (PBKDF2, no plaintext), and tamper-evident security auditing in-process. It does
**not** add transport security (TLS), a secrets-management service, network firewalls, or
deployment hardening (those are deployment concerns, out of scope / later phases). The default
entropy source is deterministic here so the flow reproduces in tests/verification; production
injects a secure entropy source.
