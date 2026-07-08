FROM python:3.11-slim-bookworm

WORKDIR /app/neurovision_ai

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Phase 1 patch: copy full project so serve_local.py can find HTML pages,
# model artifacts, and all supporting modules.
COPY . .

EXPOSE 8080

# Phase 1 patch: serve_local.py is the unified entry point (was neurovision_api.py,
# which is a standalone model API that doesn't serve HTML pages).
ENTRYPOINT ["python", "serve_local.py"]