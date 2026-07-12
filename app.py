import os
import urllib.request
from flask import Flask, Response, request, jsonify, stream_with_context
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # CORS एरर से बचने के लिए

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
            stream_url = info['url']
            
            # YouTube IP Lock को बायपास करने के लिए हम सीधे ऑडियो बाइट्स को पाइप/स्ट्रीम करेंगे
            req = urllib.request.Request(
                stream_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            )
            
            # यूट्यूब से कनेक्शन खोलें
            response_stream = urllib.request.urlopen(req)
            
            content_type = response_stream.headers.get('Content-Type', 'audio/mpeg')
            content_length = response_stream.headers.get('Content-Length', '')
            
            # चंक्स में डेटा रीड करके क्लाइंट को भेजना (पाइपिंग)
            def generate(stream):
                try:
                    while True:
                        chunk = stream.read(1024 * 32) # 32KB के छोटे चंक्स में भेजना
                        if not chunk:
                            break
                        yield chunk
                except Exception as e:
                    print("Streaming error:", e)
                finally:
                    stream.close()

            headers = {
                'Content-Type': content_type,
                'Accept-Ranges': 'bytes'
            }
            if content_length:
                headers['Content-Length'] = content_length

            return Response(stream_with_context(generate(response_stream)), headers=headers)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
