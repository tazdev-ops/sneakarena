"""
WebSocket Hub for managing connections between API requests and browser clients.
This allows multiple tabs/api clients to potentially connect to browser instances.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, Callable, Awaitable
from uuid import uuid4
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

logger = logging.getLogger(__name__)


class WebSocketHub:
    """Manages WebSocket connections between API layer and browser clients."""
    
    def __init__(self):
        # Map of client IDs to WebSocket connections
        self.connections: Dict[str, WebSocket] = {}
        
        # Map of API request IDs to client IDs (to route responses)
        self.request_routing: Dict[str, str] = {}
        
        # Map of client IDs to pending API requests
        self.pending_requests: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Set of connected client IDs
        self.connected_clients: Set[str] = set()
        
        # Callbacks for handling events
        self.on_client_connect: List[Callable[[str], None]] = []
        self.on_client_disconnect: List[Callable[[str], None]] = []
        self.on_request_forward: List[Callable[[str, Dict[str, Any]], None]] = []
        self.on_response_receive: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def register_client(self, client_id: str, websocket: WebSocket) -> None:
        """Register a new browser client connection."""
        async with self._lock:
            self.connections[client_id] = websocket
            self.connected_clients.add(client_id)
        
        # Notify listeners
        for callback in self.on_client_connect:
            try:
                callback(client_id)
            except Exception as e:
                logger.error(f"Error in client connect callback: {e}")
        
        logger.info(f"Browser client connected: {client_id}")
    
    async def unregister_client(self, client_id: str) -> None:
        """Unregister a browser client connection."""
        async with self._lock:
            if client_id in self.connections:
                del self.connections[client_id]
            
            if client_id in self.connected_clients:
                self.connected_clients.remove(client_id)
            
            # Clean up pending requests for this client
            if client_id in self.pending_requests:
                del self.pending_requests[client_id]
            
            # Remove routing entries for this client
            request_ids_to_remove = [
                req_id for req_id, client_id_route in self.request_routing.items()
                if client_id_route == client_id
            ]
            for req_id in request_ids_to_remove:
                del self.request_routing[req_id]
        
        # Notify listeners
        for callback in self.on_client_disconnect:
            try:
                callback(client_id)
            except Exception as e:
                logger.error(f"Error in client disconnect callback: {e}")
        
        logger.info(f"Browser client disconnected: {client_id}")
    
    async def has_connections(self) -> bool:
        """Check if there are any connected clients."""
        return len(self.connected_clients) > 0
    
    async def get_connected_clients(self) -> Set[str]:
        """Get a set of currently connected client IDs."""
        return self.connected_clients.copy()
    
    async def route_request_to_client(self, request_id: str, client_id: str) -> bool:
        """Route an API request to a specific client."""
        async with self._lock:
            if client_id not in self.connected_clients:
                return False
            self.request_routing[request_id] = client_id
            return True
    
    async def assign_request_to_any_client(self, request_id: str) -> Optional[str]:
        """Assign an API request to any available client."""
        if not self.connected_clients:
            return None
        
        # For now, just pick the first available client
        # In the future, we could implement more sophisticated routing
        client_id = next(iter(self.connected_clients))
        async with self._lock:
            self.request_routing[request_id] = client_id
        return client_id
    
    async def forward_request_to_client(self, request_id: str, request_data: Dict[str, Any]) -> bool:
        """Forward an API request to the appropriate browser client."""
        async with self._lock:
            if request_id not in self.request_routing:
                logger.warning(f"No client assigned for request: {request_id}")
                return False
            
            client_id = self.request_routing[request_id]
            if client_id not in self.connections:
                logger.warning(f"Client {client_id} not found for request: {request_id}")
                return False
            
            websocket = self.connections[client_id]
        
        # Add request ID to the data so client knows which request this is for
        request_data['request_id'] = request_id
        
        try:
            # Notify listeners
            for callback in self.on_request_forward:
                try:
                    callback(client_id, request_data)
                except Exception as e:
                    logger.error(f"Error in request forward callback: {e}")
            
            # Send the request to the browser client
            await websocket.send_json(request_data)
            
            # Track this pending request
            async with self._lock:
                self.pending_requests[client_id][request_id] = request_data
            
            logger.debug(f"Forwarded request {request_id} to client {client_id}")
            return True
            
        except WebSocketDisconnect:
            logger.warning(f"Client {client_id} disconnected while forwarding request {request_id}")
            await self.unregister_client(client_id)
            return False
        except Exception as e:
            logger.error(f"Error forwarding request {request_id} to client {client_id}: {e}")
            return False
    
    async def send_response_to_api_client(self, request_id: str, response_data: Dict[str, Any], send_to_websocket: Optional[WebSocket] = None) -> bool:
        """Send a response back to the API client."""
        # In the actual implementation, we'd have a way to send back to the API client
        # For now, we'll just call any registered callbacks
        
        # Notify listeners
        for callback in self.on_response_receive:
            try:
                callback(request_id, response_data)
            except Exception as e:
                logger.error(f"Error in response receive callback: {e}")
        
        logger.debug(f"Received response for request {request_id}")
        
        # Remove from pending requests
        async with self._lock:
            for client_id, pending in self.pending_requests.items():
                if request_id in pending:
                    del pending[request_id]
        
        return True
    
    async def handle_client_disconnect(self, client_id: str) -> None:
        """Handle client disconnection and clean up related data."""
        await self.unregister_client(client_id)
    
    def create_request_id(self) -> str:
        """Create a unique request ID."""
        return f"req_{uuid4().hex[:8]}"
    
    def create_client_id(self) -> str:
        """Create a unique client ID."""
        return f"client_{uuid4().hex[:8]}"


# Global hub instance
websocket_hub = WebSocketHub()