from flask import Flask, request, send_file, jsonify
import yt_dlp
import os
import re
import subprocess

app = Flask(__name__)

COOKIE_FILE = "cookies.txt"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# 🔥 画質 → 高さ（height）のマッピング
QUALITY_HEIGHT = {
    '144': 144,
    '240': 240,
    '360': 360,
    '480': 480,
    '720': 720,
    '1080': 1080,
    '2160': 2160,
}

def get_video_format(container, quality):
    height = QUALITY_HEIGHT.get(quality, 720)
    if container == 'mp4':
        return f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
    else:  # webm
        return f'bestvideo[height<={height}][ext=webm]+bestaudio[ext=webm]/best[height<={height}][ext=webm]/best'

def download_media(video_id, media_type, container, quality, audio_format):
    url = f"https://www.youtube.com/watch?v={video_id}"

    if media_type == 'audio':
        formats_to_try = [audio_format, '139', '249', 'bestaudio']
        for fmt in formats_to_try:
            print(f"🔍 音声フォーマット '{fmt}' を試しています...")
            result = try_download(url, fmt, audio_only=True)
            if result:
                return result
        raise Exception("音声ダウンロードに失敗しました")

    else:  # video
        format_spec = get_video_format(container, quality)
        print(f"🔍 動画: コンテナ={container}, 画質={quality}p, フォーマット='{format_spec}'")
        result = try_download(url, format_spec, audio_only=False)
        if result:
            return result
        raise Exception(f"動画ダウンロードに失敗しました (コンテナ={container}, 画質={quality})")

def try_download(url, format_spec, audio_only):
    cmd = [
        'yt-dlp',
        '--format', format_spec,
        '--user-agent', USER_AGENT,
        '-o', '%(title)s.%(ext)s',
        url
    ]

    if audio_only:
        cmd.append('--extract-audio')
        cmd.append('--audio-format')
        cmd.append('mp3')

    if os.path.exists(COOKIE_FILE):
        cmd.insert(1, '--cookies')
        cmd.insert(2, COOKIE_FILE)

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        exts = ('.m4a', '.webm', '.mp4', '.mkv', '.mp3')
        downloaded_files = [f for f in os.listdir('.') if f.endswith(exts)]
        if not downloaded_files:
            return None
        latest_file = max(downloaded_files, key=os.path.getctime)
        print(f"✅ ダウンロード成功: {latest_file}")
        return latest_file
    except subprocess.CalledProcessError as e:
        print(f"❌ ダウンロード失敗: {e.stderr.decode() if e.stderr else '不明'}")
        return None

@app.route('/download', methods=['GET'])
def download():
    video_id = request.args.get('video')
    media_type = request.args.get('type', 'audio')
    container = request.args.get('container', 'mp4')
    quality = request.args.get('quality', '720')
    audio_format = request.args.get('format', '139')

    if not video_id:
        return jsonify({'error': 'videoパラメータがありません'}), 400

    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        return jsonify({'error': '無効な動画IDです'}), 400

    if media_type == 'video':
        if container not in ['mp4', 'webm']:
            return jsonify({'error': '無効なコンテナ形式です (mp4 / webm)'}), 400
        if quality not in QUALITY_HEIGHT:
            return jsonify({'error': f'無効な画質です ({", ".join(QUALITY_HEIGHT.keys())}p)'}), 400

    try:
        filename = download_media(video_id, media_type, container, quality, audio_format)
        if not filename:
            return jsonify({'error': 'ダウンロードに失敗しました'}), 500
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
