FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV, PyTorch, InsightFace
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (modern compatible versions)
RUN pip install --no-cache-dir \
    flask>=3.0.0 \
    easydict \
    numpy \
    tqdm \
    torch \
    torchvision \
    opencv-python-headless \
    Pillow \
    tensorboardX \
    insightface \
    onnxruntime \
    cloudinary

# Copy application code
COPY . .

# Pre-download anti-spoofing models
RUN python download_models.py || true

EXPOSE 5001

ENV PYTHONUNBUFFERED=1
ENV PORT=5001

CMD ["python", "app_server.py"]
