"""
API routes for models endpoint.
Implements the /v1/models endpoint to list available models.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time

from ..settings import load_settings, load_models
from ..services.openai_adapter import create_openai_model_list

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/v1/models", tags=["models"])
async def list_models() -> Dict[str, Any]:
    """
    List all available models in OpenAI-compatible format.
    """
    try:
        # Load current settings and models
        settings = load_settings()
        models_map = load_models()
        
        logger.debug(f"Available models: {list(models_map.keys())}")
        
        # Create OpenAI-compatible model list
        openai_model_response = create_openai_model_list(models_map)
        
        # Add request timestamp
        response = openai_model_response.model_dump()
        response["created"] = int(time.time())
        
        logger.info(f"Returning {len(response['data'])} models to client")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in list_models: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading models: {str(e)}")


@router.get("/v1/models/{model}", tags=["models"])
async def retrieve_model(model: str) -> Dict[str, Any]:
    """
    Retrieve information about a specific model.
    """
    try:
        # Load current models
        models_map = load_models()
        
        if model not in models_map:
            raise HTTPException(status_code=404, detail=f"Model '{model}' not found")
        
        # Get the model specification
        model_spec = models_map[model]
        
        # Extract model ID (without type suffix)
        if ':' in model_spec:
            model_id = model_spec.split(':')[0]
        else:
            model_id = model_spec
        
        # Create response in OpenAI format
        response = {
            "id": model,
            "object": "model",
            "created": 1234567890,  # Placeholder timestamp
            "owned_by": "LMArenaBridge",
            "root": model,
            "parent": None,
            "metadata": {
                "lmarena_model_id": model_id,
                "model_type": model_spec.split(':')[1] if ':' in model_spec else 'text'
            }
        }
        
        logger.debug(f"Returning model info for: {model}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in retrieve_model for '{model}': {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving model: {str(e)}")


@router.get("/internal/models/refresh", tags=["internal"])
async def refresh_models() -> Dict[str, Any]:
    """
    Internal endpoint to refresh the models list from configuration.
    This doesn't fetch from LMArena but reloads from our config files.
    """
    try:
        # Load models to ensure they're fresh
        models_map = load_models()
        
        # Return the number of models loaded
        result = {
            "status": "success",
            "message": f"Refreshed {len(models_map)} models from configuration",
            "model_count": len(models_map),
            "models": list(models_map.keys())
        }
        
        logger.info(f"Models refreshed: {len(models_map)} models loaded")
        
        return result
        
    except Exception as e:
        logger.error(f"Error refreshing models: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing models: {str(e)}")


@router.get("/internal/models/raw", tags=["internal"])
async def get_raw_models() -> Dict[str, str]:
    """
    Internal endpoint to get raw models mapping (for debugging).
    """
    try:
        models_map = load_models()
        
        # Return the raw mapping
        return models_map
        
    except Exception as e:
        logger.error(f"Error getting raw models: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading raw models: {str(e)}")