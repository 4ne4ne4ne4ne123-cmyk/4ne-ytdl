FROM python:3.11-slim

# 🔥 unzip を追加！
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Deno のインストール（今度は unzip があるので成功する）
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
# cookies.txt がなくてもビルドが通るようにダミーを作成
RUN touch cookies.txt

EXPOSE 8080
CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:8080"]
