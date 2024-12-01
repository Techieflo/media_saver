from flask import Flask, jsonify, request
import yt_dlp

# Initialize Flask app
app = Flask(__name__)

# Helper function to get video URL
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

# Helper function to handle errors
def handle_error(message, status_code=400):
    """Return a structured error response."""
    return jsonify({'error': message}), status_code

# Define the API endpoint
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

# Run the Flask app on Render (no need for debugging or other parameters)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Render needs to listen on 0.0.0.0 for the correct IP binding
