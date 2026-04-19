"""TeraCast API - Main Flask Application."""
from flask import Flask, request, jsonify, Response
from datetime import datetime, timezone
import logging
import time
import aiohttp
import os

from config import (
    headers, load_cookies, PROXY_BASE_URL, 
    PROXY_MODE_RESOLVE, PROXY_MODE_PAGE, PROXY_MODE_API,
    PROXY_MODE_STREAM, PROXY_MODE_SEGMENT
)
from utils import is_valid_share_url
from terabox_client import (
    fetch_download_link, fetch_direct_links,
    _gather_format_file_info, _normalize_api2_items
)
from rate_limiter import rate_limit
import cache


def format_response_time(seconds: float) -> str:
    """Format response time with appropriate unit."""
    if seconds >= 60:
        return f"{round(seconds / 60, 2)}m"
    return f"{round(seconds, 3)}s"


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    return app


# Create app instance
app = create_app()


# CORS headers for browser access
@app.after_request
def add_cors_headers(resp: Response) -> Response:
    """Add CORS headers to all responses."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    return resp


# =============== API ROUTES ===============


@app.route("/")
def index():
    """API information endpoint."""
    return jsonify({
        "name": "TeraCast API",
        "version": "1.0.0",
        "status": "operational",
        "description": "Professional TeraBox Video Streaming & Downloader API",
        "endpoints": {
            "/": "API information",
            "/api": "File listing and proxy modes",
            "/api2": "Direct download links",
            "/health": "Health check",
            "/help": "Documentation"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/api", methods=["GET"])
@rate_limit
async def api():
    """
    Unified API endpoint - file listing and proxy modes.
    
    Query Parameters:
        - url: TeraBox share URL (for file listing)
        - mode: Proxy mode (resolve, page, api, stream, segment)
        - surl: Short URL ID (for proxy modes)
        - pwd: Password (optional, for protected links)
    """
    try:
        start_time = time.time()
        mode = request.args.get("mode")
        url = request.args.get("url")
        
        # ===== PROXY MODE =====
        if mode:
            cookies = load_cookies()
            params = {"mode": mode}
            
            # Add all query params except 'mode'
            for key, value in request.args.items():
                if key != "mode":
                    params[key] = value
            
            # Make proxy request
            async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
                async with session.get(PROXY_BASE_URL, params=params) as response:
                    content = await response.read()
                    content_type = response.headers.get("Content-Type", "application/json")
                    
                    return Response(
                        content,
                        status=response.status,
                        content_type=content_type
                    )
        
        # ===== FILE LISTING MODE =====
        if not url:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: url or mode",
                "examples": {
                    "file_listing": "/api?url=https://terabox.com/s/...",
                    "proxy_mode": "/api?mode=resolve&surl=abc123"
                }
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
            formatted_files = await _gather_format_file_info(cached)
            return jsonify({
                "status": "success",
                "url": url,
                "files": formatted_files,
                "total_files": len(formatted_files),
                "response_time": format_response_time(time.time() - start_time),
                "cached": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Fetch from TeraBox
        link_data = await fetch_download_link(url, password)
        
        # Handle errors
        if isinstance(link_data, dict) and "error" in link_data:
            status_code = 400 if link_data.get("requires_password") else 500
            return jsonify({
                "status": "error",
                "url": url,
                "error": link_data["error"],
                "errno": link_data.get("errno"),
                "message": link_data.get("message", "")
            }), status_code
        
        # Success
        if link_data:
            cache.put(url, link_data, password)
            formatted_files = await _gather_format_file_info(link_data)
            
            return jsonify({
                "status": "success",
                "url": url,
                "files": formatted_files,
                "total_files": len(formatted_files),
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
async def api2():
    """
    Alternative API endpoint with direct download links.
    
    Query Parameters:
        - url: TeraBox share URL (required)
        - pwd: Password (optional)
    """
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
        
        # Fetch direct links
        link_data = await fetch_direct_links(url, password)
        
        # Handle errors
        if isinstance(link_data, dict) and "error" in link_data:
            return jsonify({
                "status": "error",
                "url": url,
                "error": link_data["error"],
                "errno": link_data.get("errno")
            }), 500
        
        # Success
        if link_data:
            formatted_files = await _normalize_api2_items(link_data)
            
            return jsonify({
                "status": "success",
                "url": url,
                "files": formatted_files,
                "total_files": len(formatted_files),
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


@app.route("/help")
def help_page():
    """API documentation endpoint."""
    return jsonify({
        "TeraCast API Documentation": {
            "version": "1.0.0",
            "description": "Extract file information and direct download links from TeraBox",
            "endpoints": {
                "GET /": "API information",
                "GET /health": "Health check",
                "GET /api": {
                    "description": "File listing and proxy modes",
                    "parameters": {
                        "url": "TeraBox share URL (for file listing)",
                        "mode": "Proxy mode: resolve, page, api, stream, segment",
                        "surl": "Short URL ID (for proxy modes)",
                        "pwd": "Password for protected links (optional)"
                    },
                    "examples": [
                        "/api?url=https://terabox.com/s/abc123",
                        "/api?mode=resolve&surl=abc123"
                    ]
                },
                "GET /api2": {
                    "description": "Direct download links",
                    "parameters": {
                        "url": "TeraBox share URL (required)",
                        "pwd": "Password (optional)"
                    }
                }
            },
            "response_format": {
                "success": {
                    "status": "success",
                    "files": "Array of file objects",
                    "total_files": "Number of files"
                },
                "error": {
                    "status": "error",
                    "message": "Error description"
                }
            }
        }
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
