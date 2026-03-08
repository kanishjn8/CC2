FROM python:3.11-slim

# Install system deps needed by psycopg2, shapely, geoalchemy2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
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
