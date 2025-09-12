from flask import Flask, request, jsonify, send_file, send_from_directory, after_this_request, Response
import yt_dlp
import uuid
import os
import shutil
from datetime import datetime

app = Flask(__name__)

# -------------------------
# 🔧 Config
# -------------------------
SEC_COOKIE = os.getenv("COOKIE_FILE", "/etc/secrets/cookies.txt")
TMP_COOKIE = "/tmp/cookies.txt"
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

BROWSER_UA = os.getenv(
    "BROWSER_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# -------------------------
# 🔧 Helpers
# -------------------------
def prepare_cookiefile():
    try:
        if os.path.exists(SEC_COOKIE):
            shutil.copy(SEC_COOKIE, TMP_COOKIE)
            return TMP_COOKIE
    except Exception:
        pass
    return SEC_COOKIE if os.path.exists(SEC_COOKIE) else None

progress = {}
cookie_file = "cookies.txt"

# -------------------------
# Serve frontend
# -------------------------
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/main.js")
def serve_js():
    return send_from_directory(".", "main.js")

# -------------------------
# 🔍 Check cookies
# -------------------------
@app.route("/check-cookies")
def check_cookies():
    return jsonify({
        "sec_path": SEC_COOKIE,
        "sec_exists": os.path.exists(SEC_COOKIE),
        "tmp_path": TMP_COOKIE,
        "tmp_exists": os.path.exists(TMP_COOKIE)
    })

# ✅ Robots.txt serve
@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nAllow: /\nSitemap: https://dolodear-1.onrender.com/sitemap.xml",
        mimetype="text/plain"
    )

# ✅ Sitemap.xml dynamic
@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": "https://dolodear-1.onrender.com/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "https://dolodear-1.onrender.com/formats", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "https://dolodear-1.onrender.com/download", "priority": "0.8", "changefreq": "weekly"},
    ]

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in pages:
        xml.append("<url>")
        xml.append(f"<loc>{page['loc']}</loc>")
        xml.append(f"<lastmod>{datetime.utcnow().date()}</lastmod>")
        xml.append(f"<changefreq>{page['changefreq']}</changefreq>")
        xml.append(f"<priority>{page['priority']}</priority>")
        xml.append("</url>")
        
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")

# ===============================
# 🎥 Get available formats + metadata
# ===============================
@app.route("/formats", methods=["POST"])
def formats():
    try:
        url = (request.json or {}).get("url")
        if not url:
            return jsonify({"error": "URL required"}), 400

        ydl_opts = {
            "cookiefile": cookie_file if os.path.exists(cookie_file) else None,
            "quiet": True,
            "noprogress": True
        }

        out = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # ✅ extra metadata
            metadata = {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "view_count": info.get("view_count"),
            }

            for f in info.get("formats", []):
                out.append({
                    "id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "height": f.get("height"),
                    "abr": f.get("abr"),
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                    "note": f.get("format_note", ""),
                    "audio_only": f.get("acodec") != "none" and f.get("vcodec") == "none",
                    "video_only": f.get("vcodec") != "none" and f.get("acodec") == "none",
                })
        return jsonify({"metadata": metadata, "formats": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===============================
# ⬇️ Download endpoint (video/audio)
# ===============================
@app.route("/download", methods=["POST"])
def download():
    try:
        data = request.json or {}
        url = data.get("url")
        format_id = data.get("format_id")
        audio_as_mp3 = bool(data.get("audio_as_mp3", False))

        if not url:
            return jsonify({"error": "URL required"}), 400

        ext = "mp3" if audio_as_mp3 else "mp4"
        out_name = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.{ext}")

        def my_hook(d):
            progress["status"] = d

        # Format expression
        if audio_as_mp3:
            fmt_expr = "ba[acodec^=mp4a]/bestaudio"
        else:
            fmt_expr = format_id or "bv*[height>=480][vcodec^=avc1]+ba/best"

        ydl_opts = {
            "format": fmt_expr,
            "merge_output_format": "mp4" if not audio_as_mp3 else None,
            "outtmpl": out_name,
            "noprogress": False,
            "quiet": True,
            "progress_hooks": [my_hook],
            "cookiefile": cookie_file if os.path.exists(cookie_file) else None,

            # ✅ Faster download options
            "concurrent_fragment_downloads": 5,
            "http_chunk_size": 5 * 1024 * 1024,
            "retries": 3,
        }

        if audio_as_mp3:
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
            ]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not os.path.exists(out_name):
            return jsonify({"error": "Download failed"}), 500

        # ✅ Send file with proper name
        filename = f"{info.get('title')}.{ext}"

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(out_name):
                    os.remove(out_name)
            except Exception:
                pass
            return response

        return send_file(out_name, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===============================
# 📊 Progress endpoint
# ===============================
@app.route("/progress", methods=["GET"])
def get_progress():
    return jsonify(progress)

# ===============================
# 🚀 Run
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)





















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


























