FROM python:3.10-slim

WORKDIR /app

# Install minimal system dependencies for OpenCV and AI inference
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only (saves ~2.5GB disk compared to default CUDA build)
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download AI models into image
COPY download_models.py .
RUN python download_models.py || true

# Copy all application code
COPY . .

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV PORT=5000

CMD ["python", "app_server.py"]
