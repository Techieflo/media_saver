from flask import Flask, request, jsonify
import subprocess
import json
import instaloader
import os
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Fetch Instagram session ID from environment

def get_instagram_session_id():
    session_id = os.getenv('SESSION_ID')
    if not session_id:
        raise ValueError("Instagram session ID is not set in environment variables.")
    return session_id

# Validate Instagram session ID
def is_instagram_session_valid(session_id):
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        instaloader.Profile.from_username(loader.context, "instagram")
        return True
    except Exception:
        return False

# Fetch Instagram Reel URL
def get_instagram_reel_url(url, session_id):
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        shortcode = url.split('/')[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        
        if not post.is_video:
            raise RuntimeError("The provided URL does not point to a video reel.")
        
        return post.video_url
    except Exception as e:
        raise RuntimeError(f"Error fetching Instagram reel: {e}")

# Extract and clean YouTube video URL
def clean_youtube_url(url):
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        video_id = parse_qs(parsed_url.query).get('v', [None])[0]
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')
    else:
        return None
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None

# Fetch the best video and audio streams using yt-dlp
def get_best_video_and_audio(clean_url):
    try:
        cookies_path = os.getenv("YOUTUBE_COOKIES_PATH", "")
        command = [
            "yt-dlp", "--no-warnings", "-j", clean_url,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "--no-check-certificate"
        ]
        if cookies_path:
            command.extend(["--cookies", cookies_path])
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        video_info = json.loads(result.stdout)
        
        best_video = max((fmt for fmt in video_info["formats"] if fmt.get("vcodec") != "none"),
                         key=lambda fmt: fmt.get("height", 0), default=None)
        best_audio = max((fmt for fmt in video_info["formats"] if fmt.get("acodec") != "none"),
                         key=lambda fmt: fmt.get("abr", 0), default=None)
        
        return {
            "video_url": best_video["url"] if best_video else None,
            "audio_url": best_audio["url"] if best_audio else None
        }
    except Exception as e:
        return {"error": str(e)}

# API endpoint to get Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required.'}), 400
    session_id = get_instagram_session_id()
    if not is_instagram_session_valid(session_id):
        return jsonify({'error': 'Invalid or expired Instagram session ID.'}), 401
    try:
        return jsonify({'video_url': get_instagram_reel_url(url, session_id)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to get YouTube video and audio URLs
@app.route('/get_video_audio_urls', methods=['POST'])
def get_video_audio_urls_endpoint():
    try:
        youtube_url = request.json.get('url')
        if not youtube_url:
            return jsonify({"error": "YouTube URL is required"}), 400
        clean_url = clean_youtube_url(youtube_url)
        if not clean_url:
            return jsonify({"error": "Invalid YouTube URL"}), 400
        result = get_best_video_and_audio(clean_url)
        return jsonify(result if "error" not in result else {"error": result["error"]}), 500 if "error" in result else 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
