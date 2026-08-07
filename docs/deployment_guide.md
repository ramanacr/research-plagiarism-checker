# 🚀 Deployment and Publishing Guide

This guide details the step-by-step procedure to deploy the **Secure Life Sciences Research Suite & Attention Analytics Engine** in two environments:
1. **AWS Cloud** (Enterprise, scalable, cloud-managed infrastructure).
2. **Internal/On-Premises Server** (Air-gapped friendly, highly secure, VM/bare-metal containerized infrastructure).

---

## 📋 Common Prerequisites

Before initiating deployment, verify that your host systems and environments meet the following requirements:

### 1. Compute & Hardware Requirements
* **RAM**: Minimum **8 GB RAM** (Recommended: **16 GB RAM**). Running spaCy’s transformer model (`en_core_web_trf`) alongside the sentence embedding model (`all-mpnet-base-v2`) requires a substantial memory footprint.
* **Storage**: At least **10 GB of free disk space** to store the container base layers and model weights (SBERT model is ~420MB; spaCy transformer is ~400MB; plus base dependencies).
* **CPU/GPU**: Multi-core modern CPU is required. GPU (NVIDIA CUDA compatible) is optional but recommended for high-throughput batch document similarity processing.

### 2. Software & Tooling Dependencies

#### For AWS Cloud Deployment:
* **AWS Account** with permissions to manage IAM roles, ECS Cluster, ECR registries, Route 53 records, and RDS instances.
* **AWS CLI (v2)** installed and configured with appropriate admin/deployment profile keys.
* **Docker Engine** (or Docker Desktop) installed locally to build and tag the initial container.

#### For Internal / On-Premises Deployment:
* **Operating System**: Modern Linux (Ubuntu 22.04 LTS, Debian 12, RHEL 8+, or equivalent) is highly recommended.
* **Docker Environment** (if containerizing):
  - **Docker Engine** (v20.10.0 or higher)
  - **Docker Compose** (v2.0.0 or higher)
* **Bare-Metal Environment** (if deploying natively):
  - **Python**: Version **3.11.x** installed.
  - **PostgreSQL Database**: Version **15 or 16** installed and running.
  - **Nginx**: Installed to act as the reverse proxy.

### 3. Port & Network Permissions
Ensure the following ports are allocated or open on your firewall/security groups:
* **Port `80` & `443`**: External access to Route 53 ALB (AWS) or local Nginx proxy (internal server).
* **Port `8000`**: Backend FastAPI web application. (Should remain private / protected behind reverse proxy).
* **Port `5432`**: PostgreSQL Database connections. (Must be locked down to only accept local-loopback or VPC container group traffic).

### 4. Environmental Configuration Variables

Regardless of the target environment, the application requires configuration variables. Create a template of environment variables to be set in your cloud container task definitions or local system environment:

```bash
# Core API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Database URL (using psycopg adapter)
RESEARCH_ATTENTION_DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@<db_host>:<db_port>/<db_name>

# Models configuration (must match download targets)
EMBEDDING_MODEL_NAME=all-mpnet-base-v2
SPACY_MODEL_NAME=en_core_web_trf
HF_HOME=/app/model_cache

# Security credentials
RESEARCH_ATTENTION_INTERNAL_API_KEY=your-custom-production-api-key-here

# Connector activation flags
RESEARCH_ATTENTION_ENABLED=true
RESEARCH_ATTENTION_ENABLE_WIKIMEDIA=true
RESEARCH_ATTENTION_ENABLE_OPENALEX=true
RESEARCH_ATTENTION_ENABLE_CROSSREF_EVENT=true
RESEARCH_ATTENTION_ENABLE_PUBPEER=true
```

---

## 🐳 Core Dockerization (Prerequisite for Container Deployments)

To deploy to either AWS ECS or an internal Docker environment, you should containerize the application.

### 1. Create a `Dockerfile`
Save this file in the project root:

