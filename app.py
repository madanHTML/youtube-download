from flask import Flask, request, jsonify, send_from_directory, send_file
import yt_dlp, os, shutil, uuid

app = Flask(__name__)

# 1) Secret cookies (read-only) -> copy to /tmp so yt-dlp can touch file safely
SEC_COOKIE = os.getenv("COOKIE_FILE", "/etc/secrets/cookies.txt")
TMP_COOKIE = "/tmp/cookies.txt"

# 2) Fixed download dir
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 3) Use same UA as the browser used to export cookies (override via ENV if needed)
BROWSER_UA = os.getenv(
    "BROWSER_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

def prepare_cookiefile():
    try:
        if os.path.exists(SEC_COOKIE):
            shutil.copy(SEC_COOKIE, TMP_COOKIE)   # avoid Errno 30 (read-only)
            return TMP_COOKIE
    except Exception:
        pass
    return SEC_COOKIE if os.path.exists(SEC_COOKIE) else None

def build_ydl_opts(for_download=False):
    cookiefile = prepare_cookiefile()
    opts = {
        "cookiefile": cookiefile,          # None => no cookies
        "user_agent": BROWSER_UA,
        "quiet": False,
        "verbose": True,                   # check logs for: Using cookies from /tmp/cookies.txt
        "noprogress": True,
        # light throttling to reduce 429
        "sleep_interval_requests": 1,
        "max_sleep_interval_requests": 3,
    }
    if for_download:
        opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, "%(title)s [%(id)s].%(ext)s")
    return opts

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/main.js")
def js():
    return send_from_directory(".", "main.js")

# Quick diagnostics for cookies state
@app.route("/check-cookies")
def check_cookies():
    return jsonify({
        "sec_path": SEC_COOKIE,
        "sec_exists": os.path.exists(SEC_COOKIE),
        "tmp_path": TMP_COOKIE,
        "tmp_exists": os.path.exists(TMP_COOKIE)
    })

# Get available formats
@app.route("/formats", methods=["POST"])
def formats():
    url = (request.json or {}).get("url")
    if not url:
        return jsonify({"error": "URL required"}), 400
    try:
        with yt_dlp.YoutubeDL(build_ydl_opts(False)) as ydl:
            info = ydl.extract_info(url, download=False)
        out = []
        for f in info.get("formats", []):
            out.append({
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution"),
                "filesize": f.get("filesize")
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Download endpoint
@app.route("/download", methods=["POST"])
def download():
    data = request.json or {}
    url = data.get("url")
    format_id = data.get("format_id")
    audio_as_mp3 = data.get("audio_as_mp3", False)
    if not url or not format_id:
        return jsonify({"error": "URL and format_id required"}), 400

    saved = {"file": None}
    def hook(d):
        # Keep final path for response
        if d.get("status") == "finished":
            # Prefer _filename (final) if present
            info = d.get("info_dict") or {}
            saved["file"] = info.get("_filename") or d.get("filename")

    ydl_opts = build_ydl_opts(True)
    ydl_opts["progress_hooks"] = [hook]

    # video+audio auto merge
    if audio_as_mp3:
        ydl_opts["format"] = format_id
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3"
        }]
    else:
        ydl_opts["format"] = format_id if '+' in format_id else f"{format_id}+bestaudio"
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        path = saved["file"]
        if not path or not os.path.exists(path):
            return jsonify({"error": "Download failed"}), 500

        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

























