"""Utility functions for TeraCast API."""
from urllib.parse import urlparse
from typing import Optional
from config import ALLOWED_HOSTS


def is_valid_share_url(url: str) -> bool:
    """
    Validate TeraBox share URL format and domain.
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if valid TeraBox share URL
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        
        # Check scheme (http or https)
        if parsed.scheme not in ["http", "https"]:
            return False
        
        # Check if domain is allowed
        if parsed.hostname not in ALLOWED_HOSTS:
            return False
        
        # Check if path contains /s/ or /share/
        if "/s/" not in parsed.path and "/share/" not in parsed.path:
            return False
        
        return True
        
    except Exception:
        return False


def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Human readable size (e.g., "1.25 GB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


def extract_surl_from_url(share_url: str) -> Optional[str]:
    """
    Extract short URL ID from TeraBox share URL.
    
    Args:
        share_url: Full TeraBox share URL
        
    Returns:
        str or None: Short URL ID if found
    """
    try:
        # Extract everything after /s/
        parts = share_url.split("/s/")
        if len(parts) < 2:
            return None
        
        # Get the part after /s/ and remove query params
        surl = parts[1].split("?")[0].split("/")[0]
        return surl if surl else None
        
    except Exception:
        return None