```dockerfile
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

# Install dependencies first for optimal layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the heavy spaCy transformer pipeline
RUN python -m spacy download en_core_web_trf

# Configure HuggingFace cache directory and pre-download the SBERT model
# This guarantees that the container doesn't fetch weights on startup (vital for air-gapped/production speed)
ENV HF_HOME=/app/model_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

# Copy the rest of the application codebase
COPY . .

# Expose the API port
EXPOSE 8000

# Default command (Web API) - can be overridden for background worker
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ☁️ Option 1: Deploying to AWS Cloud (ECS Fargate & RDS)

The recommended production architecture for AWS uses **Amazon ECS (Elastic Container Service) on AWS Fargate** (serverless containers) paired with **Amazon RDS for PostgreSQL**.

```
                           ┌──────────────────────────┐
                           │      AWS Route 53        │
                           └─────────────┬────────────┘
                                         │
                                         ▼
                           ┌──────────────────────────┐
                           │  Application Load Balancer│ (Handles SSL termination)
                           └─────────────┬────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │ Private Subnet                            │
                   ▼                                           ▼
      ┌─────────────────────────┐                 ┌─────────────────────────┐
      │  ECS Fargate (Web API)  │                 │ ECS Fargate (Worker)    │
      │  (Multiple tasks, ASG)  │                 │ (Single Task daemon)    │
      └────────────┬────────────┘                 └────────────┬────────────┘
                   │                                           │
                   └─────────────────────┬─────────────────────┘
                                         ▼
                           ┌──────────────────────────┐
                           │  Amazon RDS PostgreSQL   │
                           └──────────────────────────┘
