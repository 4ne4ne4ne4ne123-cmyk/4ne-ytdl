from flask import Flask
import yt_dlp  # ← これを追加

app = Flask(__name__)

@app.route('/')
def index():
    return "OK"
