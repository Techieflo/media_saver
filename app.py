from flask import Flask, request, jsonify
import subprocess
import json
import requests
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Function to clean YouTube URL by extracting only the video ID after 'v='
def clean_youtube_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    video_id = query_params.get('v', [None])[0]
    if video_id:
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        return clean_url
    else:
        return None

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    data = request.json
    youtube_url = data.get('url')

    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400

    clean_url = clean_youtube_url(youtube_url)
    if not clean_url:
        return jsonify({"error": "Invalid YouTube URL. No video ID found."}), 400

    try:
        result = subprocess.run(
            ['yt-dlp', '--no-warnings', '-j', clean_url],
            capture_output=True,
            text=True,
            check=True
        )

        video_info = json.loads(result.stdout)

        best_video = None
        best_audio = None

        for format in video_info['formats']:
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
            return jsonify(response_data), 200
        else:
            return jsonify({"error": "No suitable video or audio formats found."}), 404

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error during yt-dlp execution: {str(e)}"}), 500
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Error decoding JSON: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
