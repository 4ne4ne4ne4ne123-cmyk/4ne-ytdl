from flask import Flask, request, send_file, jsonify
import subprocess
import os
import re
import shutil
import logging

# ============================================================
# ログ設定（Renderのログで見やすく）
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================
# 設定（環境変数 or デフォルト値）
# ============================================================
# Cookieファイルのパス（Secret Files を優先）
COOKIE_FILE = os.getenv('COOKIE_PATH', '/etc/secrets/cookies.txt')
if not os.path.exists(COOKIE_FILE):
    COOKIE_FILE = 'cookies.txt'
    logger.warning(f"⚠️ Secret Files not found. Using local {COOKIE_FILE}")

# WARPプロキシ（docker-compose のサービス名を指定）
PROXY = os.getenv('YDL_PROXY', 'socks5://warp-proxy:40000')

# User-Agent（ブロック回避用）
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

logger.info(f"🍪 Cookie file: {COOKIE_FILE} (exists: {os.path.exists(COOKIE_FILE)})")
logger.info(f"🔧 Proxy: {PROXY}")

# ============================================================
# ダウンロード処理
# ============================================================
def download_media(video_id, media_type, container, quality, audio_format):
    url = f"https://www.youtube.com/watch?v={video_id}"

    # ---------- 音声 ----------
    if media_type == 'audio':
        formats_to_try = [audio_format, '139', '249', 'bestaudio']
        for fmt in formats_to_try:
            logger.info(f"🔍 音声フォーマット '{fmt}' を試しています...")
            result = try_download(url, fmt, audio_only=True)
            if result:
                return result
        raise Exception("すべての音声フォーマットでダウンロードに失敗しました")

    # ---------- 動画 ----------
    else:
        # 画質 → 高さ（height）に変換
        quality_map = {
            '144': 144, '240': 240, '360': 360,
            '480': 480, '720': 720, '1080': 1080, '2160': 2160
        }
        height = quality_map.get(quality, 720)

        if container == 'mp4':
            format_spec = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
        else:  # webm
            format_spec = f'bestvideo[height<={height}][ext=webm]+bestaudio[ext=webm]/best[height<={height}][ext=webm]/best'

        logger.info(f"🔍 動画: コンテナ={container}, 画質={quality}p, フォーマット='{format_spec}'")
        result = try_download(url, format_spec, audio_only=False)
        if result:
            return result
        raise Exception(f"動画ダウンロードに失敗しました (コンテナ={container}, 画質={quality})")

# ============================================================
# yt-dlp 実行（プロキシ対応）
# ============================================================
def try_download(url, format_spec, audio_only):
    cmd = [
        'yt-dlp',
        '--format', format_spec,
        '--user-agent', USER_AGENT,
        '--proxy', PROXY,  # 🔥 WARPプロキシ経由！
        '-o', '%(title)s.%(ext)s',
        url
    ]

    # Cookieがあれば使う
    if os.path.exists(COOKIE_FILE):
        cmd.insert(1, '--cookies')
        cmd.insert(2, COOKIE_FILE)
        logger.info(f"🍪 Cookieを使用: {COOKIE_FILE}")
    else:
        logger.warning("⚠️ Cookieなしで実行")

    # 音声の場合は mp3 に変換
    if audio_only:
        cmd.append('--extract-audio')
        cmd.append('--audio-format')
        cmd.append('mp3')

    logger.info(f"🔧 実行コマンド: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)

        # ダウンロードされたファイルを探す
        exts = ('.m4a', '.webm', '.mp4', '.mkv', '.mp3')
        downloaded_files = [f for f in os.listdir('.') if f.endswith(exts)]
        if not downloaded_files:
            logger.warning("⚠️ ファイルが見つかりませんでした")
            return None

        # 最新のファイルを返す
        latest_file = max(downloaded_files, key=os.path.getctime)
        logger.info(f"✅ ダウンロード成功: {latest_file}")
        return latest_file

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else '不明なエラー'
        logger.error(f"❌ yt-dlp 実行失敗: {stderr}")
        return None
    except Exception as e:
        logger.error(f"❌ 予期せぬエラー: {e}")
        return None

# ============================================================
# API エンドポイント
# ============================================================
@app.route('/')
def index():
    return "OK"

@app.route('/download', methods=['GET'])
def download():
    video_id = request.args.get('video')
    media_type = request.args.get('type', 'audio')
    container = request.args.get('container', 'mp4')
    quality = request.args.get('quality', '720')
    audio_format = request.args.get('format', '139')

    # バリデーション
    if not video_id:
        return jsonify({'error': 'videoパラメータがありません'}), 400

    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        return jsonify({'error': '無効な動画IDです'}), 400

    if media_type == 'video':
        if container not in ['mp4', 'webm']:
            return jsonify({'error': '無効なコンテナ形式です (mp4 / webm)'}), 400
        if quality not in ['144', '240', '360', '480', '720', '1080', '2160']:
            return jsonify({'error': f'無効な画質です (144/240/360/480/720/1080/2160)'}), 400

    try:
        filename = download_media(video_id, media_type, container, quality, audio_format)
        if not filename:
            return jsonify({'error': 'ダウンロードに失敗しました'}), 500
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logger.error(f"❌ APIエラー: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================
# 起動
# ============================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
