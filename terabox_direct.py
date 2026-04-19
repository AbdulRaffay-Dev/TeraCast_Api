"""Direct TeraBox API Client - No Cloudflare Worker needed."""
import requests
import re
import logging
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)

class TeraBoxDirect:
    """Direct TeraBox API client."""
    
    def __init__(self, ndus_cookie: str):
        self.ndus = ndus_cookie
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.session.cookies.set('ndus', ndus_cookie, domain='.1024terabox.com')
    
    def extract_js_token(self, html: str) -> Optional[str]:
        """Extract jsToken from HTML."""
        patterns = [
            r'jsToken\s*:\s*["\']([^"\']+)["\']',
            r'jsToken:["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        
        return None
    
    def get_share_info(self, share_url: str, password: str = "") -> Dict:
        """
        Get file information from TeraBox share link.
        
        Args:
            share_url: TeraBox share URL
            password: Optional password
            
        Returns:
            Dict with file information
        """
        try:
            # Extract surl from URL
            surl = share_url.split('/s/')[-1].split('?')[0].split('/')[0]
            
            # Step 1: Fetch share page
            share_page_url = f'https://www.1024terabox.com/s/{surl}'
            response = self.session.get(share_page_url, timeout=30)
            
            if response.status_code != 200:
                return {
                    'error': f'Failed to fetch share page: {response.status_code}',
                    'status_code': response.status_code
                }
            
            html = response.text
            
            # Step 2: Extract jsToken
            js_token = self.extract_js_token(html)
            
            if not js_token:
                logging.error("jsToken not found in page")
                return {
                    'error': 'jsToken not found. Cookie may be invalid.',
                    'hint': 'Check if your ndus cookie is valid'
                }
            
            logging.info(f"Extracted jsToken: {js_token[:20]}...")
            
            # Step 3: Call share API
            api_url = 'https://www.1024terabox.com/api/shorturlinfo'
            params = {
                'jsToken': js_token,
                'shorturl': surl,
                'root': '1',
            }
            
            if password:
                params['pwd'] = password
            
            api_response = self.session.get(api_url, params=params, timeout=30)
            
            if api_response.status_code != 200:
                return {
                    'error': f'API request failed: {api_response.status_code}',
                    'status_code': api_response.status_code
                }
            
            data = api_response.json()
            
            # Add direct_link field if download_link exists
            if 'list' in data:
                for item in data['list']:
                    if 'download_link' in item:
                        item['direct_link'] = item['download_link']
            
            return data
            
        except requests.RequestException as e:
            logging.error(f"Request error: {e}")
            return {
                'error': f'Network error: {str(e)}',
                'status_code': 0
            }
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return {
                'error': f'Error: {str(e)}',
                'status_code': 0
            }


# Convenience function
def fetch_terabox_files(share_url: str, password: str = "", ndus: str = "") -> Dict:
    """
    Fetch files from TeraBox share link.
    
    Args:
        share_url: TeraBox share URL
        password: Optional password
        ndus: TeraBox ndus cookie (optional, will use from config if not provided)
        
    Returns:
        Dict with file information
    """
    if not ndus:
        from config import load_cookies
        cookies = load_cookies()
        ndus = cookies.get('ndus', '')
    
    if not ndus:
        return {
            'error': 'No ndus cookie provided',
            'hint': 'Set COOKIE_JSON in .env file'
        }
    
    client = TeraBoxDirect(ndus)
    return client.get_share_info(share_url, password)
