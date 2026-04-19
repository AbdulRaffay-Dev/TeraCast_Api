"""TeraBox API client with unified proxy integration."""
import aiohttp
from typing import Dict, List, Optional
from config import PROXY_BASE_URL, PROXY_MODE_RESOLVE, headers, load_cookies
from utils import format_file_size, extract_surl_from_url


async def fetch_download_link(share_url: str, password: str = "") -> Dict:
    """
    Fetch file information from TeraBox via proxy.
    
    Args:
        share_url: TeraBox share URL
        password: Optional password for protected links
        
    Returns:
        Dict containing file information or error
    """
    try:
        cookies = load_cookies()
        
        # Extract surl from share URL
        surl = extract_surl_from_url(share_url)
        if not surl:
            return {
                "error": "Invalid share URL format",
                "errno": -1,
                "message": "Could not extract short URL from share link"
            }
        
        # Build proxy request parameters
        params = {
            "mode": PROXY_MODE_RESOLVE,
            "surl": surl
        }
        if password:
            params["pwd"] = password
        
        # Make async request to proxy
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.get(PROXY_BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    return {
                        "error": f"Proxy error: {response.status}",
                        "errno": response.status,
                        "details": error_text[:500]
                    }
                    
    except aiohttp.ClientError as e:
        return {
            "error": f"Network error: {str(e)}",
            "errno": -2,
            "message": "Failed to connect to TeraBox"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "errno": -1
        }


async def fetch_direct_links(share_url: str, password: str = "") -> Dict:
    """
    Fetch files with direct download links.
    
    Args:
        share_url: TeraBox share URL
        password: Optional password
        
    Returns:
        Dict with files including direct_link field
    """
    try:
        link_data = await fetch_download_link(share_url, password)
        
        # If error occurred, return as-is
        if "error" in link_data:
            return link_data
        
        # Add direct_link field if download_link exists
        if "list" in link_data:
            for item in link_data["list"]:
                if "download_link" in item:
                    item["direct_link"] = item["download_link"]
        
        return link_data
        
    except Exception as e:
        return {
            "error": str(e),
            "errno": -1
        }


async def _gather_format_file_info(link_data: Dict) -> List[Dict]:
    """
    Format file information for API response.
    
    Args:
        link_data: Raw data from TeraBox API
        
    Returns:
        List of formatted file information
    """
    formatted = []
    
    if "list" not in link_data:
        return formatted
    
    for item in link_data["list"]:
        file_info = {
            "file_name": item.get("server_filename", item.get("file_name", "Unknown")),
            "size": item.get("size", 0),
            "size_readable": format_file_size(item.get("size", 0)),
            "fs_id": item.get("fs_id"),
            "path": item.get("path"),
            "isdir": item.get("isdir", 0),
            "category": item.get("category", 1),
        }
        
        # Add download link if available
        if "download_link" in item:
            file_info["direct_link"] = item["download_link"]
        
        # Add thumbnail if available
        if "thumbs" in item and item["thumbs"]:
            file_info["thumbnail"] = item["thumbs"].get("url3")
        
        # Add timestamps
        if "server_ctime" in item:
            file_info["created_time"] = item["server_ctime"]
        if "server_mtime" in item:
            file_info["modified_time"] = item["server_mtime"]
        
        formatted.append(file_info)
    
    return formatted


async def _normalize_api2_items(link_data: Dict) -> List[Dict]:
    """
    Normalize items for /api2 endpoint with direct links.
    
    Args:
        link_data: Raw data from TeraBox API
        
    Returns:
        List of normalized file information
    """
    return await _gather_format_file_info(link_data)
