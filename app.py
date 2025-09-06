from flask import Flask, request, jsonify, send_file, send_from_directory, after_this_request
import yt_dlp
import uuid
import os

app = Flask(__name__)

# Serve frontend
@app.route("/")
def home():
    return send_from_directory(".", "index.html")  # index.html same folder [4]

@app.route("/main.js")
def serve_js():
    return send_from_directory(".", "main.js")     # main.js same folder [4]

# Get available formats (optional for UI)
@app.route("/formats", methods=["POST"])
def formats():
    try:
        url = (request.json or {}).get("url")
        if not url:
            return jsonify({"error": "URL required"}), 400
        out = []
        with yt_dlp.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url, download=False)  # metadata only [4]
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
        return jsonify({"formats": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Universal download route – robust audio+video merge
@app.route("/download", methods=["POST"])
def download():
    try:
        data = request.json or {}
        url = data.get("url")
        format_id = data.get("format_id")          # optional; if not sent, we auto-select
        audio_as_mp3 = bool(data.get("audio_as_mp3", False))

        if not url:
            return jsonify({"error": "URL required"}), 400

        # Output filename
        ext = "mp3" if audio_as_mp3 else "mp4"
        out_name = f"{uuid.uuid4()}.{ext}"

        # Build robust format selection
        # Goal: Always return file with audio, prefer H.264 (avc1) + AAC (mp4a), MP4 container
        use_selector = False
        fmt_expr = None

        if audio_as_mp3:
            # Prefer AAC audio stream, else bestaudio; then extract to MP3
            fmt_expr = "ba[acodec^=mp4a]/bestaudio"  # reliable audio capture [6]
            use_selector = True
        else:
            if format_id and '+' in format_id:
                ydl_fmt = format_id  # e.g., "137+251" – respect exact combo [4]
            elif format_id:
                # Try selected video id with bestaudio; if not available, fallback handled below
                ydl_fmt = f"{format_id}+bestaudio/b"  # graceful fallback [6]
            else:
                use_selector = True

        if use_selector:
            # Prefer 480p+ H.264 video + AAC audio -> progressive MP4 -> generic bv+ba -> best
            fmt_expr = fmt_expr or (
                "bv*[height>=480][vcodec^=avc1]+ba[acodec^=mp4a]/"
                "b[ext=mp4]/"
                "bv*+ba/b"
            )  # avoids silent video and maximizes device compatibility [6][4]

        ydl_opts = {
            "format": fmt_expr if use_selector else ydl_fmt,
            "merge_output_format": "mp4",  # final container [4]
            "outtmpl": out_name,
            "noprogress": False,
            "quiet": False,
        }

        if audio_as_mp3:
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
            ]  # extract to MP3 after grabbing AAC/bestaudio [4]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])  # download + merge via ffmpeg [4]

        if not os.path.exists(out_name):
            return jsonify({"error": "Download failed"}), 500

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(out_name):
                    os.remove(out_name)
            except Exception:
                pass
            return response

        return send_file(out_name, as_attachment=True)
    except Exception as e:
        # Return readable error to UI
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)





















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