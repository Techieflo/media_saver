from flask import Flask, request, jsonify
import subprocess
import json
import requests
from urllib.parse import urlparse, parse_qs
import os

app = Flask(__name__)

# Path to cookies.txt file (adjust for Render environment)
COOKIES_PATH = "/data/cookies.txt"

# Function to clean YouTube URL by extracting only the video ID after 'v='
def clean_youtube_url(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Extract the query parameters
    query_params = parse_qs(parsed_url.query)

    # Extract video ID from the 'v' parameter and construct the clean URL
    video_id = query_params.get('v', [None])[0]
    if video_id:
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        return clean_url
    return None

# Function to get the best video and audio URLs
def get_best_video_and_audio(clean_url, cookies_path):
    try:
        # Run yt-dlp to fetch video information in JSON format
        command = ["yt-dlp", "--no-warnings", "-j", clean_url]
        if cookies_path:
            command.extend(["--cookies", cookies_path])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the JSON output
        video_info = json.loads(result.stdout)

        # Find the best video and audio streams
        best_video = None
        best_audio = None

        for fmt in video_info["formats"]:
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                if not best_video or fmt["height"] > best_video["height"]:
                    best_video = fmt
            elif fmt.get("acodec") != "none":
                if not best_audio or fmt.get("abr") > best_audio["abr"]:
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

# API endpoint to get the best video and audio URLs
@app.route('/get_video_audio_urls', methods=['POST'])
def get_video_audio_urls_endpoint():
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
