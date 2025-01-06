from flask import Flask, jsonify, request
import instaloader
import yt_dlp
import os
import base64
import requests
import subprocess
import json
from urllib.parse import urlparse, parse_qs

# Initialize Flask app
app = Flask(__name__)

# Helper function to download and save cookies from MediaFire
def download_and_save_cookies():
    """Download cookies file from MediaFire using the direct link and save it locally."""
    download_link = os.getenv('downloadlink')  # Get download link from environment variable
    cookies_path = 'cookies.txt'

    if download_link:
        try:
            response = requests.get(download_link)
            response.raise_for_status()
            with open(cookies_path, 'wb') as f:
                f.write(response.content)
            return cookies_path
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error downloading cookies file: {e}")
    else:
        raise ValueError("No download link found in environment variables.")

# Helper function to fetch Instagram session ID
def get_instagram_session_id():
    session_id = os.getenv('SESSION_ID')
    if not session_id:
        raise ValueError("Instagram session ID is not set in environment variables.")
    return session_id

# Helper function to check Instagram session validity
def is_instagram_session_valid(session_id):
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        instaloader.Profile.from_username(loader.context, "instagram")
        return True
    except Exception as e:
        print(f"Instagram session validation error: {e}")
        return False

# Helper function to get Instagram reel URL
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

# Helper function to clean YouTube URL by extracting only the video ID after 'v='
def clean_youtube_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    video_id = query_params.get('v', [None])[0]
    if video_id:
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        return clean_url
    else:
        return None

# API endpoint for Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    url = request.args.get('url')
    session_id = get_instagram_session_id()

    if not url:
        return handle_error('URL parameter is required.')
    if not is_instagram_session_valid(session_id):
        return handle_error('Invalid or expired Instagram session ID.', 401)

    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# API endpoint for YouTube video URL
@app.route('/get_youtube_video_url', methods=['GET'])
def youtube_video_url_api():
    url = request.args.get('url')
    if not url:
        return handle_error('URL parameter is required.')
    try:
        clean_url = clean_youtube_url(url)
        if not clean_url:
            return handle_error('Invalid YouTube URL. No video ID found.', 400)

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
            if format.get('vcodec') != 'none' and format.get('acodec') != 'none':
                if best_video is None or format['height'] > best_video['height']:
                    best_video = format
                if best_audio is None or format['abr'] > best_audio['abr']:
                    best_audio = format

        if best_video and best_audio:
            return jsonify({
                "best_video_url": best_video['url'],
                "best_audio_url": best_audio['url']
            })
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Helper function to handle errors
def handle_error(message, status_code=400):
    return jsonify({'error': message}), status_code

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
