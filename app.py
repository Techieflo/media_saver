from flask import Flask, request, jsonify
import subprocess
import json
import requests
import instaloader
import os
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Path to cookies.txt file in Render Secrets
COOKIES_PATH = "etc/secrets/cookies.txt"

# Function to clean YouTube URL by extracting only the video ID

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

# Function to get the best video and audio URLs
def get_best_video_and_audio(clean_url, cookies_path):
    """Fetch the best video and audio streams using yt-dlp."""
    try:
        command = [
            "yt-dlp", "--no-warnings", "-j", clean_url,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", 
            "--no-check-certificate"
        ]

        if os.path.exists(cookies_path):
            command.extend(["--cookies", cookies_path])
        else:
            return {"error": "Cookies file not found in Render Secrets."}

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        video_info = json.loads(result.stdout)
        best_video, best_audio = None, None

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

# API endpoint to get YouTube video and audio URLs
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
