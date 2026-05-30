# Operations Foundation Platform — Key Decisions (Productization P8)

See `.gcc/decisions/ADR-0021-productization-p8-operations-foundation.md` for the full ADR.

1. **`operations/` is a top-level ops layer (peer of `scripts/`).** It composes/observes
   P1–P7 and modifies no workflow. It may import `backend`/`frontend` (lazily); no domain
   package imports it. This keeps the governed DAG intact and one-way.

2. **Real container builds where possible; structural validation where not.** The sandbox
   runtime is Podman/Buildah with no `docker compose`. So `docker build`/`docker run` of
   the slim, stdlib-only frontend image is exercised for real (proves build + startup),
   while the backend image and compose are validated structurally. Both are faithful,
   runnable definitions.

3. **No HTTP server is added.** A long-running serving transport would be a new backend
   feature (forbidden). The deployable unit is a CLI/batch application; container
   liveness/readiness are exposed via `operations.cli`, which is the standard
   exec-style container healthcheck. An HTTP transport is deferred to a later phase.

4. **Secrets are never hardcoded and never persisted.** Config resolves secrets via an
   injectable provider (env or mounted file); they are redacted in every serialized
   config/report and excluded from backups; real environments reject placeholder secrets.

5. **Determinism preserved (NR-9/NR-10).** Config signatures, structured logs, metrics,
   backup manifests, and reports are deterministic; logs default to a fixed epoch clock
   (a real deployment injects a wall-clock).

6. **Recovery is verified, not assumed.** Restore re-hashes every backed-up component
   against the manifest (tamper-detecting), reloads the registry defensively, and asserts
   orphan-free + secret-free.

7. **CI is repository-native / vendor-neutral.** The pipeline runs plain in-repo commands
   (compile/ruff/pytest/verify); it can be wired into any provider but locks into none.

## Inherited platform gaps (unchanged, disclosed)

* **G3 — in-memory persistence.** Backups snapshot the in-memory registry + on-disk
  content-addressed stores; durable databases remain out of scope.
* **G1/G2** (synthetic-data lineage, unmechanized `.gcc` governance) are inherited and
  unchanged by P8.
