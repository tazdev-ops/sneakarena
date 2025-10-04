"""
OpenAI API adapter for converting OpenAI requests to LMArena-compatible format
and converting LMArena responses back to OpenAI format.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, field_validator
from pathlib import Path
import base64

logger = logging.getLogger(__name__)


class OpenAIChatRequest(BaseModel):
    """Model for OpenAI chat completion request."""
    
    model: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 2):
            raise ValueError('Temperature must be between 0 and 2')
        return v
    
    @field_validator('top_p')
    @classmethod
    def validate_top_p(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Top_p must be between 0 and 1')
        return v


class OpenAIModelResponse(BaseModel):
    """Model for OpenAI list models response."""
    
    object: str = "list"
    data: List[Dict[str, Any]]


class OpenAIChatResponse(BaseModel):
    """Model for OpenAI chat completion response."""
    
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


def convert_openai_request_to_lmarena(request: OpenAIChatRequest, model_id: str, **kwargs) -> Dict[str, Any]:
    """
    Convert OpenAI chat request to LMArena-compatible format.
    
    Args:
        request: OpenAI chat request
        model_id: LMArena model ID
        **kwargs: Additional parameters like session_id, message_id, etc.
    
    Returns:
        Dictionary in LMArena-compatible format
    """
    # Extract conversation history from OpenAI messages
    conversation = []
    
    # Process messages to extract user/assistant turns
    for msg in request.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Handle content that is a list (for multimodal)
        if isinstance(content, list):
            # For multimodal content, we need to handle both text and images
            text_content = ""
            image_urls = []
            
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_content = item.get("text", "")
                    elif item.get("type") == "image_url":
                        image_url = item.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image"):
                            # Handle base64 encoded images
                            image_urls.append(image_url)
                        else:
                            image_urls.append(image_url)
            
            if role == "user":
                conversation.append({"role": "user", "content": text_content, "images": image_urls})
            elif role == "assistant":
                conversation.append({"role": "assistant", "content": text_content})
        else:
            # Handle simple string content
            if role == "user":
                # Check if content contains image data
                if "![image](" in content or "data:image" in content:
                    # Simple image extraction for base64 images
                    import re
                    image_urls = re.findall(r'data:image/[^;]+;base64,[^\s\)]+', content)
                    text_content = re.sub(r'data:image/[^;]+;base64,[^\s\)]+\s*', '', content).strip()
                    conversation.append({"role": "user", "content": text_content, "images": image_urls})
                else:
                    conversation.append({"role": "user", "content": content})
            elif role == "assistant":
                conversation.append({"role": "assistant", "content": content})
            elif role == "system":
                # Handle system messages (will be converted based on settings)
                conversation.append({"role": "system", "content": content})
    
    # Prepare the LMArena request
    lmarena_request = {
        "conversation": conversation,
        "model": model_id,
        "temperature": request.temperature or 1.0,
        "top_p": request.top_p or 1.0,
        "max_tokens": request.max_tokens,
        "stream": request.stream or False,
    }
    
    # Add any additional parameters
    lmarena_request.update(kwargs)
    
    return lmarena_request


def format_lmarena_message_for_sending(text: str, images: Optional[List[str]] = None) -> str:
    """
    Format a message with optional images for sending to LMArena.
    """
    if not images:
        return text
    
    # For now, we'll just append image descriptions to the text
    # In the future, we'll handle actual image uploading
    message = text
    for img in images:
        if img.startswith("data:image"):
            # This is a base64 encoded image
            # We might need to upload to file bed first
            message += f" [Image: base64_data]"
        else:
            # Just a URL
            message += f" [Image: {img}]"
    
    return message


def convert_lmarena_response_to_openai_chunk(
    content: str,
    finish_reason: Optional[str] = None,
    request_id: str = "",
    model: str = "",
    index: int = 0
) -> Dict[str, Any]:
    """
    Convert a chunk of LMArena response to OpenAI format.
    """
    chunk = {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion.chunk",
        "created": 0,  # Will be set by caller
        "model": model,
        "choices": [{
            "index": index,
            "delta": {},
            "finish_reason": finish_reason
        }]
    }
    
    if finish_reason is None and content:
        chunk["choices"][0]["delta"] = {"content": content}
        chunk["choices"][0]["finish_reason"] = None
    elif finish_reason is not None:
        chunk["choices"][0]["delta"] = {}
        chunk["choices"][0]["finish_reason"] = finish_reason
    
    return chunk


def convert_lmarena_response_to_openai_completion(
    content: str,
    request_id: str,
    model: str,
    finish_reason: str = "stop",
    prompt_tokens: int = 0,
    completion_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convert LMArena response to OpenAI completion format.
    """
    # Calculate token counts if not provided
    if completion_tokens is None:
        completion_tokens = len(content.split())  # Rough estimate
    
    total_tokens = prompt_tokens + completion_tokens
    
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": 0,  # Will be set by caller
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": finish_reason
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
    }


