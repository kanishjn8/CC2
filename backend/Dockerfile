FROM python:3.11-slim

# Install system deps needed by psycopg2, shapely, geoalchemy2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (used by the project for dependency management)
RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv into the system Python (no venv needed in Docker)
RUN uv pip install --system --no-cache \
        fastapi \
        "uvicorn[standard]" \
        sqlalchemy \
        psycopg2-binary \
        geoalchemy2 \
        shapely \
        simpy \
        numpy \
        pandas \
        python-dotenv \
        scikit-learn \
        "google-genai>=1.0.0" \
        langgraph \
        langgraph-checkpoint-postgres

# Copy application code
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
