FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Install uv & dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache .

# Application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
