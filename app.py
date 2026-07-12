import os
from flask import Flask, redirect, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # यह आपके HTML को इस Python API से कनेक्ट करने की अनुमति देता है

@app.route('/')
def home():
    return "ISKCON Audio Stream Backend is Running! 🪔"

@app.route('/stream')
def stream():
    video_id = request.args.get('id')
    if not video_id:
        return jsonify({"error": "Missing video id"}), 400
    
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            # direct audio URL पर redirect करें
            return redirect(info['url'])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Render.com ऑटोमैटिकली PORT एनवायरनमेंट वेरिएबल देता है
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
