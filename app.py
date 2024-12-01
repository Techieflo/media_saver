from flask import Flask, jsonify, request
import yt_dlp

# Initialize Flask app
app = Flask(__name__)

# Helper function to get Instagram Reel URL using yt-dlp
def get_instagram_reel_url(url):
    """
    Fetch the direct video URL for Instagram Reels using yt-dlp with cookies for authentication.
    """
    ydl_opts = {
        'format': 'best',            # Choose the best video quality
        'quiet': True,               # Suppress unnecessary output
        'cookies': 'cookies.txt',    # Path to the cookies file for authentication
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video information without downloading
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                return result['entries'][0]['url']  # Return the first video URL
            return result['url']  # Return the video URL
    except Exception as e:
        raise RuntimeError(f"Error: {e}")

# Helper function to handle errors
def handle_error(message, status_code=400):
    """
    Return a structured error response.
    """
    return jsonify({'error': message}), status_code

# Define the API endpoint for Instagram reel URL
@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """
    API endpoint to get the Instagram reel URL.
    """
    url = request.args.get('url')  # Extract the URL parameter from the request

    if not url:
        return handle_error('URL parameter is required')  # Return an error if no URL is provided

    try:
        # Fetch the Instagram reel video URL
        reel_url = get_instagram_reel_url(url)
        return jsonify({'video_url': reel_url})  # Return the video URL as JSON
    except Exception as e:
        return handle_error(f"Error: {str(e)}", 500)  # Return an error if the operation fails

# Run the Flask app
if __name__ == '__main__':
    # The app listens on all interfaces and port 5000
    app.run(host='0.0.0.0', port=5000)
