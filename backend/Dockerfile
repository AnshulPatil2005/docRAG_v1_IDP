# Dockerfile for the API service
FROM python:3.11-slim

WORKDIR /app

# Copy requirements file first for caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for API (FastAPI/Uvicorn)
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
