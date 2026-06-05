FROM python:3.12-slim

WORKDIR /app

# System dependencies for MNE/scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download CHB-MIT subset and extract features during build.
# This bakes the trained model into the Docker image so startup is fast.
RUN bash scripts/build_chbmit_features.sh /app/data/chbmit && \
    python scripts/train_chbmit.py --patients 1,3,5,10,23 \
        --output /app/data/chbmit --skip-download || \
    echo "CHB-MIT training skipped (will use synthetic fallback)"

# Hugging Face Spaces requires port 7860
ENV PORT=7860
ENV NV_HOST=0.0.0.0
ENV NV_WORKSPACE_DIR=/tmp/neurovision_workspace
ENV NV_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["python", "scripts/serve_neurovision.py"]
