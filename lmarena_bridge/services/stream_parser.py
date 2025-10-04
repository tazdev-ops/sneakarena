"""
Stream parser for processing LMArena server-sent events (SSE).
This module handles parsing the complex streaming responses from LMArena
and converting them to OpenAI-compatible format.
"""

import re
import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, Tuple
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Regular expressions to parse LMArena's SSE format
# These patterns are adapted from the original implementation
TEXT_RE = re.compile(r'a\d+:"([^"]*)"')
IMG_RE = re.compile(r'a\d+:\[(\{.*\})\]')
FINISH_RE = re.compile(r'ad:(\{.*\})')
CLOUDFLARE_RE = re.compile(r'Cloudflare')

# Pattern to extract finish reason from finish event
FINISH_REASON_RE = re.compile(r'"finishReason":"([^"]*)"')


class StreamParser:
    """Parser for LMArena's server-sent events stream."""
    
    def __init__(self, request_id: str, model: str):
        self.request_id = request_id
        self.model = model
        self.has_content = False
        self.full_content = ""
        self.cloudflare_detected = False
    
    def parse_sse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single line from the SSE stream.
        Returns either a delta dictionary or None if not a content line.
        """
        # Check for Cloudflare detection
        if CLOUDFLARE_RE.search(line):
            self.cloudflare_detected = True
            return {
                "type": "error",
                "error": "Cloudflare verification required",
                "message": "Please complete Cloudflare verification in your browser and try again."
            }
        
        # Try to match text content
        text_match = TEXT_RE.search(line)
        if text_match:
            content = text_match.group(1)
            self.full_content += content
            self.has_content = True
            
            return {
                "type": "text",
                "content": content
            }
        
        # Try to match image content
        img_match = IMG_RE.search(line)
        if img_match:
            try:
                img_data = json.loads(img_match.group(1))
                return {
                    "type": "image",
                    "data": img_data
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse image data: {img_match.group(1)}")
                return None
        
        # Try to match finish event
        finish_match = FINISH_RE.search(line)
        if finish_match:
            try:
                finish_data = json.loads(finish_match.group(1))
                finish_reason = finish_data.get("finishReason", "stop")
                
                return {
                    "type": "finish",
                    "finish_reason": finish_reason,
                    "raw_data": finish_data
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse finish data: {finish_match.group(1)}")
                return {
                    "type": "finish",
                    "finish_reason": "stop",
                    "raw_data": {}
                }
        
        return None
    
    async def convert_to_openai_format(self, parsed_data: Dict[str, Any], 
                                     chunk_id: str, index: int = 0) -> Dict[str, Any]:
        """
        Convert parsed LMArena data to OpenAI-compatible format.
        """
        if parsed_data["type"] == "text":
            return {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": self.model,
                "choices": [{
                    "index": index,
                    "delta": {"content": parsed_data["content"]},
                    "finish_reason": None
                }]
            }
        
        elif parsed_data["type"] == "image":
            # For image models, we include the image data
            return {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": self.model,
                "choices": [{
                    "index": index,
                    "delta": {"content": f"[Image: {parsed_data['data'].get('image', 'Generated image')}]"},
                    "finish_reason": None
                }]
            }
        
        elif parsed_data["type"] == "finish":
            finish_reason = parsed_data["finish_reason"]
            # Map LMArena finish reasons to OpenAI equivalents
            if finish_reason.lower() in ["stop", "eos_token"]:
                mapped_reason = "stop"
            elif "length" in finish_reason.lower():
                mapped_reason = "length"
            elif "content" in finish_reason.lower():
                mapped_reason = "content_filter"
            else:
                mapped_reason = finish_reason.lower()
            
            return {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": self.model,
                "choices": [{
                    "index": index,
                    "delta": {},
                    "finish_reason": mapped_reason
                }]
            }
        
        elif parsed_data["type"] == "error":
            return {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": self.model,
                "choices": [{
                    "index": index,
                    "delta": {},
                    "finish_reason": "error"
                }],
                "error": parsed_data.get("error", "Stream error"),
                "error_message": parsed_data.get("message", "An error occurred while processing the stream")
            }
        
        return None
    
    def finalize(self) -> Tuple[bool, str]:
        """
        Get final status and content after parsing is complete.
        Returns (has_content, full_content).
        """
        return self.has_content, self.full_content


class NonStreamingConverter:
    """Converter for non-streaming responses."""
    
    @staticmethod
    def convert_to_openai_completion(response_text: str, 
                                   model: str, 
                                   prompt_tokens: int = 0,
                                   completion_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Convert LMArena response to OpenAI-compatible completion format.
        """
        # If we don't have completion tokens, make a rough estimate
        if completion_tokens is None:
            completion_tokens = len(response_text.split())  # Very rough estimate
        
        total_tokens = prompt_tokens + completion_tokens
        
        return {
            "id": f"chatcmpl-{asyncio.get_event_loop().time()}",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        }


async def parse_stream_response(sse_stream: AsyncGenerator[str, None], 
                              request_id: str, 
                              model: str,
                              is_streaming: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Parse the SSE stream from LMArena and yield OpenAI-compatible chunks.
    """
    parser = StreamParser(request_id, model)
    chunk_index = 0
    
    async for line in sse_stream:
        if line.startswith("data: "):
            data = line[6:]  # Remove "data: " prefix
            
            if data.strip() == "[DONE]":
                # Send final chunk with finish reason
                if is_streaming:
                    final_chunk = {
                        "id": f"chatcmpl-{request_id}-{chunk_index}",
                        "object": "chat.completion.chunk",
                        "created": int(asyncio.get_event_loop().time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield final_chunk
                break
            
            parsed = parser.parse_sse_line(data)
            if parsed:
                if parsed["type"] == "error":
                    # For errors, yield error chunk and return
                    error_chunk = await parser.convert_to_openai_format(
                        parsed, f"chatcmpl-{request_id}-error", chunk_index
                    )
                    yield error_chunk
                    return  # Stop processing on error
                elif parsed["type"] == "finish":
                    if is_streaming:
                        finish_chunk = await parser.convert_to_openai_format(
                            parsed, f"chatcmpl-{request_id}-{chunk_index}", chunk_index
                        )
                        yield finish_chunk
                    break
                elif parsed["type"] in ["text", "image"]:
                    if is_streaming:
                        chunk = await parser.convert_to_openai_format(
                            parsed, f"chatcmpl-{request_id}-{chunk_index}", chunk_index
                        )
                        if chunk:
                            yield chunk
                        chunk_index += 1
    
    # Set the full content on the parser so the caller can access it
    # This is important for non-streaming responses
    if not is_streaming:
        has_content, full_content = parser.finalize()
        if has_content:
            # For non-streaming, we return the complete response at once
            completion = NonStreamingConverter.convert_to_openai_completion(
                full_content, model
            )
            yield completion


def extract_finish_reason(sse_line: str) -> Optional[str]:
    """
    Extract finish reason from an SSE line.
    """
    match = FINISH_RE.search(sse_line)
    if match:
        try:
            data = json.loads(match.group(1))
            return data.get("finishReason")
        except json.JSONDecodeError:
            pass
    return None


def is_cloudflare_challenge(sse_line: str) -> bool:
    """
    Check if the SSE line indicates a Cloudflare challenge.
    """
    return CLOUDFLARE_RE.search(sse_line) is not None