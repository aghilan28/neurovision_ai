FROM python:3.11-slim-bookworm

WORKDIR /app/neurovision_ai

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project execution files directly into the execution path
COPY PHASE12_DEEP_SEQUENTIAL_ENGINE.py .
COPY neurovision_api.py .
COPY PHASE5B_TEMPORAL_XGBOOST.joblib .

EXPOSE 8080

ENTRYPOINT ["python", "neurovision_api.py"]