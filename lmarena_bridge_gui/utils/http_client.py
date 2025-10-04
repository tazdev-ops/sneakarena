"""
HTTP client utilities for the GTK4 GUI.
Handles communication with the backend API server from GUI threads.
"""

import threading
import logging
import json
from typing import Optional, Dict, Any, Callable
import httpx
from gi.repository import GLib

logger = logging.getLogger(__name__)


class GUILayerHTTPClient:
    """
    HTTP client for GUI layer communication with the backend API.
    Uses httpx for async requests but provides sync interface for GUI.
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:5102"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
    
    def get(self, endpoint: str, callback: Callable[[Optional[Dict[str, Any]], Optional[str]], None]) -> None:
        """
        Perform a GET request in a background thread and call the callback on the main thread.
        """
        def _background_task():
            try:
                response = self.client.get(endpoint)
                response.raise_for_status()
                data = response.json()
                
                # Call the callback on the main thread
                GLib.idle_add(callback, data, None)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"HTTP GET error for {endpoint}: {error_msg}")
                GLib.idle_add(callback, None, error_msg)
        
        thread = threading.Thread(target=_background_task, daemon=True)
        thread.start()
    
    def post(self, endpoint: str, data: Dict[str, Any], 
             callback: Callable[[Optional[Dict[str, Any]], Optional[str]], None]) -> None:
        """
        Perform a POST request in a background thread and call the callback on the main thread.
        """
        def _background_task():
            try:
                response = self.client.post(endpoint, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Call the callback on the main thread
                GLib.idle_add(callback, result, None)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"HTTP POST error for {endpoint}: {error_msg}")
                GLib.idle_add(callback, None, error_msg)
        
        thread = threading.Thread(target=_background_task, daemon=True)
        thread.start()
    
    def put(self, endpoint: str, data: Dict[str, Any], 
            callback: Callable[[Optional[Dict[str, Any]], Optional[str]], None]) -> None:
        """
        Perform a PUT request in a background thread and call the callback on the main thread.
        """
        def _background_task():
            try:
                response = self.client.put(endpoint, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Call the callback on the main thread
                GLib.idle_add(callback, result, None)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"HTTP PUT error for {endpoint}: {error_msg}")
                GLib.idle_add(callback, None, error_msg)
        
        thread = threading.Thread(target=_background_task, daemon=True)
        thread.start()
    
    def delete(self, endpoint: str, 
               callback: Callable[[Optional[Dict[str, Any]], Optional[str]], None]) -> None:
        """
        Perform a DELETE request in a background thread and call the callback on the main thread.
        """
        def _background_task():
            try:
                response = self.client.delete(endpoint)
                response.raise_for_status()
                result = response.json()
                
                # Call the callback on the main thread
                GLib.idle_add(callback, result, None)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"HTTP DELETE error for {endpoint}: {error_msg}")
                GLib.idle_add(callback, None, error_msg)
        
        thread = threading.Thread(target=_background_task, daemon=True)
        thread.start()
    
    def health_check(self, callback: Callable[[bool, Optional[str]], None]) -> None:
        """
        Check if the backend server is running.
        """
        def _background_task():
            try:
                response = self.client.get("/internal/healthz")
                is_healthy = response.status_code == 200
                error_msg = None if is_healthy else f"Server returned {response.status_code}"
                
                # Call the callback on the main thread
                GLib.idle_add(callback, is_healthy, error_msg)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                GLib.idle_add(callback, False, str(e))
        
        thread = threading.Thread(target=_background_task, daemon=True)
        thread.start()
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()


# Global HTTP client instance for the GUI
gui_http_client: Optional[GUILayerHTTPClient] = None


def get_gui_http_client() -> GUILayerHTTPClient:
    """Get or create the global GUI HTTP client instance."""
    global gui_http_client
    if gui_http_client is None:
        gui_http_client = GUILayerHTTPClient()
    return gui_http_client


def shutdown_gui_http_client():
    """Shutdown the global GUI HTTP client."""
    global gui_http_client
    if gui_http_client:
        gui_http_client.close()
        gui_http_client = None