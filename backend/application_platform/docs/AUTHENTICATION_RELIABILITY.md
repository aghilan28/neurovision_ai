# Authentication Reliability (DBE-5)

> **Deployment blocker eliminated:** an invalid or malicious bearer token can no longer
> produce an HTTP 500. Every authentication and authorization failure now returns a
> **controlled, documented** `401` / `403` response. This document is the single reference
> for that behaviour and contains the four guides the DBE-5 directive requires:
>
> 1. [Authentication Failure Guide](#1-authentication-failure-guide)
> 2. [Security Operator Guide](#2-security-operator-guide)
> 3. [API Response Guide](#3-api-response-guide)
> 4. [Token Validation Guide](#4-token-validation-guide)

The scope of DBE-5 is **authentication reliability only**: token validation, authorization
reliability, and error containment. It introduces **no** new authentication framework and
issues **no** new token type. It hardens the existing operative auth
(`backend/application_backend/auth`, opaque session tokens) at the HTTP boundary.

---

## Root cause (what was fixed)

The protected endpoint `POST /v1/uploads` only rejected a *missing* / *empty* bearer token.
A **present-but-invalid** token (malformed, truncated, random, forged, wrong, or a foreign
JWT) was passed straight into the deep workflow:

```
/v1/uploads -> svc.upload_and_analyze(token) -> run_backend_analysis(token)
            -> application_backend.api.handle(UPLOAD_EEG, token)
            -> RequestValidator fails "authentication" -> returns UNAUTHORIZED ApiResponse
            -> run_backend_analysis raises WorkflowError (a RuntimeError)
            -> the endpoint did NOT catch it -> FastAPI returned HTTP 500
```

Authorization failures (a *valid* token whose role is not permitted) followed the identical
path and also produced a 500.

**The fix:** the endpoint now classifies and validates the credential **before any work**, at
a hardened boundary (`ApplicationPlatformService.authenticate_request`). An invalid credential
never reaches business logic, so it can never raise `WorkflowError` and can never become a
500. A controlled `AuthenticationFailure` is raised and rendered to a `401` / `403` by a
registered FastAPI exception handler. A bare `AuthError` surfacing from anywhere is also
contained as a `401` (defense-in-depth).

---

## 1. Authentication Failure Guide

Every invalid credential is classified into exactly one **closed-vocabulary** code
(`backend/application_platform/security/token_validation.py :: TokenFailureCode`). There are
no free-form failure strings.

| Code | HTTP | Meaning | Typical cause |
|---|---|---|---|
| `MISSING_TOKEN` | 401 | No `Authorization` header was sent. | Client forgot the header. |
| `EMPTY_TOKEN` | 401 | Header present but the token is empty (`Bearer ` / `Bearer`). | Truncated/blank header. |
| `MALFORMED_TOKEN` | 401 | Token cannot be parsed as a live token shape (non-hex, wrong length, or a JWT whose segments are not valid base64url JSON). | Corruption, truncation, junk. |
| `INVALID_SIGNATURE` | 401 | A JWT-shaped token claiming our issuer **and** audience — but we never sign JWTs, so the signature is foreign/forged. | Self-signed / forged JWT. |
| `INVALID_ISSUER` | 401 | A JWT-shaped token whose `iss` claim is not `neurovision`. | Token from another system. |
| `INVALID_AUDIENCE` | 401 | A JWT-shaped token with the right issuer but an `aud` not equal to `neurovision-application-api`. | Token minted for another audience. |
| `EXPIRED_TOKEN` | 401 | The token maps to a session that is no longer `ACTIVE` (revoked / logged out / expired). | Stale session after logout. |
| `UNAUTHORIZED` | 401 | A well-formed token that matches no active session (random / wrong / forged opaque token), or whose user is no longer active. | Guessed / stale / tampered token. |
| `FORBIDDEN` | 403 | A **valid** session whose role is not permitted for the operation. | A `viewer` attempting an upload. |
| `UNKNOWN_TOKEN_FAILURE` | 401 | A contained, unexpected validation condition (the classifier never raises). | Defense-in-depth catch-all. |

**Guarantees**

- **Deterministic** — the same header + auth state always yields the same code and message
  (no wall-clock, no randomness).
- **Never crashes** — classification cannot raise; any surprise becomes
  `UNKNOWN_TOKEN_FAILURE` (a controlled 401).
- **No leakage** — responses never contain a stack trace, an internal exception string, or
  the token itself.

---

## 2. Security Operator Guide

**What to expect in production**

- Invalid tokens are *expected* traffic (scanners, expired sessions, client bugs). They are
  handled, classified, and audited — they are **not** incidents and never page as 5xx.
- Each failure appends a tamper-evident event to the shared application audit log
  (`ApplicationPlatformService.audit`), so the chain stays valid (`audit.verify()` remains
  `True`):
  - `authentication_failed` — for every `4xx` authentication code (missing/empty/malformed/
    signature/issuer/audience/expired/unauthorized/unknown).
  - `authorization_denied` — for `FORBIDDEN`.
- **Audit payloads never contain the raw token.** They carry `{code, operation, http_status,
  token_fingerprint?}` where `token_fingerprint` is a SHA-256-based hash (the same primitive
  the platform uses for session storage), never the secret.

**Triage**

| Symptom | Likely meaning | Action |
|---|---|---|
| Spike in `UNAUTHORIZED` | token guessing / stale clients | Inspect source; rate-limit upstream (out of app scope). |
| Spike in `EXPIRED_TOKEN` | sessions revoked / users logging out | Usually benign. |
| Any `INVALID_SIGNATURE` / `INVALID_ISSUER` / `INVALID_AUDIENCE` | a **foreign JWT** was presented (the platform issues opaque tokens only) | Investigate the client; this is never a valid NeuroVision token. |
| `FORBIDDEN` | a real user lacks the role | Grant an appropriate role (`admin`/`clinician`/`researcher`) if intended. |
| **Any** `500` on an auth path | should be impossible | Treat as a regression; run `scripts/verify_dbe5_authentication_reliability.py`. |

**Readiness** — `assess_security_readiness(service)` returns a `SecurityReadinessReport`
(`READY` / `NOT_READY`) confirming authentication is reachable + never crashes, the
authorization policy is defined, and the protected endpoint is guarded.

---

## 3. API Response Guide

### Protected endpoint

`POST /v1/uploads` requires `Authorization: Bearer <token>` and a write-capable role
(`admin`, `clinician`, or `researcher`).

### Controlled failure response (deterministic schema)

On any authentication/authorization failure the endpoint returns this exact JSON body:

```json
{
  "error": "unauthorized",          // "forbidden" when status == 403
  "code": "MALFORMED_TOKEN",        // one TokenFailureCode value
  "message": "The bearer token is malformed and cannot be parsed.",
  "status": 401,                     // 401 (authentication) or 403 (authorization)
  "operation": "upload_eeg"          // the attempted operation
}
```

- `401 Unauthorized` — authentication failures (all codes except `FORBIDDEN`).
- `403 Forbidden` — authorization failure (`FORBIDDEN`).
- The body is **stable**: the same code always yields the same `message`. It never contains a
  stack trace or internal text.

### Other status codes (unchanged by DBE-5)

| Status | When |
|---|---|
| `200` | Valid token; upload was a duplicate of a prior analysis (DBE-3). |
| `201` | Valid token; new upload accepted and analyzed. |
| `400` | Valid token; request body's `content_base64` is not valid base64. |
| `409` / `422` | Valid token; conflicting / invalid EEG upload (DBE-3). |

> Note: a valid, authorized request with **no model prepared** still raises the existing
> business error (`ApplicationPlatformError`). That is *not* an authentication path and is
> intentionally out of DBE-5 scope.

---

## 4. Token Validation Guide

### Token model

NeuroVision issues **opaque session tokens** — 64 lowercase hex characters
(`TOKEN_BYTES = 32`). They are not JWTs. Only a token **fingerprint** (a hash) is ever
stored; the raw token is returned once at `POST /v1/auth/login`.

### Validation pipeline (`security/classifier.py :: classify_request`)

```
extract_bearer(Authorization)
  -> absent            => MISSING_TOKEN
  -> "" (Bearer / blank)=> EMPTY_TOKEN
  -> looks like a JWT? (3 dot-separated segments)
       -> bad base64url/JSON          => MALFORMED_TOKEN
       -> iss != "neurovision"        => INVALID_ISSUER
       -> aud != "neurovision-application-api" => INVALID_AUDIENCE
       -> otherwise (foreign signature)        => INVALID_SIGNATURE
  -> opaque token => AuthService.classify_session_token(token)
       -> "active"        => authorize (role policy) -> ok | FORBIDDEN
       -> "revoked"       => EXPIRED_TOKEN
       -> "inactive_user" => UNAUTHORIZED
       -> "unknown" + 64-hex shape => UNAUTHORIZED
       -> "unknown" + bad shape    => MALFORMED_TOKEN
  -> any unexpected error => UNKNOWN_TOKEN_FAILURE   (contained; never raised)
```

### Why JWT-shaped tokens are rejected by class

The platform never *issues* a JWT, so any JWT-shaped credential is foreign by definition.
The validator still classifies it precisely (issuer → audience → signature) so operators get
an accurate, auditable reason rather than a generic rejection. This is **validation only** —
the platform does not accept, verify, or mint JWTs.

### Authorization (reused policy)

After authentication, the user's roles are checked against the existing
`OPERATION_ROLES` policy (`application_backend/validation`). `UPLOAD_EEG` requires
`{admin, clinician, researcher}`; a `viewer` is authenticated but `FORBIDDEN`. No new
authorization model is introduced.

### Determinism & safety invariants

- No wall-clock and no randomness in classification → reproducible codes/messages.
- The classifier and `AuthService.classify_session_token` are **read-only** and **never
  raise**.
- Secrets never enter a response, a log, or the audit chain (only fingerprints do).

---

## Verifying

```bash
python -m scripts.verify_dbe5_authentication_reliability          # the 15 directive criteria
python -m pytest tests/test_dbe5_authentication_reliability.py    # the test suite
```
