# ============================================================
# Stage 1: Python + Requirements
# ============================================================
FROM python:3.11-slim AS dependencies

WORKDIR /app

# Copy requirements file
COPY src/requirements.txt .

# Install Python libraries
RUN pip install --no-cache-dir -r requirements.txt


# ============================================================
# Stage 2: Application Code
# ============================================================
FROM dependencies AS application

WORKDIR /app

# Copy your project
COPY . .

# Expose FastAPI port
EXPOSE 8000

ENV PYTHONPATH=/app/src
# Run FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]