from flask import Flask, jsonify, request
import instaloader

# Initialize Flask app
app = Flask(__name__)

# Helper function to get Instagram video URL
def get_instagram_video_url(url, session_id=None):
    """
    Fetch the direct video URL for Instagram posts using Instaloader.
    Handles private posts if a valid session ID is provided.
    """
    try:
        # Initialize Instaloader instance
        loader = instaloader.Instaloader()

        # If session ID is provided, authenticate
        if session_id:
            loader.context._session.cookies.set('sessionid', session_id)

        # Extract shortcode from URL
        shortcode = url.split('/')[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Ensure the post is a video
        if not post.is_video:
            raise RuntimeError("The provided URL does not point to a video post.")

        # Return the direct video URL
        return post.video_url
    except Exception as e:
        raise RuntimeError(f"Error: {e}")

# Helper function to handle errors
def handle_error(message, status_code=400):
    """Return a structured error response."""
    return jsonify({'error': message}), status_code

# API endpoint for Instagram video URL
@app.route('/get_instagram_video_url', methods=['GET'])
def instagram_video_url_api():
    """
    API endpoint to get the Instagram video URL from the provided post URL.
    Handles private posts if a valid session ID is provided.
    """
    url = request.args.get('url')
    session_id = request.args.get('session_id')  # Optional session ID for private posts

    if not url:
        return handle_error('URL parameter is required.')

    try:
        video_url = get_instagram_video_url(url, session_id)
        return jsonify({'video_url': video_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Render or localhost setup
