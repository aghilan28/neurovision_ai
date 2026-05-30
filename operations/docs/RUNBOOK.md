# Operations Runbook (Productization P8)

Operational procedures for deploying and running NeuroVision. All commands are
repository-native and require no vendor services.

## 1. Configure an environment

Copy the template and inject real secrets out-of-band (never commit them):

```bash
cp operations/environments/production.env.template ./prod.env   # then edit / inject secrets
# OR mount a secrets file and point NV_SECRETS_FILE at it
python -m operations.cli config --environment production         # validate (secrets redacted)
```

## 2. Build the images

```bash
docker build -f operations/deployment/docker/Dockerfile.frontend -t neurovision-frontend .
docker build -f operations/deployment/docker/Dockerfile.backend  -t neurovision-backend  .
```

(Where a `docker compose` provider exists: `docker compose -f
operations/deployment/compose/docker-compose.yml up --build`.)

## 3. Health & readiness probes

```bash
python -m operations.cli live                       # liveness (container HEALTHCHECK)
python -m operations.cli ready  --environment production
python -m operations.cli health --environment production
```

## 4. Backup

```bash
python -m operations.cli backup --dest /var/lib/neurovision/backups/$(date +%s) \
    --environment production
```

A backup writes a checksummed `manifest.json` + the registry/config (redacted) +
content-addressed artifacts.

## 5. Restore & verify recovery

```bash
python -m operations.cli restore --dest /var/lib/neurovision/backups/<id>
```

Restore re-hashes every component against the manifest and fails closed on any mismatch
(tamper detection), reloads the registry, and asserts it is orphan-free and secret-free.

## 6. CI / release gate

```bash
python -m scripts.verify_productization_p8          # 15 operational criteria
python -m pytest -q                                 # full suite
```

The CI pipeline (`operations.ci.CiPipeline`) runs build/lint/test verification with a
quality gate; `ReleaseValidator` combines the gate + operations validation into a release
decision.

## 7. Operations report

```bash
python -m operations.cli report --environment production
```

Emits the Operations Readiness verdict over every operational dimension.
