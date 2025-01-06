from flask import Flask, request, jsonify
    import yt_dlp

    app = Flask(__name__)

    def get_video_url(video_url):
        ydl_opts = {
            'quiet': True,
            'format': 'best',
            'extractor-retries': 3,
            'noplaylist': True,
            'geturl': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                result = ydl.extract_info(video_url, download=False)
                if 'url' in result:
                    return result['url']
                else:
                    return None
            except yt_dlp.utils.DownloadError as e:
                print(f"An error occurred: {e}")
                return None

    @app.route('/get_download_link', methods=['GET'])
    def get_download_link():
        video_url = request.args.get('video_url')

        if not video_url:
            return jsonify({'error': 'video_url parameter is required'}), 400

        download_link = get_video_url(video_url)

        if download_link:
            return jsonify({'download_link': download_link})
        else:
            return jsonify({'error': 'Failed to get download link'}), 500

    if __name__ == '__main__':
        app.run(debug=True)
