import subprocess
import os
import json

# Function to get best video and audio URLs using cookies
def get_best_video_and_audio(clean_url):
    """Fetch the best video and audio streams using yt-dlp with cookies."""
    try:
        cookies = os.getenv("YT_COOKIES")
        has_cookies = bool(cookies)  # Check if cookies exist

        # Base command for yt-dlp
        command = ["yt-dlp", "--no-warnings", "-j", clean_url]

        # Only add cookies if they exist
        cookies_file = None
        if has_cookies:
            cookies_file = "/tmp/yt_cookies.txt"
            with open(cookies_file, "w") as f:
                f.write(cookies)
            command.extend(["--cookies", cookies_file])

        # Log the command being run for debugging
        print(f"Running yt-dlp with command: {command}")

        # Run yt-dlp
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        # Log the raw yt-dlp output for debugging
        print("yt-dlp stdout:", result.stdout)
        print("yt-dlp stderr:", result.stderr)

        # Check if yt-dlp returned any output
        if not result.stdout:
            return {"error": "yt-dlp did not return any output. Check the URL and try again.", "cookies_used": has_cookies}

        try:
            video_info = json.loads(result.stdout)
            print(f"yt-dlp JSON output: {video_info}")
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse yt-dlp response: {e}. Raw output: {result.stdout}", "cookies_used": has_cookies}

        if not isinstance(video_info, dict) or "formats" not in video_info:
            return {"error": f"Unexpected yt-dlp response format. Raw output: {result.stdout}", "cookies_used": has_cookies}

        available_formats = video_info.get("formats", [])
        best_video, best_audio = None, None

        for fmt in available_formats:
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                if not best_video or fmt["height"] > best_video["height"]:
                    best_video = fmt
            elif fmt.get("acodec") != "none":
                if not best_audio or fmt["abr"] > best_audio["abr"]:
                    best_audio = fmt

        response = {
            "message": "Successfully retrieved video and audio URLs",
            "available_formats": available_formats,
            "cookies_used": has_cookies
        }

        if best_video and best_audio:
            response["best_video_url"] = best_video["url"]
            response["best_audio_url"] = best_audio["url"]

        if not best_video or not best_audio:
            response["error"] = "No suitable video or audio streams found."

        return response

    except subprocess.CalledProcessError as e:
        # Enhanced error handling for yt-dlp failure
        print(f"yt-dlp subprocess error: {e}")
        return {"error": f"yt-dlp failed: {e.stderr}", "cookies_used": bool(os.getenv("YT_COOKIES"))}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": f"Unexpected error: {e}", "cookies_used": bool(os.getenv("YT_COOKIES"))}
