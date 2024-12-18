from flask import Flask, jsonify, request
import instaloader
import yt_dlp
import os
import base64
import requests

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
            response.raise_for_status()  # Ensure we handle any errors in downloading the file
            
            with open(cookies_path, 'wb') as f:
                f.write(response.content)
            return cookies_path
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error downloading cookies file: {e}")
    else:
        raise ValueError("No download link found in environment variables.")

# Helper function to fetch Instagram session ID
def get_instagram_session_id():
    """Fetch Instagram session ID from environment variables."""
    session_id = os.getenv('SESSION_ID')
    if not session_id:
        raise ValueError("Instagram session ID is not set in environment variables.")
    return session_id

# Helper function to check if the Instagram session ID is valid
def is_instagram_session_valid(session_id):
    """Check if the provided session ID is valid for Instagram."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        # Test with a public profile
        instaloader.Profile.from_username(loader.context, "instagram")
        return True
    except Exception as e:
        print(f"Instagram session validation error: {e}")
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
    except Exception as e:
        raise RuntimeError(f"Error fetching Instagram reel: {e}")

# Helper function to get YouTube video URL using yt-dlp
def get_youtube_video_url(url):
    """Fetch the direct video URL for YouTube."""
    try:
        cookies_path = download_and_save_cookies()  # Use the downloaded cookie path
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'cookies': cookies_path,  # Pass the cookies file to yt-dlp
            'noplaylist': True,  # Disable playlist extraction (if not needed)
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                return result['entries'][0]['url']
            return result['url']
    except Exception as e:
        raise RuntimeError(f"Error fetching YouTube video: {e}")

# Helper function to handle errors
def handle_error(message, status_code=400):
    """Return a structured error response."""
    return jsonify({'error': message}), status_code

# API endpoint to get Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    session_id = get_instagram_session_id()  # Fetch session ID from environment

    if not url:
        return handle_error('URL parameter is required.')

    if not is_instagram_session_valid(session_id):
        return handle_error('Invalid or expired Instagram session ID.', 401)

    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# API endpoint to get YouTube video URL
@app.route('/get_youtube_video_url', methods=['GET'])
def youtube_video_url_api():
    """API endpoint to get the YouTube video URL."""
    url = request.args.get('url')

    if not url:
        return handle_error('URL parameter is required.')

    try:
        video_url = get_youtube_video_url(url)
        return jsonify({'video_url': video_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Render needs to listen on 0.0.0.0 for IP binding
