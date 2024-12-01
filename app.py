from flask import Flask, jsonify, request
import instaloader
import yt_dlp
import os

# Initialize Flask app
app = Flask(__name__)

# Helper function to fetch cookies from environment variables
def get_session_cookies():
    """Fetch session cookies from environment variables."""
    session_id = os.getenv('SESSION_ID')
    if not session_id:
        raise ValueError("Session ID is not set in environment variables.")
    return session_id

# Helper function to check if the session ID is valid (for Instagram)
def is_instagram_session_valid(session_id):
    """Check if the provided session ID is valid for Instagram."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        # Test with a simple query to a public Instagram profile
        instaloader.Profile.from_username(loader.context, "instagram")
        return True
    except Exception as e:
        print(f"Instagram session validation error: {e}")
        return False

# Helper function to get Instagram reel URL using Instaloader
def get_instagram_reel_url(url, session_id):
    """Fetch the direct video URL for Instagram Reels using Instaloader."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        shortcode = url.split('/')[-2]  # Extract shortcode from URL
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        if not post.is_video:
            raise RuntimeError("The provided URL does not point to a video reel.")

        return post.video_url
    except Exception as e:
        raise RuntimeError(f"Error fetching Instagram reel: {e}")

# Helper function to get YouTube video URL using yt-dlp
def get_youtube_video_url(url):
    """Fetch the direct video URL for YouTube using yt-dlp."""
    try:
        cookies = get_session_cookies()  # Fetch session cookies (if any)

        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'cookies': cookies  # Add the cookies to the yt-dlp options
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

# API endpoint to get the Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    session_id = get_session_cookies()  # Fetch session ID from environment

    if not url or not session_id:
        return handle_error('URL and session_id parameters are required')

    if not is_instagram_session_valid(session_id):
        return handle_error('Invalid or expired session ID. Please provide a valid session ID.', 401)

    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# API endpoint to get the YouTube video URL
@app.route('/get_youtube_video_url', methods=['GET'])
def youtube_video_url_api():
    """API endpoint to get the YouTube video URL."""
    url = request.args.get('url')

    if not url:
        return handle_error('URL parameter is required')

    try:
        video_url = get_youtube_video_url(url)
        return jsonify({'video_url': video_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Render needs to listen on 0.0.0.0 for the correct IP binding
