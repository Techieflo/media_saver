from flask import Flask, request, jsonify
import subprocess
import json
import yt_dlp
import requests
from urllib.parse import urlparse, parse_qs

# Initialize Flask app
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

# Function to get the best video URL using yt_dlp
def get_video_url(url):
    ydl_opts = {
        'format': 'best',  # Choose the best video quality
        'quiet': True,     # Suppress output
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)  # Extract info without downloading
        if 'entries' in result:
            video_url = result['entries'][0]['url']  # Get the direct video URL
        else:
            video_url = result['url']
        return video_url

# Endpoint for detailed YouTube video information
@app.route('/getyoutubevideo', methods=['POST'])
def getyoutubevideo():
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
        return jsonify({"error": f"Error during yt-dlp execution: {e}"}), 500
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Error decoding JSON: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

# Endpoint for extracting direct video URL
@app.route('/get_video_url', methods=['GET'])
def video_url_api():
    # Get the URL parameter from the request
    url = request.args.get('url')

    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400

    try:
        # Get the video URL
        video_url = get_video_url(url)
        return jsonify({'video_url': video_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
