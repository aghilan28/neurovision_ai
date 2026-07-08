FROM python:3.11-slim-bookworm

WORKDIR /app/neurovision_ai

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the ENTIRE project (frontend HTML + backend + model + all assets)
COPY . .

EXPOSE 8080

# ONE entry point — the unified backend server
ENTRYPOINT ["python", "serve_local.py"]
