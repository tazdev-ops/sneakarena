"""
Configuration settings for LMArena Bridge.
Handles loading, validation, and saving of configuration files.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .utils.jsonc import load_jsonc_file, save_jsonc_file
from pydantic import BaseModel, field_validator, model_validator
from .utils.jsonc import load_jsonc_file, save_jsonc_file

# Define the config directory path
CONFIG_DIR = Path(os.environ.get('LMABRIDGE_CONFIG_DIR', 
                                os.path.expanduser('~/.config/lmarena-bridge')))

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Define default config file paths
CONFIG_FILE = CONFIG_DIR / 'config.jsonc'
MODELS_FILE = CONFIG_DIR / 'models.json'
MODEL_ENDPOINT_MAP_FILE = CONFIG_DIR / 'model_endpoint_map.json'


class Settings(BaseModel):
    """Main application settings model with validation."""
    
    # Version tracking
    version: str = "3.0.0"
    
    # Session configuration
    session_id: str = "YOUR_SESSION_ID"
    message_id: str = "YOUR_MESSAGE_ID"
    
    # Operation modes
    id_updater_last_mode: str = "direct_chat"  # "direct_chat" or "battle"
    id_updater_battle_target: Optional[str] = "A"  # "A" or "B" for battle mode
    
    # Feature flags
    enable_auto_update: bool = True
    bypass_enabled: bool = True
    tavern_mode_enabled: bool = False
    
    # File bed configuration (for image uploads)
    file_bed_enabled: bool = False
    file_bed_upload_url: str = "http://127.0.0.1:5180/upload"
    file_bed_api_key: str = ""
    
    # Behavior settings
    use_default_ids_if_mapping_not_found: bool = True
    
    # Server settings
    stream_response_timeout_seconds: int = 360
    enable_idle_restart: bool = False
    idle_restart_timeout_seconds: int = -1
    api_key: Optional[str] = ""
    auto_open_browser: bool = False
    server_host: str = "127.0.0.1"
    server_port: int = 5102
    
    # Validation methods
    @field_validator('session_id', 'message_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        if v == "YOUR_SESSION_ID" or v == "YOUR_MESSAGE_ID":
            return v
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Invalid UUID: {v}')
    
    @field_validator('id_updater_last_mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ["direct_chat", "battle"]:
            raise ValueError(f'Mode must be "direct_chat" or "battle", got: {v}')
        return v
    
    @field_validator('id_updater_battle_target')
    @classmethod
    def validate_battle_target(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ["A", "B"]:
            raise ValueError(f'Battle target must be "A" or "B", got: {v}')
        return v
    
    @field_validator('server_port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f'Port must be between 1 and 65535, got: {v}')
        return v
    
    @field_validator('stream_response_timeout_seconds')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f'Timeout must be positive, got: {v}')
        return v
    
    @model_validator(mode='after')
    def validate_battle_mode(self) -> 'Settings':
        if self.id_updater_last_mode == "battle" and not self.id_updater_battle_target:
            raise ValueError('Battle target must be specified when in battle mode')
        return self


def create_default_config() -> Dict[str, Any]:
    """Create default configuration dictionary."""
    return {
        "version": "3.0.0",
        "session_id": "YOUR_SESSION_ID",
        "message_id": "YOUR_MESSAGE_ID",
        "id_updater_last_mode": "direct_chat",
        "id_updater_battle_target": "A",
        "enable_auto_update": True,
        "bypass_enabled": True,
        "tavern_mode_enabled": False,
        "file_bed_enabled": False,
        "file_bed_upload_url": "http://127.0.0.1:5180/upload",
        "file_bed_api_key": "",
        "use_default_ids_if_mapping_not_found": True,
        "stream_response_timeout_seconds": 360,
        "enable_idle_restart": False,
        "idle_restart_timeout_seconds": -1,
        "api_key": "",
        "auto_open_browser": False,
        "server_host": "127.0.0.1",
        "server_port": 5102
    }


def create_default_models() -> Dict[str, str]:
    """Create default models mapping."""
    return {
        "gemini-2.5-pro": "YOUR_MODEL_ID:text",
        "gpt-4": "YOUR_MODEL_ID:text",
        "claude-3": "YOUR_MODEL_ID:text"
    }


def create_default_model_endpoint_map() -> Dict[str, Any]:
    """Create default model endpoint mapping."""
    return {}


def ensure_config_files_exist() -> None:
    """Ensure all required config files exist with default content."""
    # Create config.jsonc if it doesn't exist
    if not CONFIG_FILE.exists():
        config_data = create_default_config()
        save_jsonc_file(CONFIG_FILE, config_data)
        print(f"Created default config file: {CONFIG_FILE}")
    
    # Create models.json if it doesn't exist
    if not MODELS_FILE.exists():
        models_data = create_default_models()
        save_jsonc_file(MODELS_FILE, models_data)
        print(f"Created default models file: {MODELS_FILE}")
    
    # Create model_endpoint_map.json if it doesn't exist
    if not MODEL_ENDPOINT_MAP_FILE.exists():
        map_data = create_default_model_endpoint_map()
        save_jsonc_file(MODEL_ENDPOINT_MAP_FILE, map_data)
        print(f"Created default model endpoint map file: {MODEL_ENDPOINT_MAP_FILE}")


def load_settings() -> Settings:
    """Load settings from config file with fallback to defaults."""
    ensure_config_files_exist()
    
    try:
        # Try to load config from file
        config_data = load_jsonc_file(CONFIG_FILE)
        
        # Update with defaults for missing keys
        default_config = create_default_config()
        for key, value in default_config.items():
            if key not in config_data:
                config_data[key] = value
        
        # Create settings instance with validation
        settings = Settings(**config_data)
        
        # Save back to file if there were updates (new defaults added)
        current_data = config_data.copy()
        for key in ["session_id", "message_id"]:
            if key in current_data and current_data[key] != getattr(settings, key):
                current_data[key] = getattr(settings, key)
        
        if current_data != config_data:
            save_jsonc_file(CONFIG_FILE, current_data)
        
        return settings
        
    except Exception as e:
        print(f"Error loading config, using defaults: {e}")
        # Return default settings
        return Settings()


def update_config_partial(updates: Dict[str, Any]) -> bool:
    """Update configuration with partial data."""
    try:
        # Load existing config
        if CONFIG_FILE.exists():
            config_data = load_jsonc_file(CONFIG_FILE)
        else:
            config_data = create_default_config()
        
        # Apply updates
        config_data.update(updates)
        
        # Validate the updated config
        Settings(**config_data)
        
        # Save updated config
        save_jsonc_file(CONFIG_FILE, config_data)
        return True
        
    except Exception as e:
        print(f"Error updating config: {e}")
        return False


def load_models() -> Dict[str, str]:
    """Load the models mapping from file."""
    ensure_config_files_exist()
    try:
        return load_jsonc_file(MODELS_FILE)
    except Exception as e:
        print(f"Error loading models, using defaults: {e}")
        models_data = create_default_models()
        save_jsonc_file(MODELS_FILE, models_data)
        return models_data


def load_model_endpoint_map() -> Dict[str, Any]:
    """Load the model endpoint mapping from file."""
    ensure_config_files_exist()
    try:
        return load_jsonc_file(MODEL_ENDPOINT_MAP_FILE)
    except Exception as e:
        print(f"Error loading model endpoint map, using defaults: {e}")
        map_data = create_default_model_endpoint_map()
        save_jsonc_file(MODEL_ENDPOINT_MAP_FILE, map_data)
        return map_data