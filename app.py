from flask import Flask, request, jsonify
import subprocess
import json
import requests
import instaloader
import os
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# GitHub raw URL of the cookies.txt file
GITHUB_COOKIES_URL = "https://raw.githubusercontent.com/Techieflo/media_saver/main/cookies.txt"


# Function to fetch the cookies.txt file from GitHub
def fetch_cookies_from_github():
    """Fetch cookies.txt content from GitHub and return it as a string."""
    try:
        response = requests.get(GITHUB_COOKIES_URL)
        response.raise_for_status()  # Raise an error for failed requests
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching cookies from GitHub: {e}")
        return None

# Function to clean YouTube URL by extracting the video ID
def clean_youtube_url(url):
    """Extract video ID from YouTube URL and construct a clean URL."""
    parsed_url = urlparse(url)

    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]

        if not video_id and 'shorts' in parsed_url.path:
            video_id = parsed_url.path.split('/')[-1]

    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')

    else:
        return None  # Not a recognized YouTube URL

    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None

# Function to get the best video and audio URLs
def get_best_video_and_audio(clean_url, cookies_content):
    """Fetch best video and audio streams using yt-dlp."""
    try:
        command = [
            "yt-dlp", "--no-warnings", "-j", clean_url,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", 
            "--no-check-certificate",
            "--cookies-from-file", "-"  # Read cookies from stdin
        ]

        result = subprocess.run(
            command,
            input=cookies_content,
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

# API endpoint to get YouTube video and audio URLs
@app.route('/get_video_audio_urls', methods=['POST'])
def get_video_audio_urls_endpoint():
    """API endpoint to get best video and audio URLs from YouTube."""
    try:
        data = request.json
        youtube_url = data.get('url')

        if not youtube_url:
            return jsonify({"error": "YouTube URL is required"}), 400

        clean_url = clean_youtube_url(youtube_url)
        if not clean_url:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        # Fetch cookies from GitHub
        cookies_content = fetch_cookies_from_github()
        if not cookies_content:
            return jsonify({"error": "Failed to load cookies from GitHub"}), 500

        result = get_best_video_and_audio(clean_url, cookies_content)

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
