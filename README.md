# Ad Campaign Analyser

Find YouTube ads -> turn into text -> ask fixed questions -> double-check -> score -> dashboard/report.

## Quick start
```bash
cp .env.example .env
make test        # backend unit tests (no Docker needed)
make dev         # postgres, redis, minio, api (:8000), worker, web (:5173)
make migrate     # then: make revision m="init" first time
```
API docs: http://localhost:8000/docs

## Status
Foundation built: SPI contracts, scoring labeler, analyse+escalation pipeline, cache,
spend cap, manual CSV import, DB models, FastAPI skeleton, Celery wiring, React shell.
Stubs to implement: Jev/Claude clients, YouTube adapter, STT/vision, ad-feed adapter,
persistence in tasks, reports, auth/RBAC, OAuth. See docs/ and the build order.

[Verify] items: Jev/TypeSafe API, YouTube quota, ad-feed terms, Hindi accuracy.
Do not download competitor video/audio without legal sign-off.

## Authentication
Email is the username. Endpoints under `/api/v1/auth`: `signup`, `login`, `logout`, `me`,
`forgot-password`, `reset-password`. Passwords are hashed with scrypt; sessions use an
httpOnly cookie; reset links are single-use and expire in 30 minutes. In dev the reset link is
printed in the API log (ConsoleMailer). **Before production:** set `JWT_SECRET`, plug a real
mailer (SES/SendGrid) into `spi/mailer.py`, and move login throttling to Redis.

## Push to GitHub
```bash
git remote add origin https://github.com/<your-username>/ad-campaign-analyser.git
git push -u origin main
```
