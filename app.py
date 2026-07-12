import os
import json
import urllib.request
from flask import Flask, Response, request, jsonify, stream_with_context
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # CORS एरर से बचने के लिए

# यदि Render का IP ब्लॉक हो जाता है, तो इन पब्लिक API सर्वर्स से ऑडियो यूआरएल निकाला जाएगा
def get_stream_from_piped(video_id):
    instances = [
        "https://pipedapi.leptons.xyz",
        "https://pipedapi.kavin.rocks",
        "https://piped-api.lunar.icu",
        "https://pipedapi.r4fo.com",
        "https://piped-api.garudalinux.org"
    ]
    for base_url in instances:
        try:
            url = f"{base_url}/streams/{video_id}"
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            )
            # 5 सेकंड का टाइमआउट ताकि स्लो सर्वर को तुरंत स्किप किया जा सके
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if "audioStreams" in data and len(data["audioStreams"]) > 0:
                    # सबसे पहला बेस्ट क्वालिटी ऑडियो यूआरएल रिटर्न करें
                    return data["audioStreams"][0]["url"]
        except Exception as e:
            print(f"Piped instance {base_url} failed: {e}")
            continue
    return None

@app.route('/')
def home():
    return "ISKCON Audio Stream Backend is Running! 🪔"

@app.route('/stream')
def stream():
    video_id = request.args.get('id')
    if not video_id:
        return jsonify({"error": "Missing video id"}), 400
    
    stream_url = None
    
    # लेयर 1: सबसे पहले सामान्य yt-dlp से ट्राई करें
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
        except Exception as e:
            print("yt-dlp failed (likely blocked by YouTube on datacenter IP):", e)
            
    # लेयर 2: यदि Render का IP ब्लॉक होने की वजह से yt-dlp फेल होता है, तो तुरंत Piped API का यूज़ करें
    if not stream_url:
        print("Falling back to Public Piped API instances...")
        stream_url = get_stream_from_piped(video_id)
        
    if not stream_url:
        return jsonify({"error": "Failed to extract audio stream from all sources."}), 500

    # लेयर 3: मोबाइल ब्राउज़र के IP Lock (403 error) को बायपास करने के लिए डेटा बाइट्स को पाइप/स्ट्रीम करें
    try:
        req = urllib.request.Request(
            stream_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        
        response_stream = urllib.request.urlopen(req, timeout=15)
        content_type = response_stream.headers.get('Content-Type', 'audio/mpeg')
        content_length = response_stream.headers.get('Content-Length', '')
        
        def generate(stream):
            try:
                while True:
                    chunk = stream.read(1024 * 32)  # 32KB के स्मूथ चंक्स में स्ट्रीम करें
                    if not chunk:
                        break
                    yield chunk
            except Exception as stream_err:
                print("Streaming pipe error:", stream_err)
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
        return jsonify({"error": f"Failed to pipe stream: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
