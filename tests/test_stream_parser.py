import pytest
import asyncio
from lmarena_bridge.services.stream_parser import TEXT_RE, IMG_RE, FINISH_RE

def test_text_pattern():
    sample = 'a0:"Hello world"'
    match = TEXT_RE.search(sample)
    assert match
    assert match.group(1) == "Hello world"

def test_image_pattern():
    sample = 'a2:[{"type":"image","image":"http://example.com/img.png"}]'
    match = IMG_RE.search(sample)
    assert match

def test_finish_pattern():
    sample = 'ad:{"finishReason":"stop"}'
    match = FINISH_RE.search(sample)
    assert match