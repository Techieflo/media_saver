from flask import Flask, jsonify, request
import yt_dlp

app = Flask(__name__)

# Helper function to get video URL with cookies for Instagram
def get_video_url(url):
    """Fetch the direct video URL using yt-dlp."""
    ydl_opts = {
        'format': 'best',  # Choose the best video quality
        'quiet': True,     # Suppress unnecessary output
        'cookiefile': 'cookies.txt',  # Use cookies to bypass login restrictions
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)  # Don't download, just extract info
            if 'entries' in result:
                return result['entries'][0]['url']  # Return the first video URL
            return result['url']  # Return the video URL
    except Exception as e:
        raise RuntimeError(f"Error: {str(e)}")

@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    """API endpoint to get the Instagram reel URL."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400
    try:
        reel_url = get_video_url(url)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
