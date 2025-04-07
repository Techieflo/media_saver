from flask import Flask, request, jsonify
import os
import instaloader
from urllib.parse import urlparse, parse_qs
from threading import Semaphore
import yt_dlp

app = Flask(__name__)

# Limit concurrent requests
MAX_CONCURRENT_REQUESTS = 5
semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)

# Fetch Instagram session ID from env
def get_instagram_session_id():
    session_id = os.getenv('SESSION_ID')
    if not session_id:
        raise ValueError("Instagram session ID not found in environment variables.")
    return session_id

# Extract video URL from Instagram Reels
def get_instagram_reel_url(url, session_id):
    try:
        loader = instaloader.Instaloader()
        loader.context._session.cookies.set('sessionid', session_id)
        shortcode = url.split('/')[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        if not post.is_video:
            raise RuntimeError("URL does not point to a video reel.")
        return post.video_url
    except Exception as e:
        raise RuntimeError(f"Error fetching reel: {e}")

# Clean YouTube URL
def clean_youtube_url(url):
    parsed_url = urlparse(url)
    video_id = None

    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
        if not video_id and 'shorts' in parsed_url.path:
            video_id = parsed_url.path.split('/')[-1]
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')
    else:
        return None

    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None

# Get direct video download link using yt_dlp and cookies
def get_download_link(video_url):
    try:
        cookies = os.getenv("YT_COOKIES")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'quiet': True,
            'noplaylist': True,
        }

        if cookies:
            # Write cookies to temp file
            cookies_file = "/tmp/yt_cookies.txt"
            with open(cookies_file, "w") as f:
                f.write(cookies)
            ydl_opts["cookiefile"] = cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            download_url = info.get('url', None)

        # Clean up cookie file
        if cookies:
            os.remove(cookies_file)

        return {
            "download_url": download_url,
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "cookies_used": bool(cookies)
        }

    except Exception as e:
        raise RuntimeError(f"Failed to extract download URL: {e}")

# --- API ENDPOINTS ---

@app.route('/get_instagram_reel_url', methods=['GET'])
def instagram_reel_url_api():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required.'}), 400
    try:
        session_id = get_instagram_session_id()
        reel_url = get_instagram_reel_url(url, session_id)
        return jsonify({'video_url': reel_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_video_audio_urls', methods=['POST'])
def get_video_audio_urls_endpoint():
    if not semaphore.acquire(blocking=False):
        return jsonify({"error": "Server busy. Please try again later."}), 503

    try:
        data = request.json
        youtube_url = data.get('url')
        if not youtube_url:
            return jsonify({"error": "YouTube URL is required"}), 400

        clean_url = clean_youtube_url(youtube_url)
        if not clean_url:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        result = get_download_link(clean_url)
        if not result.get("download_url"):
            return jsonify({"error": "No downloadable URL found"}), 500

        return jsonify({
            "message": "Success",
            **result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        semaphore.release()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
