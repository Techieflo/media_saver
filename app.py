from flask import Flask, request, jsonify
import subprocess
import json
import requests
import instaloader
import base64
from urllib.parse import urlparse, parse_qs
import os

app = Flask(__name__)

# Helper function to fetch Instagram session ID
def get_instagram_session_id():
    """Fetch Instagram session ID from environment variables."""
    session_id = os.getenv('SESSION_ID')
    if not session_id:
        raise ValueError("Instagram session ID is not set in environment variables.")
    print(f"Session ID: {session_id}")  # Debugging output
    return session_id

# Helper function to check if the Instagram session ID is valid
def is_instagram_session_valid(session_id):
    """Check if the provided session ID is valid for Instagram."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        # Test with a public profile
        instaloader.Profile.from_username(loader.context, "instagram")
        print("Session is valid")  # Debugging output
        return True
    except Exception as e:
        print(f"Instagram session validation error: {e}")  # Debugging output
        return False

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
    except instaloader.exceptions.InstaloaderException as e:
        raise RuntimeError(f"Instaloader error: {e}")
    except Exception as e:
        raise RuntimeError(f"Error fetching Instagram reel: {e}")

# Path to cookies.txt file (adjust for Render environment)
COOKIES_PATH = "/data/cookies.txt"

# Function to clean YouTube URL by extracting only the video ID after 'v='
def clean_youtube_url(url):
    """Extract video ID from YouTube URL and construct the clean URL."""
    parsed_url = urlparse(url)

    # Handle standard YouTube URLs
    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]

        # Handle shorts URLs
        if not video_id and 'shorts' in parsed_url.path:
            video_id = parsed_url.path.split('/')[-1]

    # Handle shortened youtu.be URLs
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')

    else:
        return None  # Return None if the URL is not a recognized YouTube URL

    # Construct the clean YouTube URL if a video ID was found
    if video_id:
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        return clean_url

    return None

# Function to get the best video and audio URLs
def get_best_video_and_audio(clean_url, cookies_path):
    """Fetch the best video and audio streams using yt-dlp."""
    try:
        command = [
            "yt-dlp", "--no-warnings", "-j", clean_url,
            # "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", 
            # "--no-check-certificate"
        ]

        if cookies_path:
            command.extend(["--cookies", cookies_path])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        video_info = json.loads(result.stdout)

        best_video = None
        best_audio = None

        for fmt in video_info["formats"]:
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                if not best_video or fmt["height"] > best_video["height"]:
                    best_video = fmt
            elif fmt.get("acodec") != "none":
                if not best_audio or fmt["abr"] > best_audio["abr"]:
                    best_audio = fmt

        if best_video and best_audio:
            return {"video_url": best_video["url"], "audio_url": best_audio["url"]}
        else:
            return {"error": "No suitable video or audio streams found."}
    except subprocess.CalledProcessError as e:
        return {"error": f"yt-dlp error: {e}"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parsing error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}

# API endpoint to get Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    session_id = get_instagram_session_id()  # Fetch session ID from environment

    if not url:
        return jsonify({'error': 'URL parameter is required.'}), 400

    if not is_instagram_session_valid(session_id):
        return jsonify({'error': 'Invalid or expired Instagram session ID.'}), 401

    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to get the best video and audio URLs
@app.route('/get_video_audio_urls', methods=['POST'])
def get_video_audio_urls_endpoint():
    """API endpoint to get the best video and audio URLs from YouTube."""
    try:
        data = request.json
        youtube_url = data.get('url')

        if not youtube_url:
            return jsonify({"error": "YouTube URL is required"}), 400

        clean_url = clean_youtube_url(youtube_url)
        if not clean_url:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        result = get_best_video_and_audio(clean_url, COOKIES_PATH)

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        return jsonify({
            "message": "Successfully retrieved video and audio URLs",
            "video_url": result["video_url"],
            "audio_url": result["audio_url"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
