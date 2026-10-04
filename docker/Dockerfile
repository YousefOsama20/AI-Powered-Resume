# ============================================================
# Python + Requirements + Application
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Copy requirements file
COPY src/requirements.txt .

# Install Python libraries
RUN pip install requirements.txt

# Copy application code
COPY . .

# FastAPI port
EXPOSE 8000

# Python import path
ENV PYTHONPATH=/app/src

# Run FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]