```

### Step 1: Push Container to Amazon ECR (Elastic Container Registry)
1. Navigate to the AWS Console -> ECR and create a private repository named `research-suite`.
2. Authenticate your Docker CLI:
   ```bash
   aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.<your-region>.amazonaws.com
   ```
3. Build and tag your image:
   ```bash
   docker build -t research-suite .
   docker tag research-suite:latest <aws_account_id>.dkr.ecr.<your-region>.amazonaws.com/research-suite:latest
   ```
4. Push to ECR:
   ```bash
   docker push <aws_account_id>.dkr.ecr.<your-region>.amazonaws.com/research-suite:latest
   ```

### Step 2: Provision Database on Amazon RDS
1. Go to Amazon RDS -> Databases -> **Create Database**.
2. Select **PostgreSQL** (version 15 or 16).
3. Select **Production** or **Dev/Test** template depending on your load profile.
4. Set DB instance identifier to `research-attention-db`.
5. Configure Master username (e.g. `postgres`) and password. Choose an instance size (e.g. `db.t4g.medium` or larger for vector tasks).
6. Enable automatic storage scaling.
7. **Networking**: Ensure the DB is placed in your **Private VPC Subnets** and is **not publicly accessible**. Create a Security Group allowing inbound TCP traffic on port `5432` from the ECS security group only.

### Step 3: Configure AWS Secrets Manager
Store the database credentials securely:
1. Go to Secrets Manager -> **Store a new secret**.
2. Choose **Credentials for Amazon RDS database** and select your `research-attention-db`.
3. Set the key/value secrets or use the auto-resolved connection URI string.

### Step 4: Define ECS Fargate Task Definitions
We need to create **two separate task definitions** (or one task definition with two service execution plans) using the same ECR image:

#### Task A: Web API Service
- **Launch Type**: Fargate.
- **CPU / Memory**: Minimum `2 vCPU` and `8 GB RAM` (needed for running spaCy transformers and SBERT models simultaneously).
- **Container Definition**:
  - Image: `<aws_account_id>.dkr.ecr.<your-region>.amazonaws.com/research-suite:latest`
  - Port Mappings: Port `8000` (TCP).
  - Command: `uvicorn src.api:app --host 0.0.0.0 --port 8000`
  - Environment variables: Map `RESEARCH_ATTENTION_DATABASE_URL` from the Secret Manager ARN.

#### Task B: Crawler Background Worker Service
- **Launch Type**: Fargate.
- **CPU / Memory**: `1 vCPU` and `4 GB RAM` (the worker does not run the heavy SBERT model but requires spaCy).
- **Container Definition**:
  - Image: `<aws_account_id>.dkr.ecr.<your-region>.amazonaws.com/research-suite:latest`
  - Command: `python -m src.attention.worker`
  - Desired Tasks count: Set strictly to `1` (or use locks) to prevent concurrent Wikimedia crawling job conflicts.

### Step 5: Configure Application Load Balancer (ALB) and SSL
1. Set up an ALB in the Public Subnets of your VPC.
2. Configure a Target Group on port `8000` using HTTP with health check path `/`.
3. Request an SSL certificate in **AWS Certificate Manager (ACM)** for your custom domain.
4. Create an HTTPS Listener (port `443`) on the ALB forwarding to your Target Group.
5. Create a Route 53 CNAME record pointing your domain (e.g. `integrity.myorg.org`) to the ALB DNS name.

### Step 6: Deploy & Database Migrations
1. To run initial database migrations, you can run a one-time ECS task mapping the command to:
   ```bash
   alembic upgrade head
   ```
2. Create your ECS cluster and launch the Services. The Web API service can scale up and down dynamically depending on request load, while the Worker Service runs continuously.

---

## 🏢 Option 2: Deploying to an Internal / On-Premises Server

For on-premises server environments (VMs, bare-metal RedHat, Ubuntu, or Windows Server instances), the two primary installation pathways are **Docker Compose** or **Native systemd services**.

### Strategy A: Docker Compose Deployment (Recommended)

This strategy isolates dependencies and makes rollback operations simple.

#### 1. Setup Project Directory on Internal Host
Clone the repository or unpack the build directory under `/opt/research-suite`.

#### 2. Create `docker-compose.prod.yml`
Save this config file in your installation directory:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: research_db
    restart: always
    environment:
      POSTGRES_DB: research_attention
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ProductionSecurePasswordHere
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432" # Keep PostgreSQL bound to localhost on host for security

  web:
    build: .
    container_name: research_web
    restart: always
    environment:
      - RESEARCH_ATTENTION_DATABASE_URL=postgresql+psycopg://postgres:ProductionSecurePasswordHere@db:5432/research_attention
      - EMBEDDING_MODEL_NAME=all-mpnet-base-v2
      - SPACY_MODEL_NAME=en_core_web_trf
      - HF_HOME=/app/model_cache
      - RESEARCH_ATTENTION_INTERNAL_API_KEY=prod-key-auth-tokens
    ports:
      - "127.0.0.1:8000:8000" # Expose to Nginx local proxy
    depends_on:
      - db
    command: uvicorn src.api:app --host 0.0.0.0 --port 8000

  worker:
    build: .
    container_name: research_worker
    restart: always
    environment:
      - RESEARCH_ATTENTION_DATABASE_URL=postgresql+psycopg://postgres:ProductionSecurePasswordHere@db:5432/research_attention
      - EMBEDDING_MODEL_NAME=all-mpnet-base-v2
      - SPACY_MODEL_NAME=en_core_web_trf
      - HF_HOME=/app/model_cache
    depends_on:
      - db
    command: python -m src.attention.worker

volumes:
  pgdata:
```

#### 3. Build and Launch
Run migrations and spin up the containers:
```bash
# Build the images and start postgres first
docker-compose -f docker-compose.prod.yml up -d db

# Run the migrations inside the temporary web container structure
docker-compose -f docker-compose.prod.yml run --rm web alembic upgrade head

# Start all services
docker-compose -f docker-compose.prod.yml up -d
```

---

### Strategy B: Native Bare-Metal / VM Deployment (Systemd + Nginx)

If docker cannot be used due to internal VM regulations, run the application directly on the server OS using system services.

