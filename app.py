from flask import Flask, jsonify, request
import instaloader

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

# Helper function to handle errors
def handle_error(message, status_code=400):
    """Return a structured error response."""
    return jsonify({'error': message}), status_code

# API endpoint to get the Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    session_id = request.args.get('session_id')

    if not url or not session_id:
        return handle_error('URL and session_id parameters are required')

    # Validate session ID before proceeding
    if not is_session_valid(session_id):
        return handle_error('Invalid or expired session ID. Please provide a valid session ID.', 401)

    try:
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Render needs to listen on 0.0.0.0 for the correct IP binding
