from flask import Flask, request, jsonify
import subprocess
import json
import requests
import re
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

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
    else:
        return None

# API endpoint to process the YouTube URL
@app.route('/get_video', methods=['POST'])
def get_video():
    # Extract URL from the request
    data = request.get_json()
    youtube_url = data.get('url')

    if not youtube_url:
        return jsonify({"error": "YouTube URL is required"}), 400

    # Clean the URL by removing unnecessary parameters
    clean_url = clean_youtube_url(youtube_url)
    if not clean_url:
        return jsonify({"error": "Invalid YouTube URL. No video ID found."}), 400

    # Run yt-dlp to fetch available formats in JSON format and list the best quality
    try:
        result = subprocess.run(
            ['yt-dlp', '--no-warnings', '-j', clean_url],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the JSON output
        video_info = json.loads(result.stdout)

        # Find the best video with both video and audio
        best_video = None
        best_audio = None

        for format in video_info['formats']:
            # Prefer a format with both video and audio
            if format.get('vcodec') != 'none' and format.get('acodec') != 'none':
                if best_video is None or format['height'] > best_video['height']:
                    best_video = format
                if best_audio is None or format['abr'] > best_audio['abr']:
                    best_audio = format

        if best_video and best_audio:
            response_data = {
                "best_video_url": best_video['url'],
                "best_audio_url": best_audio['url']
            }

            # Optionally, verify content type by sending a HEAD request
            video_url = best_video['url']
            response = requests.head(video_url)
            content_type = response.headers.get('Content-Type')

            if 'video' in content_type:
                response_data["video_valid"] = True
            else:
                response_data["video_valid"] = False

            return jsonify(response_data)

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": f"yt-dlp error: {e.stderr}"
        }), 500
    except json.JSONDecodeError as e:
        return jsonify({
            "error": f"Error decoding JSON: {e}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"An unexpected error occurred: {e}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
