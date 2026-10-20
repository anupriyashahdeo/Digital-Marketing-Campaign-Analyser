# Production image: one container serves the website and the API on one URL.
# Used by Render (render.yaml). Local development still uses docker-compose.yml.

# 1) Build the React website into static files
FROM node:20-alpine AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web .
RUN npm run build

# 2) Python API, plus the built website
FROM python:3.12-slim
WORKDIR /app
COPY apps/api/pyproject.toml .
COPY apps/api/src ./src
RUN pip install --no-cache-dir .
COPY apps/api/alembic.ini .
COPY apps/api/alembic ./alembic
COPY --from=web /web/dist ./web
ENV APP_ENV=prod WEB_DIST=/app/web PORT=8000
EXPOSE 8000
# Create/upgrade database tables, then start. Render sets $PORT.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn ada.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'"]
