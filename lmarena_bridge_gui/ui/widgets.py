"""
Custom GTK4 widgets for the LMArena Bridge GUI.
Provides reusable UI components for the application.
"""

import logging
from typing import Optional, Callable, Any
from gi.repository import Gtk, Adw, GObject, Pango, Gio

logger = logging.getLogger(__name__)


class StatusIndicator(Adw.Bin):
    """
    A custom status indicator widget showing connection status.
    """

    # Template children (if we had a UI file)
    # status_label = Gtk.Template.Child()
    # status_icon = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        
        # Create the indicator
        self._status = "disconnected"
        self._connected = False
        
        # Main container
        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_child(self._box)
        
        # Status icon
        self._icon = Gtk.Image()
        self._icon.set_icon_name("network-offline-symbolic")  # Default to offline
        self._icon.set_pixel_size(16)
        self._box.append(self._icon)
        
        # Status label
        self._label = Gtk.Label()
        self._label.set_text("Disconnected")
        self._label.set_halign(Gtk.Align.START)
        self._box.append(self._label)
        
        self.update_status("disconnected", False)
    
    def update_status(self, status_text: str, connected: bool):
        """Update the status indicator."""
        self._status = status_text
        self._connected = connected
        
        # Update icon and label
        if connected:
            self._icon.set_icon_name("network-wired-symbolic")
            self._icon.set_css_classes(["success"])
        else:
            self._icon.set_icon_name("network-offline-symbolic")
            self._icon.set_css_classes(["error"])
        
        self._label.set_text(status_text)
    
    @property
    def connected(self) -> bool:
        """Get connection status."""
        return self._connected


class ModelComboBox(Gtk.Box):
    """
    A custom combo box for selecting models from the backend.
    """
    
    def __init__(self, http_client):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.http_client = http_client
        
        # Create the combo box
        self._combo = Gtk.ComboBoxText()
        self._combo.set_hexpand(True)
        
        # Add loading option
        self._combo.append("", "Loading models...")
        self._combo.set_active_id("")
        
        # Refresh button
        self._refresh_button = Gtk.Button()
        icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        self._refresh_button.set_child(icon)
        self._refresh_button.set_tooltip_text("Refresh models")
        
        # Add to container
        self.append(self._combo)
        self.append(self._refresh_button)
        
        # Connect refresh button
        self._refresh_button.connect("clicked", self._on_refresh_clicked)
        
        # Load models initially
        self.load_models()
    
    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        self.load_models()
    
    def load_models(self):
        """Load models from the backend API."""
        def on_models_loaded(models_data, error):
            if error:
                logger.error(f"Error loading models: {error}")
                self._combo.remove_all()
                self._combo.append("", "Error loading models")
                self._combo.set_active_id("")
                return
            
            # Clear existing models
            self._combo.remove_all()
            
            if models_data and "data" in models_data:
                for model in models_data["data"]:
                    model_id = model.get("id", "")
                    self._combo.append(model_id, model_id)
                
                # Set first model as active if any exist
                if models_data["data"]:
                    first_model_id = models_data["data"][0].get("id", "")
                    self._combo.set_active_id(first_model_id)
                else:
                    self._combo.append("", "No models available")
            else:
                self._combo.append("", "No models returned")
        
        # Call the API to get models
        self.http_client.get("/v1/models", on_models_loaded)
    
    def get_active_model(self) -> Optional[str]:
        """Get the currently selected model ID."""
        return self._combo.get_active_id()
    
    def set_active_model(self, model_id: str):
        """Set the active model."""
        self._combo.set_active_id(model_id)


class ChatMessageView(Gtk.ScrolledWindow):
    """
    A custom view for displaying chat messages.
    """
    
    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Create a vertical box to hold messages
        self._message_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._message_container.set_margin_start(10)
        self._message_container.set_margin_end(10)
        self._message_container.set_margin_top(10)
        self._message_container.set_margin_bottom(10)
        
        # Create an adapter for the box
        adjustment = Gtk.Adjustment()
        self._message_container.set_vadjustment(adjustment)
        
        self.set_child(self._message_container)
        
        self._messages = []
    
    def add_message(self, role: str, content: str):
        """Add a message to the chat view."""
        message_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        message_box.set_hexpand(True)
        
        # Role label
        role_label = Gtk.Label()
        role_label.set_text(f"{role.upper()}:")
        role_label.set_halign(Gtk.Align.START)
        role_label.set_css_classes(["heading"])
        
        # Message content
        content_label = Gtk.Label()
        content_label.set_text(content)
        content_label.set_halign(Gtk.Align.START)
        content_label.set_wrap(True)
        content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content_label.set_selectable(True)
        content_label.set_xalign(0.0)
        
        # Style based on role
        if role.lower() == "user":
            content_label.set_css_classes(["user-message"])
        elif role.lower() == "assistant":
            content_label.set_css_classes(["assistant-message"])
        else:
            content_label.set_css_classes(["system-message"])
        
        message_box.append(role_label)
        message_box.append(content_label)
        
        self._message_container.append(message_box)
        self._messages.append({"role": role, "content": content})
        
        # Scroll to bottom
        vadj = self.get_vadjustment()
        vadj.set_value(vadj.get_upper())
    
    def clear_messages(self):
        """Clear all messages from the view."""
        for child in self._message_container.get_children():
            self._message_container.remove(child)
        self._messages.clear()