#from flask import Flask, request, jsonify, send_file, send_from_directory, after_this_request
#import yt_dlp
#import uuid
#import os
#
#app = Flask(__name__)
#
## Serve frontend HTML
#@app.route("/")
#def home():
#    return send_from_directory(".", "index.html")
#
## Static route for main.js
#@app.route("/main.js")
#def serve_js():
#    return send_from_directory(".", "main.js")
#
## Get available formats for given URL
#@app.route("/formats", methods=["POST"])
#def formats():
#    try:
#        url = request.json.get("url")
#        if not url:
#            return jsonify({"error": "YouTube link jaruri hai."}), 400
#        format_list = []
#        with yt_dlp.YoutubeDL({}) as ydl:
#            info = ydl.extract_info(url, download=False)
#            formats = info.get("formats", [])
#            for f in formats:
#                format_list.append({
#                    "id": f.get("format_id"),
#                    "ext": f.get("ext"),
#                    "height": f.get("height"),
#                    "abr": f.get("abr"),
#                    "note": f.get("format_note", ""),
#                    "audio_only": f.get("acodec") != "none" and f.get("vcodec") == "none",
#                    "video_only": f.get("vcodec") != "none" and f.get("acodec") == "none"
#                })
#        return jsonify({"formats": format_list})
#    except Exception as e:
#        return jsonify({"error": str(e)}), 500
#
## Download route with automatic video+audio merge
#@app.route("/download", methods=["POST"])
#def download():
#    try:
#        data = request.json
#        url = data.get("url")
#        format_id = data.get("format_id")
#        audio_as_mp3 = data.get("audio_as_mp3", False)
#
#        if not url or not format_id:
#            return jsonify({"error": "YouTube link aur format id dono jaruri hain."}), 400
#
#        ext = "mp3" if audio_as_mp3 else "mp4"
#        out_name = f"{uuid.uuid4()}.{ext}"
#
#        # Merge logic: video+audio unless audio only or manual merge format already given
#        if not audio_as_mp3 and '+' not in format_id:
#            ydl_fmt = f"{format_id}+bestaudio"
#        else:
#            ydl_fmt = format_id
#
#        ydl_opts = {
#            "format": ydl_fmt,
#            "outtmpl": out_name,
#            "merge_output_format": "mp4"
#        }
#
#        if audio_as_mp3:
#            ydl_opts["postprocessors"] = [{
#                "key": "FFmpegExtractAudio",
#                "preferredcodec": "mp3"
#            }]
#
#        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#            ydl.download([url])
#
#        if not os.path.exists(out_name):
#            return jsonify({"error": "Download fail hua."}), 500
#
#        @after_this_request
#        def cleanup(response):
#            try:
#                os.remove(out_name)
#            except Exception:
#                pass
#            return response
#
#        return send_file(out_name, as_attachment=True)
#    except Exception as e:
#        return jsonify({"error": str(e)}), 500
#
#@app.errorhandler(404)
#def not_found(e):
#    return jsonify({"error": "Not found"}), 404
#
#@app.errorhandler(405)
#def method_not_allowed(e):
#    return jsonify({"error": "Method not allowed"}), 405
#
#if __name__ == "__main__":
#    app.run(debug=True)
#


#
#from flask import Flask, request, jsonify, send_file, send_from_directory
#import yt_dlp
#import uuid
#import os
#
#app = Flask(__name__)
#
## Homepage/HTML route
#@app.route("/")
#def home():
#    return send_from_directory(".", "index.html")  # HTML file yahin ho
#
#    # YAHAN ADD KARO 👇
#@app.route("/main.js")
#def serve_js():
#    return send_from_directory(".", "main.js")
#
## Dynamic format list route
#@app.route("/formats", methods=["POST"])
#def formats():
#    try:
#        url = request.json.get("url")
#        if not url:
#            return jsonify({"error": "YouTube link jaruri hai."}), 400
#        format_list = []
#        with yt_dlp.YoutubeDL({}) as ydl:
#            info = ydl.extract_info(url, download=False)
#            formats = info.get("formats", [])
#            for f in formats:
#                format_list.append({
#                    "id": f.get("format_id"),
#                    "ext": f.get("ext"),
#                    "height": f.get("height"),
#                    "abr": f.get("abr"),
#                    "note": f.get("format_note", ""),
#                    "audio_only": f.get("acodec") != "none" and f.get("vcodec") == "none",
#                    "video_only": f.get("vcodec") != "none" and f.get("acodec") == "none"
#                })
#        return jsonify({"formats": format_list})
#    except Exception as e:
#        return jsonify({"error": str(e)}), 500
#
## Universal download route with auto merge logic
#@app.route("/download", methods=["POST"])
#def download():
#    try:
#        data = request.json
#        url = data.get("url")
#        format_id = data.get("format_id")
#        audio_as_mp3 = data.get("audio_as_mp3", False)
#
#        if not url or not format_id:
#            return jsonify({"error": "YouTube link aur format id dono jaruri hain."}), 400
#
#        ext = "mp3" if audio_as_mp3 else "mp4"
#        out_name = f"{uuid.uuid4()}.{ext}"
#
#              # ⭐️ 
#
#        # Most universal video+audio merge logic
#        if not audio_as_mp3 and '+' not in format_id:
#            ydl_fmt = f"{format_id}+bestaudio"
#        else:
#            ydl_fmt = format_id
#
#        ydl_opts = {
#            "format": ydl_fmt,
#            "outtmpl": out_name,
#            "merge_output_format": "mp4"
#        }
#        if audio_as_mp3:
#            ydl_opts["postprocessors"] = [{
#                "key": "FFmpegExtractAudio",
#                "preferredcodec": "mp3"
#            }]
#
#        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#            ydl.download([url])
#
#        if not os.path.exists(out_name):
#            return jsonify({"error": "Download fail hua."}), 500
#
#        return send_file(out_name, as_attachment=True)
#    except Exception as e:
#        return jsonify({"error": str(e)}), 500
#    finally:
#        try:
#            if 'out_name' in locals() and os.path.exists(out_name):
#                os.remove(out_name)
#        except Exception:
#            pass
#
## Global error handler
#@app.errorhandler(404)
#def not_found(e):
#    return jsonify({"error": "Not found"}), 404
#
#@app.errorhandler(405)
#def method_not_allowed(e):
#    return jsonify({"error": "Method not allowed"}), 405
#
#if __name__ == "__main__":
#    app.run(debug=True)

#







