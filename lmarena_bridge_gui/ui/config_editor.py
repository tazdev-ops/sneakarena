"""
Configuration editor component for the GTK4 GUI.
Provides a form-based interface for editing configuration settings.
"""

import json
import logging
import threading
from typing import Optional, Dict, Any
from gi.repository import Gtk, Adw, GObject, GLib

from lmarena_bridge.settings import load_settings, update_config_partial
from ..utils.notifications import show_error_async, show_info_async
from .widgets import ExpandableSection

logger = logging.getLogger(__name__)


class ConfigEditor(Adw.PreferencesPage):
    """
    A preferences page for editing configuration settings.
    """
    
    __gsignals__ = {
        'config-saved': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'config-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, http_client):
        super().__init__()
        self.set_title("Configuration")
        self.set_name("config")
        
        self.http_client = http_client
        self._current_config = {}
        
        # Create the preferences groups
        self._create_session_group()
        self._create_operation_group()
        self._create_features_group()
        self._create_file_bed_group()
        self._create_advanced_group()
        
        # Action bar with save/reload buttons
        self._create_action_bar()
    
    def _create_session_group(self):
        """Create the session settings group."""
        session_group = Adw.PreferencesGroup()
        session_group.set_title("Session Settings")
        session_group.set_description("IDs captured from LMArena browser session")
        self.add(session_group)
        
        # Session ID
        self._session_row = Adw.EntryRow()
        self._session_row.set_title("Session ID")
        self._session_row.set_show_apply_button(True)
        session_group.add(self._session_row)
        
        # Message ID
        self._message_row = Adw.EntryRow()
        self._message_row.set_title("Message ID")
        self._message_row.set_show_apply_button(True)
        session_group.add(self._message_row)
    
    def _create_operation_group(self):
        """Create the operation mode group."""
        operation_group = Adw.PreferencesGroup()
        operation_group.set_title("Operation Mode")
        operation_group.set_description("How the bridge interacts with LMArena")
        self.add(operation_group)
        
        # Mode selection
        self._mode_combo = Adw.ComboRow()
        self._mode_combo.set_title("Mode")
        self._mode_combo.set_model(Gtk.StringList.new(["Direct Chat", "Battle"]))
        operation_group.add(self._mode_combo)
        
        # Battle target (only visible in battle mode)
        self._battle_target_combo = Adw.ComboRow()
        self._battle_target_combo.set_title("Battle Target")
        self._battle_target_combo.set_model(Gtk.StringList.new(["A", "B"]))
        self._battle_target_combo.set_sensitive(False)  # Initially disabled
        operation_group.add(self._battle_target_combo)
        
        # Connect mode combo change to show/hide battle target
        self._mode_combo.connect('notify::selected', self._on_mode_changed)
    
    def _create_features_group(self):
        """Create the features group."""
        features_group = Adw.PreferencesGroup()
        features_group.set_title("Features")
        self.add(features_group)
        
        # Auto-update
        self._auto_update_switch = self._create_pref_switch("Enable Auto-Update", True)
        features_group.add(self._auto_update_switch)
        
        # Bypass mode
        self._bypass_switch = self._create_pref_switch("Enable Bypass Mode", True)
        self._bypass_switch.set_subtitle("Inject empty messages to bypass filters")
        features_group.add(self._bypass_switch)
        
        # Tavern mode
        self._tavern_switch = self._create_pref_switch("Enable Tavern Mode", False)
        self._tavern_switch.set_subtitle("Merge system messages (for character cards)")
        features_group.add(self._tavern_switch)
    
    def _create_file_bed_group(self):
        """Create the file bed settings group."""
        file_bed_group = Adw.PreferencesGroup()
        file_bed_group.set_title("File Bed")
        file_bed_group.set_description("External service for uploading images")
        self.add(file_bed_group)
        
        # File bed enabled
        self._file_bed_enabled_switch = self._create_pref_switch("Enable File Bed", False)
        file_bed_group.add(self._file_bed_enabled_switch)
        
        # Upload URL
        self._file_bed_url_row = Adw.EntryRow()
        self._file_bed_url_row.set_title("Upload URL")
        self._file_bed_url_row.set_show_apply_button(True)
        self._file_bed_url_row.set_sensitive(False)  # Only enabled when file bed is enabled
        file_bed_group.add(self._file_bed_url_row)
        
        # API key
        self._file_bed_key_row = Adw.PasswordEntryRow()
        self._file_bed_key_row.set_title("API Key")
        self._file_bed_key_row.set_show_apply_button(True)
        self._file_bed_key_row.set_sensitive(False)  # Only enabled when file bed is enabled
        file_bed_group.add(self._file_bed_key_row)
        
        # Connect file bed switch to enable/disable rows
        self._file_bed_enabled_switch.connect('notify::active', self._on_file_bed_toggle)
    
    def _create_advanced_group(self):
        """Create the advanced settings group."""
        advanced_group = Adw.PreferencesGroup()
        advanced_group.set_title("Advanced")
        self.add(advanced_group)
        
        # Stream timeout
        self._timeout_row = Adw.SpinRow.new_with_range(60, 3600, 1)
        self._timeout_row.set_title("Stream Timeout (seconds)")
        advanced_group.add(self._timeout_row)
        
        # API key
        self._api_key_row = Adw.PasswordEntryRow()
        self._api_key_row.set_title("API Key (Optional)")
        self._api_key_row.set_subtitle("Require API key for authentication")
        self._api_key_row.set_show_apply_button(True)
        advanced_group.add(self._api_key_row)
        
        # Server port
        self._port_row = Adw.SpinRow.new_with_range(1, 65535, 1)
        self._port_row.set_title("Server Port")
        self._port_row.set_subtitle("Port for the API server to listen on")
        advanced_group.add(self._port_row)
    
    def _create_action_bar(self):
        """Create the action bar with save/reload buttons."""
        # Create a box for the action bar
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action_box.set_halign(Gtk.Align.END)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        action_box.set_margin_start(12)
        action_box.set_margin_end(12)
        
        # Reload button
        reload_btn = Gtk.Button(label="Reload")
        reload_btn.add_css_class("flat")
        reload_btn.connect("clicked", self.load_config)
        action_box.append(reload_btn)
        
        # Save button
        save_btn = Gtk.Button(label="Save Configuration")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self.save_config)
        action_box.append(save_btn)
        
        # Add the action bar to the main box
        self.set_header_suffix(action_box)
    
    def _create_pref_switch(self, title: str, default: bool) -> Adw.SwitchRow:
        """Create a preference switch row."""
        switch_row = Adw.SwitchRow()
        switch_row.set_title(title)
        switch_row.set_active(default)
        return switch_row
    
    def _on_mode_changed(self, combo, _):
        """Handle mode selection change."""
        selected = combo.get_selected()
        is_battle = selected == 1  # "Battle" is the second option
        
        # Enable/disable battle target based on mode
        self._battle_target_combo.set_sensitive(is_battle)
    
    def _on_file_bed_toggle(self, switch, _):
        """Handle file bed toggle change."""
        enabled = switch.get_active()
        
        # Enable/disable file bed fields
        self._file_bed_url_row.set_sensitive(enabled)
        self._file_bed_key_row.set_sensitive(enabled)
    
    def load_config(self, button=None):
        """Load configuration from the backend API."""
        def on_config_loaded(config_data, error):
            if error:
                logger.error(f"Error loading config: {error}")
                # Show error in main thread
                def show_error():
                    show_error_async(None, f"Failed to load configuration: {error}")
                GLib.idle_add(show_error)
                return
            
            # Update UI with config values
            def update_ui():
                self._current_config = config_data
                
                # Session settings
                self._session_row.set_text(config_data.get("session_id", ""))
                self._message_row.set_text(config_data.get("message_id", ""))
                
                # Operation mode
                mode = config_data.get("id_updater_last_mode", "direct_chat")
                self._mode_combo.set_selected(1 if mode == "battle" else 0)
                
                battle_target = config_data.get("id_updater_battle_target", "A")
                self._battle_target_combo.set_selected(1 if battle_target == "B" else 0)
                
                # Features
                self._auto_update_switch.set_active(config_data.get("enable_auto_update", True))
                self._bypass_switch.set_active(config_data.get("bypass_enabled", True))
                self._tavern_switch.set_active(config_data.get("tavern_mode_enabled", False))
                
                # File bed
                self._file_bed_enabled_switch.set_active(config_data.get("file_bed_enabled", False))
                self._file_bed_url_row.set_text(config_data.get("file_bed_upload_url", ""))
                self._file_bed_key_row.set_text(config_data.get("file_bed_api_key", ""))
                
                # Advanced
                self._timeout_row.set_value(config_data.get("stream_response_timeout_seconds", 360))
                self._api_key_row.set_text(config_data.get("api_key", ""))
                self._port_row.set_value(config_data.get("server_port", 5102))
                
                # Update dependent UI elements
                self._on_file_bed_toggle(self._file_bed_enabled_switch, None)
                self._on_mode_changed(self._mode_combo, None)
                
                # Emit signal
                self.emit("config-loaded")
                
                logger.info("Configuration loaded successfully")
            
            GLib.idle_add(update_ui)
        
        # Call the API to get current config
        self.http_client.get("/internal/config", on_config_loaded)
    
    def save_config(self, button):
        """Save configuration back to the backend API."""
        # Collect configuration values from UI
        new_config = {
            "session_id": self._session_row.get_text(),
            "message_id": self._message_row.get_text(),
            "id_updater_last_mode": "battle" if self._mode_combo.get_selected() == 1 else "direct_chat",
            "id_updater_battle_target": "B" if self._battle_target_combo.get_selected() == 1 else "A",
            "enable_auto_update": self._auto_update_switch.get_active(),
            "bypass_enabled": self._bypass_switch.get_active(),
            "tavern_mode_enabled": self._tavern_switch.get_active(),
            "file_bed_enabled": self._file_bed_enabled_switch.get_active(),
            "file_bed_upload_url": self._file_bed_url_row.get_text(),
            "file_bed_api_key": self._file_bed_key_row.get_text(),
            "stream_response_timeout_seconds": int(self._timeout_row.get_value()),
            "api_key": self._api_key_row.get_text(),
            "server_port": int(self._port_row.get_value()),
        }
        
        def on_save_complete(success, error):
            if success:
                def show_success():
                    show_info_async(None, "Configuration saved successfully!")
                    self.emit("config-saved")
                    logger.info("Configuration saved successfully")
                GLib.idle_add(show_success)
            else:
                def show_error():
                    show_error_async(None, f"Failed to save configuration: {error}")
                GLib.idle_add(show_error)
        
        # For now, we'll update the local config file directly
        # In a real implementation, we would send this to the backend API
        def _save():
            success = update_config_partial(new_config)
            GLib.idle_add(on_save_complete, success, None if success else "Unknown error")
        
        save_thread = threading.Thread(target=_save, daemon=True)
        save_thread.start()
    
    def validate_config(self) -> bool:
        """Validate the current configuration values."""
        errors = []
        
        # Validate session IDs (if not default values)
        session_id = self._session_row.get_text()
        if session_id and session_id != "YOUR_SESSION_ID" and not self._is_valid_uuid(session_id):
            errors.append("Session ID is not a valid UUID")
        
        message_id = self._message_row.get_text()
        if message_id and message_id != "YOUR_MESSAGE_ID" and not self._is_valid_uuid(message_id):
            errors.append("Message ID is not a valid UUID")
        
        # Validate port
        port = int(self._port_row.get_value())
        if not (1 <= port <= 65535):
            errors.append("Port must be between 1 and 65535")
        
        # Validate timeout
        timeout = int(self._timeout_row.get_value())
        if timeout < 1:
            errors.append("Stream timeout must be positive")
        
        # Show validation errors if any
        if errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(f"• {e}" for e in errors)
            show_error_async(None, error_msg)
            return False
        
        return True
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Check if a string is a valid UUID."""
        import uuid
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False