# API d'estimation immobiliere (FastAPI + uvicorn)
# Build depuis la RACINE : docker build -f server/Dockerfile -t sorydiallo89/gitops-project:api-1 .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Code + artefacts du modele, et le front (server.py le sert via StaticFiles)
COPY server/ /app/server/
COPY client/ /app/client/

# server.py cherche le front dans BASE.parent/"client" : cette structure est obligatoire
WORKDIR /app/server

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
