FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY apps/api/pyproject.toml .
COPY apps/api/src ./src
RUN pip install --no-cache-dir -e ".[media]" && playwright install --with-deps chromium
CMD ["celery","-A","ada.workers.celery_app","worker","-l","info"]
