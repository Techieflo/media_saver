from flask import Flask, request, jsonify
import subprocess
import json
import os
import instaloader
import logging
from urllib.parse import urlparse, parse_qs
from threading import Semaphore

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set a limit on the number of concurrent requests
MAX_CONCURRENT_REQUESTS = 5
semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)

def get_env_variable(key, error_message):
    """Fetch an environment variable and raise an error if missing."""
    value = os.getenv(key)
    if not value:
        raise ValueError(error_message)
    return value

def get_instagram_reel_url(url, session_id):
    """Fetch the direct video URL for Instagram Reels."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        shortcode = url.split('/')[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        
        if not post.is_video:
            raise RuntimeError("The provided URL does not point to a video reel.")
        
        return post.video_url
    except Exception as e:
        logging.error(f"Error fetching Instagram reel: {e}")
        raise RuntimeError(f"Error fetching Instagram reel: {e}")

def clean_youtube_url(url):
    """Extract video ID from YouTube URL and construct the clean URL."""
    parsed_url = urlparse(url)
    video_id = None
    
    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
        if not video_id and 'shorts' in parsed_url.path:
            video_id = parsed_url.path.split('/')[-1]
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')
    
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None

def get_best_video_and_audio(clean_url):
    """Fetch the best video and audio streams using yt-dlp with cookies."""
    try:
        cookies = get_env_variable("YT_COOKIES", "YouTube cookies are missing from environment variables.")
        cookies_path = "/tmp/cookies.txt"
        
        with open(cookies_path, "w") as cookie_file:
            cookie_file.write(cookies)
        
        command = ["yt-dlp", "--no-warnings", "-j", clean_url, "--cookies", cookies_path]
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        os.remove(cookies_path)  # Cleanup temporary cookies file
        
        if not result.stdout:
            return {"error": "yt-dlp did not return any output."}
        
        try:
            video_info = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": "Failed to parse yt-dlp response."}
        
        best_video, best_audio = None, None
        for fmt in video_info.get("formats", []):
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                if not best_video or fmt["height"] > best_video["height"]:
                    best_video = fmt
            elif fmt.get("acodec") != "none":
                if not best_audio or fmt["abr"] > best_audio["abr"]:
                    best_audio = fmt
        
        return {
            "video_url": best_video["url"] if best_video else None,
            "audio_url": best_audio["url"] if best_audio else None,
            "error": "No suitable video or audio streams found." if not best_video or not best_audio else None
        }
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {"error": str(e)}

@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required.'}), 400
    try:
        session_id = get_env_variable('SESSION_ID', "Instagram session ID is missing.")
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_video_audio_urls', methods=['POST'])
def get_video_audio_urls_endpoint():
    """API endpoint to get video and audio URLs using cookies."""
    if not semaphore.acquire(blocking=False):
        return jsonify({"error": "Server overload; please try again later."}), 503
    try:
        data = request.json
        youtube_url = data.get('url')
        if not youtube_url:
            return jsonify({"error": "YouTube URL is required."}), 400
        
        clean_url = clean_youtube_url(youtube_url)
        if not clean_url:
            return jsonify({"error": "Invalid YouTube URL."}), 400
        
        result = get_best_video_and_audio(clean_url)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        
        return jsonify({
            "message": "Successfully retrieved video and audio URLs",
            "video_url": result["video_url"],
            "audio_url": result["audio_url"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        semaphore.release()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
