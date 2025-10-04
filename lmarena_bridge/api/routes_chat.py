"""
API routes for chat completions.
Implements the /v1/chat/completions endpoint for OpenAI compatibility.
"""

import logging
import asyncio
import time
import json
from typing import Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from ..settings import load_settings, load_models, load_model_endpoint_map
from ..services.openai_adapter import (
    OpenAIChatRequest, 
    convert_openai_request_to_lmarena,
    extract_model_info,
    is_image_model,
    apply_tavern_mode,
    apply_bypass_mode,
    validate_api_key,
    get_lmarena_model_type
)
from ..services.websocket_hub import websocket_hub
from ..services.stream_parser import parse_stream_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/v1/chat/completions", tags=["chat"])
async def chat_completions(request: Request) -> Response:
    """
    Create a chat completion using LMArena as the backend.
    Supports both streaming and non-streaming responses.
    """
    # Get API key from header
    auth_header = request.headers.get("Authorization")
    provided_api_key = None
    if auth_header and auth_header.startswith("Bearer "):
        provided_api_key = auth_header[7:]
    
    # Load settings and models
    settings = load_settings()
    
    # Validate API key if one is required
    if not validate_api_key(provided_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Parse the request body
    try:
        request_json = await request.json()
        openai_request = OpenAIChatRequest.model_validate(request_json)
    except Exception as e:
        logger.error(f"Invalid request format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
    
    logger.info(f"API CALL [ID: {openai_request.model}] Request for model: {openai_request.model}")
    
    # Check if we have a browser connection
    if not await websocket_hub.has_connections():
        raise HTTPException(
            status_code=503,
            detail="No browser connected to the bridge. Please ensure LMArena is open in a browser with the Tampermonkey script installed."
        )
    
    # Load models and endpoint mapping
    models_map = load_models()
    endpoint_map = load_model_endpoint_map()
    
    # Get the LMArena model ID
    model_id = extract_model_info(openai_request.model, models_map)
    if not model_id:
        raise HTTPException(
            status_code=404, 
            detail=f"Model '{openai_request.model}' not found in models configuration"
        )
    
    # Determine if this is an image model
    is_img_model = is_image_model(openai_request.model, models_map)
    
    # Apply tavern mode if enabled
    messages = openai_request.messages
    if settings.tavern_mode_enabled:
        messages = apply_tavern_mode(messages)
    
    # Apply bypass mode if enabled
    if settings.bypass_enabled:
        messages = apply_bypass_mode(messages)
    
    # Determine session configuration
    session_config = {
        "session_id": settings.session_id,
        "message_id": settings.message_id,
        "mode": settings.id_updater_last_mode,
    }
    
    # Check if there's a specific endpoint mapping for this model
    if openai_request.model in endpoint_map:
        model_config = endpoint_map[openai_request.model]
        
        # Handle multiple possible configurations (random selection)
        if isinstance(model_config, list):
            import random
            model_config = random.choice(model_config)
        
        # Override session config with model-specific settings
        session_config.update(model_config)
    elif not settings.use_default_ids_if_mapping_not_found:
        raise HTTPException(
            status_code=400,
            detail=f"No endpoint mapping found for model '{openai_request.model}' and default fallback is disabled"
        )
    
    # Validate required session IDs are present
    if (session_config["session_id"] == "YOUR_SESSION_ID" or 
        session_config["message_id"] == "YOUR_MESSAGE_ID"):
        raise HTTPException(
            status_code=500,
            detail="Session IDs not configured. Please capture session IDs using the GUI or setup wizard."
        )
    
    # Generate a unique request ID
    request_id = websocket_hub.create_request_id()
    
    # Convert OpenAI request to LMArena format
    lmarena_request = convert_openai_request_to_lmarena(
        openai_request,
        model_id,
        **session_config
    )
    
    # Add the messages to the LMArena request
    lmarena_request["messages"] = messages
    
    # Update start time for timeout calculation
    start_time = time.time()
    
    # Check if streaming is requested
    if openai_request.stream:
        logger.info(f"STREAMER [ID: {request_id}] Initiating streaming request")
        
        async def generate_stream():
            """Generate streaming response from LMArena."""
            try:
                # Assign request to a client
                client_id = await websocket_hub.assign_request_to_any_client(request_id)
                if not client_id:
                    logger.error(f"No available client for request {request_id}")
                    yield f"data: {str({'error': 'No browser client available'})}\n\n"
                    return
                
                # Forward request to browser client
                success = await websocket_hub.forward_request_to_client(request_id, lmarena_request)
                if not success:
                    logger.error(f"Failed to forward request {request_id} to client")
                    yield f"data: {str({'error': 'Failed to communicate with browser client'})}\n\n"
                    return
                
                # Create a mock SSE stream (in real implementation, this would come from browser)
                # For now, we'll simulate the streaming response
                sample_response = "This is a simulated streaming response from LMArena."
                for i, char in enumerate(sample_response.split()):
                    if time.time() - start_time > settings.stream_response_timeout_seconds:
                        logger.warning(f"Request {request_id} timed out")
                        yield f"data: {str({'error': 'Request timed out'})}\n\n"
                        break
                    
                    chunk_data = {
                        "id": f"chatcmpl-{request_id}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": openai_request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": char + " "},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    await asyncio.sleep(0.01)  # Small delay to simulate streaming
                
                # Send finish chunk
                finish_chunk = {
                    "id": f"chatcmpl-{request_id}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": openai_request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(finish_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                
            except asyncio.CancelledError:
                logger.info(f"Request {request_id} was cancelled")
                # Cleanup if needed
                raise
            except Exception as e:
                logger.error(f"Error in streaming response for {request_id}: {e}")
                error_chunk = {
                    "error": {
                        "type": "server_error",
                        "message": str(e)
                    }
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
                yield "data: [DONE]\n\n"
        
        # Return streaming response
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    
    else:  # Non-streaming request
        logger.info(f"COMPLETION [ID: {request_id}] Initiating completion request")
        
        try:
            # Assign request to a client
            client_id = await websocket_hub.assign_request_to_any_client(request_id)
            if not client_id:
                raise HTTPException(
                    status_code=503,
                    detail="No browser client available"
                )
            
            # Forward request to browser client
            success = await websocket_hub.forward_request_to_client(request_id, lmarena_request)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to communicate with browser client"
                )
            
            # In a real implementation, we would wait for the response from the browser
            # For now, we'll return a simulated response
            response_content = "This is a simulated completion response from LMArena."
            
            # Calculate token usage (simulated)
            prompt_tokens = sum(len(str(msg.get("content", ""))) for msg in messages)
            completion_tokens = len(response_content.split())
            total_tokens = prompt_tokens + completion_tokens
            
            response = {
                "id": f"chatcmpl-{request_id}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": openai_request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            }
            
            logger.info(f"COMPLETION [ID: {request_id}] Completed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error in completion request {request_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing completion: {str(e)}")


