from flask import Flask, jsonify, request
import instaloader
import yt_dlp
import os

# Initialize Flask app
app = Flask(__name__)

# Helper function to check if the session ID is valid
def is_session_valid(session_id):
    """Check if the provided session ID is valid."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        # Test with a simple query to a public Instagram profile
        instaloader.Profile.from_username(loader.context, "instagram")
        return True
    except Exception as e:
        print(f"Session validation error: {e}")
        return False

# Helper function to get Instagram reel URL using Instaloader
def get_instagram_reel_url(url, session_id):
    """Fetch the direct video URL for Instagram Reels using Instaloader."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)

        shortcode = url.split('/')[-2]  # Extract shortcode from URL
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Ensure that the post is a video
        if not post.is_video:
            raise RuntimeError("The provided URL does not point to a video reel.")

        # Return the URL of the video
        return post.video_url
    except Exception as e:
        raise RuntimeError(f"Error: {e}")

# Helper function to get video URL from generic platforms (yt-dlp)
def get_video_url(url):
    """Fetch the direct video URL using yt-dlp."""
    ydl_opts = {
        'format': 'best',  # Choose the best video quality
        'quiet': True,     # Suppress unnecessary output
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)  # Don't download, just extract info
            if 'entries' in result:
                return result['entries'][0]['url']  # Return the first video URL
            return result['url']  # Return the video URL
    except Exception as e:
        raise RuntimeError(f"Error fetching video URL: {str(e)}")

# Helper function to handle errors
def handle_error(message, status_code=400):
    """Return a structured error response."""
    return jsonify({'error': message}), status_code

# API endpoint to get the Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')

    if not url:
        return handle_error('URL parameter is required')

    # Fetch the session ID from environment variables
    session_id = os.getenv('SESSION_ID')

    if not session_id:
        return handle_error('Session ID is not set. Please configure the session ID in the environment variables.', 500)

    # Validate session ID before proceeding
    if not is_session_valid(session_id):
        return handle_error('Invalid or expired session ID. Please provide a valid session ID.', 401)

    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# API endpoint to get the generic video URL (from YouTube or other sources)
@app.route('/get_video_url', methods=['GET'])
def video_url_api():
    """API endpoint to get the video URL from the provided URL (YouTube or other platforms)."""
    url = request.args.get('url')

    if not url:
        return handle_error('URL parameter is required')

    try:
        video_url = get_video_url(url)
        return jsonify({'video_url': video_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Render needs to listen on 0.0.0.0 for the correct IP binding