#### Step 1: Install System Packages & Postgres (example for Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib libpq-dev nginx
```

Create the database and database user inside the PostgreSQL console:
```sql
CREATE DATABASE research_attention;
CREATE USER research_admin WITH PASSWORD 'ProductionSecurePasswordHere';
GRANT ALL PRIVILEGES ON DATABASE research_attention TO research_admin;
```

#### Step 2: Set Up Directory & Virtual Environment
1. Deploy project directory to `/opt/research-suite`.
2. Configure permissions:
   ```bash
   sudo chown -R $USER:$USER /opt/research-suite
   cd /opt/research-suite
   ```
3. Set up the virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Download the local AI models:
   ```bash
   python -m spacy download en_core_web_trf
   # Pre-cache SentenceTransformers
   export HF_HOME=/opt/research-suite/model_cache
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"
   ```

#### Step 3: Configure Database Schema
Apply migrations natively:
```bash
export RESEARCH_ATTENTION_DATABASE_URL=postgresql+psycopg://research_admin:ProductionSecurePasswordHere@localhost:5432/research_attention
.venv/bin/alembic upgrade head
```

#### Step 4: Create Systemd Services
Create two unit service configurations to handle system restarts, logs, and processes automatically.

##### Service 1: Web API (`/etc/systemd/system/research-web.service`)
```ini
[Unit]
Description=Secure Life Sciences Research API Service
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/opt/research-suite
Environment="PATH=/opt/research-suite/.venv/bin"
Environment="RESEARCH_ATTENTION_DATABASE_URL=postgresql+psycopg://research_admin:ProductionSecurePasswordHere@localhost:5432/research_attention"
Environment="HF_HOME=/opt/research-suite/model_cache"
ExecStart=/opt/research-suite/.venv/bin/uvicorn src.api:app --host 127.0.0.1 --port 8000 --workers 4

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

##### Service 2: Background Crawler Worker (`/etc/systemd/system/research-worker.service`)
```ini
[Unit]
Description=Research Attention Background Worker Daemon
After=network.target postgresql.service research-web.service

[Service]
User=www-data
WorkingDirectory=/opt/research-suite
Environment="PATH=/opt/research-suite/.venv/bin"
Environment="RESEARCH_ATTENTION_DATABASE_URL=postgresql+psycopg://research_admin:ProductionSecurePasswordHere@localhost:5432/research_attention"
Environment="HF_HOME=/opt/research-suite/model_cache"
ExecStart=/opt/research-suite/.venv/bin/python -m src.attention.worker

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

##### Start and Enable the Services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable research-web.service research-worker.service
sudo systemctl start research-web.service research-worker.service
```

---

## 🔒 Configuration of Reverse Proxy (Nginx)

For both Docker Compose and Bare-Metal native setup, Nginx should serve as a secure front-facing reverse proxy to manage SSL/TLS certificate termination.

### 1. Create Nginx Server Block Configuration
Save the following config as `/etc/nginx/sites-available/research-suite`:

```nginx
server {
    listen 80;
    server_name integrity-check.internal.org; # Replace with target subdomain

    # Redirect all HTTP requests to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name integrity-check.internal.org;

    # SSL Certificates (Specify Let's Encrypt or Corporate Authority paths)
    ssl_certificate /etc/ssl/certs/research_suite.crt;
    ssl_certificate_key /etc/ssl/private/research_suite.key;

    # Hardened SSL Parameters
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Increase maximum upload file limit for large research papers (PDFs/Word docs)
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Disable buffering to allow smooth streaming and long polling
        proxy_buffering off;
        proxy_read_timeout 600s;
    }
}
```

### 2. Enable Configuration & Restart Nginx
```bash
sudo ln -s /etc/nginx/sites-available/research-suite /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📈 Performance & Scaling Tuning

### Air-Gapped / Isolated Deployments
If your internal server cannot access the public internet:
1. Complete the Docker build on a machine connected to the internet.
2. Export the container image to a tarball archive:
   ```bash
   docker save research-suite:latest > research-suite-latest.tar
   ```
3. Copy the archive file to your internal server via secure SFTP or drive transfer.
4. Load the image inside the internal docker daemon:
   ```bash
   docker load < research-suite-latest.tar
   ```

### CPU vs GPU Allocation
By default, PyTorch and HuggingFace models run on CPU inside containerized environments. If a GPU (NVIDIA Cuda) is available on the internal server:
1. Use an NVIDIA-backed CUDA runtime base image (e.g., `nvidia/cuda:11.8.0-runtime-ubuntu22.04`).
2. Install PyTorch with CUDA support.
3. Configure the docker-compose/task definitions to allocate standard GPU access to containers.
