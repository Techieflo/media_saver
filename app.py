from flask import Flask, jsonify, request
import instaloader

# Initialize Flask app
app = Flask(__name__)

# Helper function to get Instagram reel or video URL using Instaloader
def get_instagram_video_url(url):
    """Fetch the direct video URL for Instagram Reels or Videos using Instaloader."""
    try:
        # Initialize Instaloader
        loader = instaloader.Instaloader()
        
        # Extract shortcode from the Instagram URL
        shortcode = url.split('/')[-2]
        
        # Fetch the post using the shortcode
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        
        # Ensure the post contains a video
        if not post.is_video:
            raise RuntimeError("The provided URL does not point to a video or reel.")
        
        # Return the URL of the video
        return post.video_url
    except Exception as e:
        raise RuntimeError(f"Error: {e}")

# Helper function to handle errors
def handle_error(message, status_code=400):
    """Return a structured error response."""
    return jsonify({'error': message}), status_code

# Define the API endpoint for Instagram video/reel URL
@app.route('/get_instagram_video_url', methods=['GET'])
def instagram_video_url_api():
    """API endpoint to get the Instagram video or reel URL."""
    url = request.args.get('url')  # The Instagram post URL
    
    if not url:
        return handle_error('URL parameter is required')
    
    try:
        video_url = get_instagram_video_url(url)
        return jsonify({'video_url': video_url})
    except Exception as e:
        return handle_error(f'Error: {str(e)}', 500)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Exposes the app for external access
