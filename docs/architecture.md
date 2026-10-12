# Architecture: layer map

| Layer | Where in repo |
|---|---|
| Client | apps/web |
| Service | apps/api/src/ada/api, deps, security |
| SPI | apps/api/src/ada/spi (contracts only) |
| External adapters | apps/api/src/ada/providers |
| Queue + Worker | apps/api/src/ada/workers (Celery + Redis) |
| Database | apps/api/src/ada/db + alembic |
| Cache | apps/api/src/ada/cache |
| Storage | apps/api/src/ada/storage (S3/MinIO) |
| Cross-cutting | observability (Sentry, OpenTelemetry), cost ledger |

Dependency direction: api -> pipeline -> spi <- providers. `domain` has no I/O.
