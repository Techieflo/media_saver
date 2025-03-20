from flask import Flask, request, jsonify
import subprocess
import json
import os
import instaloader
from urllib.parse import urlparse, parse_qs
from threading import Semaphore

app = Flask(__name__)

# Set a limit on the number of concurrent requests
MAX_CONCURRENT_REQUESTS = 5
semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)

# Helper function to fetch Instagram session ID
def get_instagram_session_id():
    """Fetch Instagram session ID from environment variables."""
    session_id = os.getenv('SESSION_ID')
    if not session_id:
        raise ValueError("Instagram session ID is not set in environment variables.")
    return session_id

# Helper function to get Instagram reel URL
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
        raise RuntimeError(f"Error fetching Instagram reel: {e}")

# Function to clean YouTube URL
def clean_youtube_url(url):
    """Extract video ID from YouTube URL and construct the clean URL."""
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
        if not video_id and 'shorts' in parsed_url.path:
            video_id = parsed_url.path.split('/')[-1]
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')
    else:
        return None
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None

# Function to get best video and audio URLs using cookies
def get_best_video_and_audio(clean_url):
    """Fetch the best video and audio streams using yt-dlp with cookies."""
    try:
        cookies = os.getenv("YT_COOKIES")
        if not cookies:
            raise ValueError("YouTube cookies are missing from environment variables.")
        
        # Write cookies to a temporary file
        cookies_path = "/tmp/cookies.txt"
        with open(cookies_path, "w") as cookie_file:
            cookie_file.write(cookies)
        
        command = [
            "yt-dlp", "--no-warnings", "-j", clean_url,
            "--cookies", cookies_path
        ]
        
        result = subprocess.run(
            command, capture_output=True, text=True, check=True
        )
        
        if not result.stdout:
            return {"error": "yt-dlp did not return any output."}
        
        try:
            video_info = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": "Failed to parse yt-dlp response."}
        
        if not isinstance(video_info, dict) or "formats" not in video_info:
            return {"error": "Unexpected yt-dlp response format."}
        
        best_video, best_audio = None, None
        for fmt in video_info.get("formats", []):
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                if not best_video or fmt["height"] > best_video["height"]:
                    best_video = fmt
            elif fmt.get("acodec") != "none":
                if not best_audio or fmt["abr"] > best_audio["abr"]:
                    best_audio = fmt
        
        if best_video and best_audio:
            return {"video_url": best_video["url"], "audio_url": best_audio["url"]}
        return {"error": "No suitable video or audio streams found."}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}

# API endpoint to get Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    session_id = get_instagram_session_id()
    if not url:
        return jsonify({'error': 'URL parameter is required.'}), 400
    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to get the best video and audio URLs
@app.route('/get_video_audio_urls', methods=['POST'])
def get_video_audio_urls_endpoint():
    """API endpoint to get video and audio URLs using cookies."""
    if not semaphore.acquire(blocking=False):
        return jsonify({"error": "Server overload; you are on a queue. Please wait."}), 503
    try:
        data = request.json
        youtube_url = data.get('url')
        if not youtube_url:
            return jsonify({"error": "YouTube URL is required"}), 400
        clean_url = clean_youtube_url(youtube_url)
        if not clean_url:
            return jsonify({"error": "Invalid YouTube URL"}), 400
        result = get_best_video_and_audio(clean_url)
        if "error" in result:
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
