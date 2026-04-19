"""TeraCast API - Direct TeraBox Integration (No Cloudflare)."""
from flask import Flask, request, jsonify
from datetime import datetime, timezone
import logging
import time

from config import load_cookies
from utils import is_valid_share_url
from terabox_direct import fetch_terabox_files
from rate_limiter import rate_limit
import cache


def format_response_time(seconds: float) -> str:
    if seconds >= 60:
        return f"{round(seconds / 60, 2)}m"
    return f"{round(seconds, 3)}s"


def create_app() -> Flask:
    app = Flask(__name__)
    return app


app = create_app()


@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


@app.route("/")
def index():
    return jsonify({
        "name": "TeraCast API",
        "version": "1.0.0",
        "status": "operational",
        "description": "Professional TeraBox Video Streaming & Downloader API",
        "endpoints": {
            "/": "API information",
            "/api": "File listing",
            "/api2": "Direct download links",
            "/health": "Health check",
            "/help": "Documentation"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/api", methods=["GET"])
@rate_limit
def api():
    """File listing endpoint."""
    try:
        start_time = time.time()
        url = request.args.get("url")
        
        if not url:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: url"
            }), 400
        
        if not is_valid_share_url(url):
            return jsonify({
                "status": "error",
                "message": "Invalid TeraBox share URL"
            }), 400
        
        password = request.args.get("pwd", "")
        logging.info(f"API request: {url}")
        
        # Check cache
        cached = cache.get(url, password)
        if cached:
            return jsonify({
                "status": "success",
                "url": url,
                "files": cached.get("list", []),
                "total_files": len(cached.get("list", [])),
                "response_time": format_response_time(time.time() - start_time),
                "cached": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Fetch from TeraBox directly
        link_data = fetch_terabox_files(url, password)
        
        # Handle errors
        if isinstance(link_data, dict) and "error" in link_
            return jsonify({
                "status": "error",
                "url": url,
                "error": link_data["error"],
                "message": link_data.get("message", "")
            }), 500
        
        # Success
        if link_data and "list" in link_
            cache.put(url, link_data, password)
            
            return jsonify({
                "status": "success",
                "url": url,
                "files": link_data.get("list", []),
                "total_files": len(link_data.get("list", [])),
                "response_time": format_response_time(time.time() - start_time),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return jsonify({
            "status": "error",
            "message": "No files found"
        }), 404
        
    except Exception as e:
        logging.error(f"API error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api2", methods=["GET"])
@rate_limit
def api2():
    """Direct download links endpoint."""
    try:
        start_time = time.time()
        url = request.args.get("url")
        
        if not url:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: url"
            }), 400
        
        if not is_valid_share_url(url):
            return jsonify({
                "status": "error",
                "message": "Invalid TeraBox share URL"
            }), 400
        
        password = request.args.get("pwd", "")
        logging.info(f"API2 request: {url}")
        
        # Fetch from TeraBox directly
        link_data = fetch_terabox_files(url, password)
        
        # Handle errors
        if isinstance(link_data, dict) and "error" in link_
            return jsonify({
                "status": "error",
                "url": url,
                "error": link_data["error"]
            }), 500
        
        # Success - format with direct_link
        if link_data and "list" in link_
            files = []
            for item in link_data["list"]:
                file_info = {
                    "file_name": item.get("server_filename", item.get("file_name", "Unknown")),
                    "size": item.get("size", 0),
                    "size_readable": format_file_size(item.get("size", 0)),
                    "fs_id": item.get("fs_id"),
                    "path": item.get("path"),
                }
                if "download_link" in item:
                    file_info["direct_link"] = item["download_link"]
                if "thumbs" in item and item["thumbs"]:
                    file_info["thumbnail"] = item["thumbs"].get("url3")
                files.append(file_info)
            
            return jsonify({
                "status": "success",
                "url": url,
                "files": files,
                "total_files": len(files),
                "response_time": format_response_time(time.time() - start_time),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return jsonify({
            "status": "error",
            "message": "No files found"
        }), 404
        
    except Exception as e:
        logging.error(f"API2 error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"


@app.route("/help")
def help_page():
    return jsonify({
        "TeraCast API Documentation": {
            "version": "1.0.0",
            "endpoints": {
                "GET /": "API information",
                "GET /health": "Health check",
                "GET /api": "File listing (url, pwd)",
                "GET /api2": "Direct download links (url, pwd)"
            }
        }
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
