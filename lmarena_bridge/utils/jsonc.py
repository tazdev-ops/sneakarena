"""
JSONC (JSON with Comments) parser utility.
Supports both JSON and JSONC files with comments and trailing commas.
"""

import json
import re
from pathlib import Path
from typing import Any, Union


def remove_comments(text: str) -> str:
    """
    Remove comments from JSONC text.
    Supports both // single-line and /* */ multi-line comments.
    """
    # Remove single-line comments
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    # Remove multi-line comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text


def parse_jsonc(content: str) -> Any:
    """
    Parse JSONC content (JSON with comments) into Python object.
    """
    content = remove_comments(content)
    # Remove trailing commas before closing braces/brackets
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    return json.loads(content)


def load_jsonc_file(file_path: Union[str, Path]) -> Any:
    """
    Load and parse a JSONC file.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return parse_jsonc(content)


def save_jsonc_file(file_path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """
    Save data to a JSON file with formatting.
    While we save as regular JSON, the loader will handle comments when reading.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.write('\n')


# For backward compatibility
loads = parse_jsonc
dumps = json.dumps