FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DASHBOARD_HOST=0.0.0.0 DASHBOARD_PORT=8765

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN mkdir -p /app/input /app/sorted /app/docling_json
EXPOSE 8765
VOLUME ["/app/input", "/app/sorted", "/app/docling_json"]
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/status', timeout=3)"

CMD ["python", "dashboard.py"]
