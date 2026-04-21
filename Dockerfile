FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ENV PYTHONPATH=/app/src
ENV WORKSPACE_PATH=/workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY frontend/build/ ./frontend/build/

RUN mkdir -p logs data output /workspace

EXPOSE 8000

VOLUME ["/app/output"]

CMD ["python", "-m", "src.agent_server"]