def extract_model_info(model_name: str, models_map: Dict[str, str]) -> Optional[str]:
    """
    Extract the LMArena model ID from the requested model name.
    
    Args:
        model_name: The model name as requested by the client
        models_map: Mapping of friendly names to LMArena IDs
        
    Returns:
        LMArena model ID or None if not found
    """
    if model_name in models_map:
        model_spec = models_map[model_name]
        # The model spec can be just the UUID or UUID:type
        if ':' in model_spec:
            return model_spec.split(':')[0]  # Return just the UUID part
        return model_spec
    
    return None


def is_image_model(model_name: str, models_map: Dict[str, str]) -> bool:
    """
    Check if a model is an image generation model.
    
    Args:
        model_name: The model name as requested by the client
        models_map: Mapping of friendly names to LMArena IDs
        
    Returns:
        True if the model is an image model, False otherwise
    """
    if model_name in models_map:
        model_spec = models_map[model_name]
        if ':' in model_spec:
            model_type = model_spec.split(':')[1]
            return model_type == 'image'
    return False


def apply_tavern_mode(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Apply tavern mode: merge all system messages into one at the beginning.
    
    Args:
        messages: List of OpenAI messages
        
    Returns:
        Modified list of messages with merged system messages
    """
    system_messages = []
    other_messages = []
    
    for msg in messages:
        if msg.get("role") == "system":
            system_messages.append(msg.get("content", ""))
        else:
            other_messages.append(msg)
    
    if system_messages:
        # Combine all system messages into one
        combined_system_content = "\n".join(system_messages)
        # Put the combined system message at the beginning
        return [{"role": "system", "content": combined_system_content}] + other_messages
    
    return messages


def apply_bypass_mode(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Apply bypass mode: inject an empty user message before the last user message.
    
    Args:
        messages: List of OpenAI messages
        
    Returns:
        Modified list of messages with bypass message injected
    """
    if not messages:
        return messages
    
    # Find the last user message
    last_user_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break
    
    if last_user_idx != -1:
        # Insert an empty user message before the last user message
        messages.insert(last_user_idx, {"role": "user", "content": ""})
    
    return messages


def validate_api_key(provided_key: Optional[str], expected_key: Optional[str]) -> bool:
    """
    Validate the API key from the request against the expected key.
    
    Args:
        provided_key: API key provided in the request
        expected_key: Expected API key from settings
        
    Returns:
        True if valid or if no key is required, False otherwise
    """
    if not expected_key:
        # No API key required
        return True
    
    if not provided_key:
        # Key required but not provided
        return False
    
    return provided_key == expected_key


def create_openai_model_list(models_map: Dict[str, str]) -> OpenAIModelResponse:
    """
    Create OpenAI-compatible model list from models mapping.
    
    Args:
        models_map: Dictionary mapping friendly names to LMArena IDs
        
    Returns:
        OpenAIModelResponse with model list
    """
    models = []
    
    for friendly_name, model_spec in models_map.items():
        # Extract just the name part if it has type info
        if ':' in model_spec:
            model_id = model_spec.split(':')[0]
        else:
            model_id = model_spec
            
        models.append({
            "id": friendly_name,
            "object": "model",
            "created": 1234567890,  # Placeholder timestamp
            "owned_by": "LMArenaBridge"
        })
    
    return OpenAIModelResponse(data=models)


def get_lmarena_model_type(model_name: str, models_map: Dict[str, str]) -> str:
    """
    Get the model type (text or image) for a given model name.
    
    Args:
        model_name: The model name as requested by the client
        models_map: Mapping of friendly names to LMArena IDs
        
    Returns:
        Model type as string ('text' or 'image')
    """
    if model_name in models_map:
        model_spec = models_map[model_name]
        if ':' in model_spec:
            model_type = model_spec.split(':')[1]
            return model_type
    return 'text'  # Default to text