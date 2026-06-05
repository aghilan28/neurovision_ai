FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=7860
ENV NV_HOST=0.0.0.0
ENV NV_WORKSPACE_DIR=/tmp/neurovision_workspace
ENV NV_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["python", "scripts/serve_neurovision.py"]
