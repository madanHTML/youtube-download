from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from datetime import datetime
import yt_dlp, os

app = Flask(__name__)

# -------------------------
# 🔧 Config
# -------------------------
COOKIE_FILE = "cookies.txt"   # Root folder me rakhi hui cookies file
DOWNLOAD_DIR = "downloads"    # Downloaded files isme aayenge
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# -------------------------
# 🔧 Helpers
# -------------------------
def prepare_cookiefile():
    return COOKIE_FILE if os.path.exists(COOKIE_FILE) else None

def build_ydl_opts(for_download=False):
    cookiefile = prepare_cookiefile()
    opts = {
        "cookiefile": cookiefile,
        "user_agent": BROWSER_UA,
        "quiet": False,
        "verbose": True,
        "noprogress": True,
        "sleep_interval_requests": 1,
        "max_sleep_interval_requests": 3,
    }
    if for_download:
        opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, "%(title)s [%(id)s].%(ext)s")
    return opts

# -------------------------
# 🏠 Static files
# -------------------------
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/main.js")
def js():
    return send_from_directory(".", "main.js")

# -------------------------
# 🔍 Check cookies
# -------------------------
@app.route("/check-cookies.txt")
def check_cookies():
    return jsonify({
        "cookie_path": COOKIE_FILE,
        "exists": os.path.exists(COOKIE_FILE)
    })

# ✅ Robots.txt serve
@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nAllow: /\nSitemap: https://your-domain.com/sitemap.xml",
        mimetype="text/plain"
    )

# ✅ Sitemap.xml dynamic
@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": "https://your-domain.com/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "https://your-domain.com/formats", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "https://your-domain.com/download", "priority": "0.8", "changefreq": "weekly"},
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

# -------------------------
# ✅ Formats endpoint
# -------------------------
@app.route("/formats", methods=["POST"])
def formats():
    try:
        url = (request.json or {}).get("url")
        if not url:
            return jsonify({"error": "URL required"}), 400

        out = []
        with yt_dlp.YoutubeDL(build_ydl_opts(False)) as ydl:
            info = ydl.extract_info(url, download=False)

            for f in info.get("formats", []):
                out.append({
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "height": f.get("height"),
                    "abr": f.get("abr"),
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                    "note": f.get("format_note", ""),
                    "audio_only": f.get("acodec") != "none" and f.get("vcodec") == "none",
                    "video_only": f.get("vcodec") != "none" and f.get("acodec") == "none",
                })

        # Extra: Add MP3 virtual option
        audio_formats = [f for f in out if f["audio_only"]]
        if audio_formats:
            best_audio = max(audio_formats, key=lambda a: a.get("abr") or 0)
            out.append({
                "format_id": best_audio["format_id"],
                "ext": "mp3",
                "abr": best_audio.get("abr"),
                "vcodec": "none",
                "acodec": "mp3",
                "note": "Extracted MP3",
                "audio_only": True,
                "video_only": False
            })

        return jsonify({
            "formats": out,
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# ✅ Download endpoint
# -------------------------
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
        if d.get("status") == "finished":
            info = d.get("info_dict") or {}
            saved["file"] = info.get("_filename") or d.get("filename")

    ydl_opts = build_ydl_opts(True)
    ydl_opts["progress_hooks"] = [hook]

    if os.path.exists(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE

    if audio_as_mp3 or str(format_id).endswith(".mp3"):
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

# -------------------------
# 🚀 Run
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
