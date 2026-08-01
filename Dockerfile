FROM python:3.11-slim

# ffmpeg + nodejs をインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY cookies.txt .

EXPOSE 8080
CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:8080"]
