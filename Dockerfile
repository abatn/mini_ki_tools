FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set Python path for proper module imports
ENV PYTHONPATH=/app/src

# Workspace configuration
# WORKSPACE_PATH: Host directory to mount as workspace (read/write/execute)
# Default workspace if not specified
ENV WORKSPACE_PATH=/workspace

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data output /workspace

# Expose port
EXPOSE 8000

# Define volume for persistent file storage
VOLUME ["/app/output"]

# Mount workspace from host (must be provided at runtime)
# Usage: docker run -v /host/path:/workspace mini-ki-tools
# Or use WORKSPACE_PATH environment variable to specify custom mount

# Run the application as module
CMD ["python", "-m", "src.agent_server"]
