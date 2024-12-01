from flask import Flask, jsonify, request
import yt_dlp
import instaloader

# Initialize Flask app
app = Flask(__name__)

# Helper function to get video URL from generic platforms (yt-dlp)
def get_video_url(url):
    """Fetch the direct video URL using yt-dlp."""
    ydl_opts = {
        'format': 'best',  # Choose the best video quality
        'quiet': True,     # Suppress unnecessary output
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)  # Don't download, just extract info
        if 'entries' in result:
            return result['entries'][0]['url']  # Return the first video URL
        return result['url']  # Return the video URL

# Helper function to get Instagram Reel URL using Instaloader
def get_instagram_reel_url(url, session_id):
    """Fetch the direct video URL for Instagram Reels using Instaloader."""
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)  # Use session ID for auth

        shortcode = url.split('/')[-2]  # Extract shortcode from URL
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Ensure that the post is a video
        if not post.is_video:
            raise RuntimeError("The provided URL does not point to a video reel.")

        # Return the URL of the video
        return post.url
    except Exception as e:
        raise RuntimeError(f"Error: {e}")

# Helper function to handle errors
def handle_error(message, status_code=400):
    """Return a structured error response."""
    return jsonify({'error': message}), status_code

# Define the API endpoint for generic video URL (yt-dlp)
@app.route('/get_video_url', methods=['GET'])
def video_url_api():
    """API endpoint to get the video URL from the provided URL."""
    url = request.args.get('url')

    if not url:
        return handle_error('URL parameter is required')

    try:
        video_url = get_video_url(url)
        return jsonify({'video_url': video_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Define the API endpoint for Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    session_id = request.args.get('session_id')

    if not url or not session_id:
        return handle_error('URL and session_id parameters are required')

    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Render needs to listen on 0.0.0.0 for the correct IP binding
