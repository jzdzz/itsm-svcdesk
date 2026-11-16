# ai-generated: 100% - Gemini updated base image digest, added apt-get upgrade and removed runtime pip for Lab 5 triage
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt && pip uninstall -y pip setuptools || true

COPY src/ /app/src/

RUN mkdir -p /data
ENV SVCDESK_DB=/data/svcdesk.db

EXPOSE 8080
CMD ["uvicorn", "main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8080"]