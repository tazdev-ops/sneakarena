"""
Internal API routes for health checks and debugging.
These are not part of the OpenAI API but are used for internal purposes.
"""

import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import asyncio
import time

from ..settings import load_settings
from ..services.websocket_hub import websocket_hub

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/internal/healthz", tags=["internal"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify the server is running.
    """
    return {"status": "ok"}


@router.get("/internal/config", tags=["internal"])
async def get_config() -> Dict[str, Any]:
    """
    Get current server configuration (excluding sensitive data).
    """
    settings = load_settings()
    
    # Create a safe config dict without sensitive information
    safe_config = {
        "version": settings.version,
        "server_host": settings.server_host,
        "server_port": settings.server_port,
        "session_id": settings.session_id if settings.session_id != "YOUR_SESSION_ID" else None,
        "message_id": settings.message_id if settings.message_id != "YOUR_MESSAGE_ID" else None,
        "id_updater_last_mode": settings.id_updater_last_mode,
        "id_updater_battle_target": settings.id_updater_battle_target,
        "enable_auto_update": settings.enable_auto_update,
        "bypass_enabled": settings.bypass_enabled,
        "tavern_mode_enabled": settings.tavern_mode_enabled,
        "file_bed_enabled": settings.file_bed_enabled,
        "use_default_ids_if_mapping_not_found": settings.use_default_ids_if_mapping_not_found,
        "stream_response_timeout_seconds": settings.stream_response_timeout_seconds,
        "enable_idle_restart": settings.enable_idle_restart,
        "idle_restart_timeout_seconds": settings.idle_restart_timeout_seconds,
        "has_api_key": bool(settings.api_key),  # Only indicate if set, not the actual value
        "auto_open_browser": settings.auto_open_browser,
    }
    
    return safe_config


@router.get("/internal/status", tags=["internal"])
async def get_status() -> Dict[str, Any]:
    """
    Get server status including connection information.
    """
    connected_clients = await websocket_hub.get_connected_clients()
    
    status = {
        "server_time": int(time.time()),
        "connected_clients_count": len(connected_clients),
        "connected_clients": list(connected_clients),
        "has_active_connections": len(connected_clients) > 0,
    }
    
    return status


@router.websocket("/internal/ws-debug")
async def websocket_debug(websocket: WebSocket):
    """
    WebSocket endpoint for debugging connections.
    """
    await websocket.accept()
    
    # Generate a client ID
    client_id = websocket_hub.create_client_id()
    
    try:
        # Register with the hub
        await websocket_hub.register_client(client_id, websocket)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "server_time": int(time.time()),
            "message": f"Debug WebSocket connection established with ID: {client_id}"
        })
        
        # Listen for messages (though this is primarily a server-sent connection)
        while True:
            try:
                # Wait for any message from client
                data = await websocket.receive_json()
                logger.info(f"Debug WS {client_id} received: {data}")
                
                # Echo back the received message
                await websocket.send_json({
                    "type": "echo",
                    "original_data": data,
                    "server_time": int(time.time())
                })
                
            except WebSocketDisconnect:
                logger.info(f"Debug WebSocket disconnected: {client_id}")
                break
            except Exception as e:
                logger.error(f"Error handling debug WebSocket message from {client_id}: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"Debug WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Error in debug WebSocket connection {client_id}: {e}")
    finally:
        # Clean up the connection
        await websocket_hub.handle_client_disconnect(client_id)


@router.get("/internal/debug/hub-status", tags=["internal"])
async def get_hub_status() -> Dict[str, Any]:
    """
    Get detailed status of the WebSocket hub.
    """
    connected_clients = await websocket_hub.get_connected_clients()
    
    hub_status = {
        "total_connections": len(websocket_hub.connections),
        "connected_clients": list(connected_clients),
        "request_routing_count": len(websocket_hub.request_routing),
        "pending_requests_count": sum(len(reqs) for reqs in websocket_hub.pending_requests.values()),
        "routing_table": websocket_hub.request_routing.copy()
    }
    
    return hub_status


@router.get("/internal/uptime", tags=["internal"])
async def get_uptime() -> Dict[str, float]:
    """
    Get server uptime information.
    """
    # For now, we'll return a simple timestamp
    # In the future, we could track actual uptime
    return {
        "server_start_time": time.time(),  # This would be set at server start
        "current_time": time.time(),
        "uptime_seconds": 0  # Placeholder
    }


@router.get("/internal/metrics", tags=["internal"])
async def get_metrics() -> Dict[str, Any]:
    """
    Get server metrics and statistics.
    """
    connected_clients = await websocket_hub.get_connected_clients()
    
    metrics = {
        "timestamp": int(time.time()),
        "connected_browser_clients": len(connected_clients),
        "has_browser_connection": len(connected_clients) > 0,
        "estimated_active_sessions": len(connected_clients),  # Rough estimate
    }
    
    return metrics


@router.post("/internal/reload-config", tags=["internal"])
async def reload_config() -> Dict[str, str]:
    """
    Reload configuration from disk.
    """
    try:
        # For now, we'll just verify the config can be loaded
        settings = load_settings()
        
        # This would trigger any config reload logic
        logger.info("Configuration reloaded successfully")
        
        return {"status": "success", "message": "Configuration reloaded"}
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        raise HTTPException(status_code=500, detail=f"Error reloading config: {str(e)}")


@router.get("/internal/info", tags=["internal"])
async def get_server_info() -> Dict[str, Any]:
    """
    Get general server information.
    """
    settings = load_settings()
    
    info = {
        "version": settings.version,
        "server_type": "LMArena Bridge",
        "api_compatibility": "OpenAI v1",
        "features": {
            "streaming": True,
            "non_streaming": True,
            "bypass_mode": settings.bypass_enabled,
            "tavern_mode": settings.tavern_mode_enabled,
            "file_bed": settings.file_bed_enabled,
            "battle_mode": True
        },
        "config_location": str(settings.__class__.__module__),  # Placeholder
    }
    
    return info