class ServerControlBar(Gtk.Box):
    """
    A control bar with start/stop server buttons and status indicator.
    """
    
    __gsignals__ = {
        'start-server': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'stop-server': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        
        # Start button
        self._start_button = Gtk.Button(label="Start Server")
        self._start_button.add_css_class("suggested-action")
        self._start_button.connect("clicked", self._on_start_clicked)
        self.append(self._start_button)
        
        # Stop button
        self._stop_button = Gtk.Button(label="Stop Server")
        self._stop_button.add_css_class("destructive-action")
        self._stop_button.set_sensitive(False)  # Disabled by default
        self._stop_button.connect("clicked", self._on_stop_clicked)
        self.append(self._stop_button)
        
        # Status indicator
        self._status_label = Gtk.Label()
        self._status_label.set_text("Server: Stopped")
        self.append(self._status_label)
    
    def _on_start_clicked(self, button):
        """Handle start button click."""
        self.emit("start-server")
    
    def _on_stop_clicked(self, button):
        """Handle stop button click."""
        self.emit("stop-server")
    
    def update_server_status(self, is_running: bool):
        """Update the server status display."""
        self._start_button.set_sensitive(not is_running)
        self._stop_button.set_sensitive(is_running)
        
        if is_running:
            self._status_label.set_text("Server: Running")
            self._status_label.set_css_classes(["success"])
        else:
            self._status_label.set_text("Server: Stopped")
            self._status_label.set_css_classes(["error"])


class ExpandableSection(Adw.PreferencesGroup):
    """
    An expandable section for the preferences window.
    """
    
    def __init__(self, title: str, description: str = ""):
        super().__init__()
        self.set_title(title)
        if description:
            self.set_description(description)
        
        # Create the expander
        self._expander = Adw.ExpanderRow()
        self.add(self._expander)
    
    def add_row(self, widget):
        """Add a widget as a row in the expander."""
        self._expander.add_row(widget)
    
    def set_expanded(self, expanded: bool):
        """Set whether the section is expanded."""
        self._expander.set_expanded(expanded)
    
    def get_expanded(self) -> bool:
        """Get whether the section is expanded."""
        return self._expander.get_expanded()


class FileChooserButton(Gtk.Box):
    """
    A button that opens a file chooser dialog.
    """
    
    __gsignals__ = {
        'file-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, title: str = "Select File", file_filter: Optional[Gtk.FileFilter] = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self._title = title
        self._file_filter = file_filter
        
        # Create button
        self._button = Gtk.Button()
        icon = Gtk.Image.new_from_icon_name("document-open-symbolic")
        self._button.set_child(icon)
        self._button.set_tooltip_text("Select file")
        self._button.connect("clicked", self._on_clicked)
        
        # Create label to show selected file
        self._label = Gtk.Label()
        self._label.set_text("No file selected")
        self._label.set_hexpand(True)
        self._label.set_halign(Gtk.Align.START)
        self._label.set_ellipsize(Pango.EllipsizeMode.END)
        
        self.append(self._button)
        self.append(self._label)
    
    def _on_clicked(self, button):
        """Handle button click to open file chooser."""
        dialog = Gtk.FileChooserNative.new(
            self._title,
            None,  # parent window
            Gtk.FileChooserAction.OPEN,
            "Select",
            "Cancel"
        )
        
        if self._file_filter:
            dialog.add_filter(self._file_filter)
        
        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                filename = dialog.get_file().get_path()
                self._label.set_text(filename)
                self.emit("file-selected", filename)
        
        dialog.connect("response", on_response)
        dialog.show()
    
    def get_filename(self) -> Optional[str]:
        """Get the selected filename."""
        text = self._label.get_text()
        if text == "No file selected":
            return None
        return text