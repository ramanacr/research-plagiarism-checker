# Use a lightweight official Python 3.11 runtime
FROM python:3.11-slim

# Install essential system-level dependencies for PostgreSQL and compilers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set local work directory
WORKDIR /app

# Install CPU-only PyTorch first to avoid downloading ~5GB of NVIDIA CUDA/cuDNN GPU binaries
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Download the spaCy transformer pipeline
RUN python -m spacy download en_core_web_trf

# Configure HuggingFace cache directory and pre-download the SBERT model
ENV HF_HOME=/app/model_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

# Copy the rest of the application codebase
COPY . .

# Expose the API port
EXPOSE 8000

# Default command (Web API)
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
