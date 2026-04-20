FROM python:3.10-slim

# Python Optimizations für schnelleren Start
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set Python path for proper module imports
ENV PYTHONPATH=/app/src

# Workspace configuration
ENV WORKSPACE_PATH=/workspace

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build frontend
RUN cd frontend && npm install && npm run build

# Create necessary directories
RUN mkdir -p logs data output /workspace

# Expose port
EXPOSE 8000

# Define volume for persistent file storage
VOLUME ["/app/output"]

# Run the application as module
CMD ["python", "-m", "src.agent_server"]
