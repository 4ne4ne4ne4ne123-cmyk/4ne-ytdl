FROM python:3.11-slim

# ============================================
# システム依存パッケージをインストール
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Python 依存関係をインストール
# ============================================
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# アプリ本体をコピー
# ============================================
COPY server.py .
COPY index.html .
COPY cookies.txt .

# ============================================
# 起動
# ============================================
CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:8080"]
