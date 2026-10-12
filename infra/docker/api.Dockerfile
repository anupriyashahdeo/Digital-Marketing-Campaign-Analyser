FROM python:3.12-slim
WORKDIR /app
COPY apps/api/pyproject.toml .
COPY apps/api/src ./src
COPY apps/api/alembic.ini apps/api/alembic ./
RUN pip install --no-cache-dir -e . gunicorn
EXPOSE 8000
CMD ["uvicorn","ada.main:app","--host","0.0.0.0","--port","8000"]
