"""Configuration module for TeraCast API."""
import functools
import logging
import os
from typing import Dict, Set

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Allowed TeraBox domains
ALLOWED_HOSTS: Set[str] = {
    "terabox.app",
    "www.erabox.app",
    "teraboxshare.com",
    "www.teraboxshare.com",
    "terabox.com",
    "www.terabox.com",
    "1024terabox.com",
    "www.1024terabox.com",
    "teraboxlink.com",
    "terasharefile.com",
    "terafileshare.com",
    "terasharelink.com",
}

# Proxy configuration
PROXY_BASE_URL: str = "https://teracast-proxy.abdulraffaynajam.workers.dev/"
PROXY_MODE_RESOLVE: str = "resolve"
PROXY_MODE_PAGE: str = "page"
PROXY_MODE_API: str = "api"
PROXY_MODE_STREAM: str = "stream"
PROXY_MODE_SEGMENT: str = "segment"

# Default HTTP headers
headers: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


@functools.lru_cache(maxsize=1)
def load_cookies() -> Dict[str, str]:
    """Load cookies from environment variables."""
    data = None
    
    # Try COOKIE_JSON from .env file
    cookie_json = os.getenv("COOKIE_JSON")
    if cookie_json:
        try:
            import json
            # Try parsing as JSON first
            data = json.loads(cookie_json)
            logging.info("✅ Loaded cookies from COOKIE_JSON (JSON format)")
        except json.JSONDecodeError:
            # If not valid JSON, treat as simple ndus token
            cookie_json = cookie_json.strip()
            if cookie_json:
                data = {"ndus": cookie_json}
                logging.info("✅ Loaded cookies from COOKIE_JSON (simple format)")
        except Exception as e:
            logging.warning(f"❌ Failed to parse COOKIE_JSON: {e}")
    
    # Fallback to TERABOX_COOKIES_JSON
    if not data:
        raw = os.getenv("TERABOX_COOKIES_JSON")
        if raw:
            try:
                import json
                data = json.loads(raw)
                logging.info("✅ Loaded cookies from TERABOX_COOKIES_JSON")
            except Exception as e:
                logging.warning(f"❌ Failed to parse TERABOX_COOKIES_JSON: {e}")
    
    if isinstance(data, dict):
        return {k: str(v) for k, v in data.items()}

    logging.warning("⚠️ Cookies not loaded. API requests will fail.")
    return {}
