FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set Python path for proper module imports
ENV PYTHONPATH=/app/src

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data output

# Expose port
EXPOSE 8000

# Define volume for persistent file storage
VOLUME ["/app/output"]

# Run the application as module
CMD ["python", "-m", "src.agent_server"]
