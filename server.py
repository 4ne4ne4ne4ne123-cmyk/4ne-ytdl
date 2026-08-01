from flask import Flask, request, send_file, jsonify
import yt_dlp
import os
import re
import shutil
import subprocess

app = Flask(__name__)

COOKIE_FILE = "cookies.txt"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def download_audio(video_id, requested_format):
    url = f"https://www.youtube.com/watch?v={video_id}"
    formats_to_try = [requested_format, '139', '249', 'bestaudio']

    for fmt in formats_to_try:
        print(f"🔍 フォーマット '{fmt}' を試しています...")

        cmd = [
            'yt-dlp',
            '--format', fmt,
            '--user-agent', USER_AGENT,
            '-o', '%(title)s.%(ext)s',
            url
        ]

        if os.path.exists(COOKIE_FILE):
            cmd.insert(1, '--cookies')
            cmd.insert(2, COOKIE_FILE)

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            downloaded_files = [f for f in os.listdir('.') if f.endswith(('.m4a', '.webm', '.mp4'))]
            if not downloaded_files:
                continue

            for original_file in downloaded_files:
                base_name = os.path.splitext(original_file)[0]
                mp3_name = base_name + '.mp3'
                shutil.copy2(original_file, mp3_name)
                return mp3_name

        except subprocess.CalledProcessError as e:
            print(f"❌ フォーマット '{fmt}' で失敗: {e.stderr.decode() if e.stderr else '不明'}")
            continue

    raise Exception("すべてのフォーマットでダウンロードに失敗しました")

@app.route('/download', methods=['GET'])
def download():
    video_id = request.args.get('video')
    fmt = request.args.get('format', '139')

    if not video_id:
        return jsonify({'error': 'videoパラメータがありません'}), 400

    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        return jsonify({'error': '無効な動画IDです'}), 400

    try:
        filename = download_audio(video_id, fmt)
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
