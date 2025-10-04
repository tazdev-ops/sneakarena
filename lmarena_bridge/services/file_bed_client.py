"""
File bed client for uploading images and files to external storage.
This allows large files to be uploaded to a separate service before
being referenced in LMArena requests.
"""

import logging
import httpx
from typing import Optional, Dict, Any, Union
from pathlib import Path
import base64

logger = logging.getLogger(__name__)


class FileBedClient:
    """Client for interacting with an external file bed service."""
    
    def __init__(self, upload_url: str, api_key: Optional[str] = None):
        self.upload_url = upload_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Add authorization header if API key is provided
        if self.api_key:
            self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def upload_file(self, file_path: Union[str, Path], filename: Optional[str] = None) -> Optional[str]:
        """Upload a file and return the URL of the uploaded file."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return None
            
            if filename is None:
                filename = file_path.name
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create multipart form data
            files = {"file": (filename, file_content, "application/octet-stream")}
            
            response = await self.client.post(
                self.upload_url,
                files=files
            )
            
            if response.status_code == 200:
                # Assuming the response contains the uploaded file URL
                result = response.json()
                if isinstance(result, str):
                    # If response is directly the URL
                    return result
                elif isinstance(result, dict) and "url" in result:
                    # If response has a "url" field
                    return result["url"]
                elif isinstance(result, dict) and "file_url" in result:
                    # If response has a "file_url" field
                    return result["file_url"]
                else:
                    logger.error(f"Unexpected response format: {result}")
                    return None
            else:
                logger.error(f"File upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None
    
    async def upload_base64_image(self, base64_image: str, filename: str = "image.png") -> Optional[str]:
        """Upload a base64-encoded image and return the URL."""
        try:
            # Decode the base64 string
            image_data = base64.b64decode(base64_image)
            
            # Create multipart form data
            files = {"file": (filename, image_data, "image/png")}
            
            response = await self.client.post(
                self.upload_url,
                files=files
            )
            
            if response.status_code == 200:
                # Assuming the response contains the uploaded file URL
                result = response.json()
                if isinstance(result, str):
                    # If response is directly the URL
                    return result
                elif isinstance(result, dict) and "url" in result:
                    # If response has a "url" field
                    return result["url"]
                elif isinstance(result, dict) and "file_url" in result:
                    # If response has a "file_url" field
                    return result["file_url"]
                else:
                    logger.error(f"Unexpected response format: {result}")
                    return None
            else:
                logger.error(f"Image upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading base64 image: {e}")
            return None
    
    async def upload_bytes(self, data: bytes, filename: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """Upload raw bytes and return the URL."""
        try:
            # Create multipart form data
            files = {"file": (filename, data, content_type)}
            
            response = await self.client.post(
                self.upload_url,
                files=files
            )
            
            if response.status_code == 200:
                # Assuming the response contains the uploaded file URL
                result = response.json()
                if isinstance(result, str):
                    # If response is directly the URL
                    return result
                elif isinstance(result, dict) and "url" in result:
                    # If response has a "url" field
                    return result["url"]
                elif isinstance(result, dict) and "file_url" in result:
                    # If response has a "file_url" field
                    return result["file_url"]
                else:
                    logger.error(f"Unexpected response format: {result}")
                    return None
            else:
                logger.error(f"Bytes upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading bytes: {e}")
            return None


# Global file bed client instance (will be initialized when needed)
file_bed_client: Optional[FileBedClient] = None


async def get_file_bed_client(upload_url: str, api_key: Optional[str] = None) -> FileBedClient:
    """Get or create the global file bed client instance."""
    global file_bed_client
    if file_bed_client is None:
        file_bed_client = FileBedClient(upload_url, api_key)
    return file_bed_client


async def close_file_bed_client():
    """Close the global file bed client."""
    global file_bed_client
    if file_bed_client:
        await file_bed_client.close()
        file_bed_client = None