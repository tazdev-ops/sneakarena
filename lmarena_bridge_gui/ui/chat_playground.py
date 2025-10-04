"""
Chat playground component for the GTK4 GUI.
Provides an interface for testing models interactively.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from gi.repository import Gtk, Adw, GObject, GLib, Gio, Pango

from ..utils.notifications import show_error_async, show_info_async
from .widgets import ModelComboBox, ChatMessageView
from ..utils.http_client import get_gui_http_client

logger = logging.getLogger(__name__)


class ChatPlayground(Adw.PreferencesPage):
    """
    A playground for testing chat completions interactively.
    """
    
    __gsignals__ = {
        'message-sent': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'response-received': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, http_client):
        super().__init__()
        self.set_title("Chat Playground")
        self.set_name("chat")
        
        self.http_client = http_client
        self._chat_history: List[Dict[str, str]] = []
        
        # Create the main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_child(main_box)
        
        # Create header with model selection
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        header_box.set_margin_top(12)
        
        # Model selection
        self._model_combo = ModelComboBox(self.http_client)
        self._model_combo.set_hexpand(True)
        header_box.append(self._model_combo)
        
        # Clear history button
        clear_btn = Gtk.Button(label="Clear History")
        clear_btn.add_css_class("flat")
        clear_btn.connect("clicked", self._on_clear_history)
        header_box.append(clear_btn)
        
        # Refresh models button
        refresh_btn = Gtk.Button()
        icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_child(icon)
        refresh_btn.set_tooltip_text("Refresh models")
        refresh_btn.connect("clicked", lambda btn: self._model_combo.load_models())
        header_box.append(refresh_btn)
        
        main_box.append(header_box)
        
        # Create chat display area
        self._chat_view = ChatMessageView()
        main_box.append(self._chat_view)
        
        # Create input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        input_box.set_margin_start(12)
        input_box.set_margin_end(12)
        input_box.set_margin_bottom(12)
        
        # System message entry
        self._system_entry = Gtk.Entry()
        self._system_entry.set_placeholder_text("System message (optional)...")
        input_box.append(self._system_entry)
        
        # User message entry
        self._message_entry = Gtk.TextView()
        self._message_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        self._message_entry.set_accepts_tab(False)  # Don't intercept tab for indentation
        
        # Add scroll to text view
        scrolled_text = Gtk.ScrolledWindow()
        scrolled_text.set_child(self._message_entry)
        scrolled_text.set_vexpand(True)
        scrolled_text.set_size_request(-1, 100)  # Set minimum height
        input_box.append(scrolled_text)
        
        # Send button
        self._send_button = Gtk.Button(label="Send")
        self._send_button.add_css_class("suggested-action")
        self._send_button.connect("clicked", self._on_send_clicked)
        
        # Add send button to a box to control positioning
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.append(self._send_button)
        button_box.set_halign(Gtk.Align.END)
        input_box.append(button_box)
        
        main_box.append(input_box)
        
        # Connect Enter key to send message
        self._message_entry.add_controller(Gtk.EventControllerKey.new())
        self._message_entry.get_controller(Gtk.EventController).connect("key-pressed", self._on_key_pressed)
    
    def _on_clear_history(self, button):
        """Handle clear history button click."""
        self._chat_history.clear()
        self._chat_view.clear_messages()
    
    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key press events in the message entry."""
        # Check if Ctrl+Enter was pressed
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval in [Gdk.KEY_Return, Gdk.KEY_KP_Enter]:
            self._on_send_clicked(None)
            return True  # Stop further processing
        
        # Check if Enter was pressed without Ctrl (to avoid submitting on single Enter)
        elif keyval in [Gdk.KEY_Return, Gdk.KEY_KP_Enter] and not (state & Gdk.ModifierType.CONTROL_MASK):
            # Don't submit on single Enter to allow multi-line input
            pass
    
    def _on_send_clicked(self, button):
        """Handle send button click."""
        # Get the message text
        buffer = self._message_entry.get_buffer()
        message = buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            False  # Don't include hidden characters
        ).strip()
        
        if not message:
            show_info_async(None, "Please enter a message to send")
            return
        
        # Get selected model
        model = self._model_combo.get_active_model()
        if not model:
            show_info_async(None, "Please select a model")
            return
        
        # Disable send button during request
        self._send_button.set_sensitive(False)
        self._send_button.set_label("Sending...")
        
        # Add user message to chat
        self._chat_history.append({"role": "user", "content": message})
        self._chat_view.add_message("user", message)
        
        # Clear the message entry
        buffer.set_text("", -1)
        
        # Prepare the API request
        system_message = self._system_entry.get_text().strip()
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Add chat history
        messages.extend(self._chat_history)
        
        request_data = {
            "model": model,
            "messages": messages,
            "stream": True  # Use streaming for real-time response
        }
        
        # Send the request to the API
        self._send_chat_request(request_data)
    
    def _send_chat_request(self, request_data: Dict[str, Any]):
        """Send the chat request to the backend API."""
        def on_response(response_data, error):
            # Re-enable the send button
            def enable_button():
                self._send_button.set_sensitive(True)
                self._send_button.set_label("Send")
            
            GLib.idle_add(enable_button)
            
            if error:
                logger.error(f"Chat request error: {error}")
                
                def show_error():
                    show_error_async(None, f"Error sending message: {error}")
                
                GLib.idle_add(show_error)
                return
            
            # In a real implementation, we would handle streaming responses
            # For now, we'll just add a placeholder response
            def add_response():
                self._chat_history.append({
                    "role": "assistant", 
                    "content": "This is a simulated response from the model."
                })
                self._chat_view.add_message("assistant", "This is a simulated response from the model.")
                self.emit("response-received", "This is a simulated response from the model.")
            
            GLib.idle_add(add_response)
        
        # For now, we'll just simulate the response
        # In a real implementation, we would make an HTTP request
        import threading
        import time
        
        def _simulate_response():
            time.sleep(2)  # Simulate network delay
            GLib.idle_add(on_response, {"content": "Simulated response"}, None)
        
        sim_thread = threading.Thread(target=_simulate_response, daemon=True)
        sim_thread.start()
        
        # This is where we would actually make the API call:
        # self.http_client.post("/v1/chat/completions", request_data, on_response)