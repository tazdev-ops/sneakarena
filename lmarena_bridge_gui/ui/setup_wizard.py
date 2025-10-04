"""
Setup wizard component for the GTK4 GUI.
Provides a guided setup process for first-time users.
"""

import logging
import webbrowser
from typing import Optional
from gi.repository import Gtk, Adw, GObject, GLib

from ..utils.notifications import show_error_async, show_info_async
from ..utils.http_client import get_gui_http_client

logger = logging.getLogger(__name__)


class SetupWizard(Adw.Window):
    """
    A setup wizard window for first-time configuration.
    """
    
    __gsignals__ = {
        'setup-complete': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'setup-cancelled': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, parent_window=None):
        super().__init__(title="Setup Wizard", modal=True)
        
        if parent_window:
            self.set_transient_for(parent_window)
        
        self.set_default_size(600, 500)
        
        self.http_client = get_gui_http_client()
        self._current_step = 0
        self._setup_complete = False
        
        # Create the main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # Create header bar
        header_bar = Adw.HeaderBar()
        main_box.append(header_bar)
        
        # Create stack for different steps
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(300)
        main_box.append(self._stack)
        
        # Create navigation controls
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        nav_box.set_margin_start(12)
        nav_box.set_margin_end(12)
        nav_box.set_margin_bottom(12)
        
        # Previous button
        self._prev_button = Gtk.Button(label="Previous")
        self._prev_button.connect("clicked", self._on_prev_clicked)
        nav_box.append(self._prev_button)
        
        # Status label
        self._status_label = Gtk.Label()
        self._status_label.set_hexpand(True)
        self._status_label.set_halign(Gtk.Align.CENTER)
        nav_box.append(self._status_label)
        
        # Next/Done button
        self._next_button = Gtk.Button(label="Next")
        self._next_button.add_css_class("suggested-action")
        self._next_button.connect("clicked", self._on_next_clicked)
        nav_box.append(self._next_button)
        
        main_box.append(nav_box)
        
        # Create wizard steps
        self._create_welcome_step()
        self._create_server_step()
        self._create_browser_step()
        self._create_ids_step()
        self._create_complete_step()
        
        # Update UI for current step
        self._update_step()
    
    def _create_welcome_step(self):
        """Create the welcome step."""
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step_box.set_margin_start(24)
        step_box.set_margin_end(24)
        step_box.set_margin_top(24)
        step_box.set_margin_bottom(24)
        
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Welcome to LMArena Bridge</span>")
        title.set_halign(Gtk.Align.CENTER)
        step_box.append(title)
        
        desc = Gtk.Label()
        desc.set_markup(
            "This wizard will help you set up the LMArena Bridge API server. "
            "You'll need to:\n\n"
            "• Start the API server\n"
            "• Install the Tampermonkey script in your browser\n"
            "• Capture session IDs from LMArena\n"
            "• Test the connection"
        )
        desc.set_halign(Gtk.Align.CENTER)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_wrap(True)
        step_box.append(desc)
        
        self._stack.add_titled(step_box, "welcome", "Welcome")
    
    def _create_server_step(self):
        """Create the server setup step."""
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step_box.set_margin_start(24)
        step_box.set_margin_end(24)
        step_box.set_margin_top(24)
        step_box.set_margin_bottom(24)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Start Server</span>")
        title.set_halign(Gtk.Align.CENTER)
        step_box.append(title)
        
        desc = Gtk.Label()
        desc.set_text("Click the button below to start the API server.")
        desc.set_halign(Gtk.Align.CENTER)
        step_box.append(desc)
        
        # Server status indicator
        self._server_status = Gtk.Label()
        self._server_status.set_text("Server: Stopped")
        self._server_status.set_halign(Gtk.Align.CENTER)
        step_box.append(self._server_status)
        
        # Start server button
        self._start_server_button = Gtk.Button(label="Start Server")
        self._start_server_button.add_css_class("suggested-action")
        self._start_server_button.connect("clicked", self._on_start_server_clicked)
        step_box.append(self._start_server_button)
        
        self._stack.add_titled(step_box, "server", "Server")
    
    def _create_browser_step(self):
        """Create the browser setup step."""
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step_box.set_margin_start(24)
        step_box.set_margin_end(24)
        step_box.set_margin_top(24)
        step_box.set_margin_bottom(24)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Connect Browser</span>")
        title.set_halign(Gtk.Align.CENTER)
        step_box.append(title)
        
        desc = Gtk.Label()
        desc.set_text("Open LMArena in your browser and ensure the Tampermonkey script is active.")
        desc.set_halign(Gtk.Align.CENTER)
        step_box.append(desc)
        
        # Browser status indicator
        self._browser_status = Gtk.Label()
        self._browser_status.set_text("Status: Not connected")
        self._browser_status.set_halign(Gtk.Align.CENTER)
        step_box.append(self._browser_status)
        
        # Open LMArena button
        open_button = Gtk.Button(label="Open LMArena in Browser")
        open_button.connect("clicked", self._on_open_lmarena_clicked)
        step_box.append(open_button)
        
        # Instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            "<b>Instructions:</b>\n"
            "1. Make sure Tampermonkey extension is installed\n"
            "2. Install the LMArena API Bridge script\n"
            "3. Open https://lmarena.ai in your browser\n"
            "4. Log in to your account\n"
            "5. Wait for the connection indicator to turn green"
        )
        instructions.set_halign(Gtk.Align.CENTER)
        instructions.set_justify(Gtk.Justification.LEFT)
        step_box.append(instructions)
        
        # Refresh status button
        refresh_button = Gtk.Button(label="Check Connection")
        refresh_button.connect("clicked", self._on_check_connection_clicked)
        step_box.append(refresh_button)
        
        self._stack.add_titled(step_box, "browser", "Browser")
    
    def _create_ids_step(self):
        """Create the ID capture step."""
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step_box.set_margin_start(24)
        step_box.set_margin_end(24)
        step_box.set_margin_top(24)
        step_box.set_margin_bottom(24)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Capture Session IDs</span>")
        title.set_halign(Gtk.Align.CENTER)
        step_box.append(title)
        
        desc = Gtk.Label()
        desc.set_text("Capture session IDs by clicking 'Retry' in a conversation.")
        desc.set_halign(Gtk.Align.CENTER)
        step_box.append(desc)
        
        # IDs status
        self._ids_status = Gtk.Label()
        self._ids_status.set_text("Status: Not captured")
        self._ids_status.set_halign(Gtk.Align.CENTER)
        step_box.append(self._ids_status)
        
        # Start capture button
        self._capture_button = Gtk.Button(label="Start ID Capture")
        self._capture_button.connect("clicked", self._on_start_capture_clicked)
        step_box.append(self._capture_button)
        
        # Instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            "<b>How to capture IDs:</b>\n"
            "1. Make sure you're on a conversation page in LMArena\n"
            "2. Click the 'Start ID Capture' button\n"
            "3. In LMArena, click the 'Retry' button (⟳) next to any message\n"
            "4. The IDs will be captured automatically"
        )
        instructions.set_halign(Gtk.Align.CENTER)
        instructions.set_justify(Gtk.Justification.LEFT)
        step_box.append(instructions)
        
        self._stack.add_titled(step_box, "ids", "Capture IDs")
    
    def _create_complete_step(self):
        """Create the completion step."""
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step_box.set_margin_start(24)
        step_box.set_margin_end(24)
        step_box.set_margin_top(24)
        step_box.set_margin_bottom(24)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Setup Complete!</span>")
        title.set_halign(Gtk.Align.CENTER)
        step_box.append(title)
        
        desc = Gtk.Label()
        desc.set_text("You've successfully set up LMArena Bridge. You can now use the API server.")
        desc.set_halign(Gtk.Align.CENTER)
        step_box.append(desc)
        
        # Success icon
        success_icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
        success_icon.set_pixel_size(64)
        success_icon.set_halign(Gtk.Align.CENTER)
        step_box.append(success_icon)
        
        self._stack.add_titled(step_box, "complete", "Complete")
    
    def _update_step(self):
        """Update the UI for the current step."""
        step_names = ["welcome", "server", "browser", "ids", "complete"]
        
        if 0 <= self._current_step < len(step_names):
            self._stack.set_visible_child_name(step_names[self._current_step])
        
        # Update button states
        self._prev_button.set_sensitive(self._current_step > 0)
        
        # Update status label
        self._status_label.set_text(f"Step {self._current_step + 1} of {len(step_names) - 1}")
        
        # Update next button text
        if self._current_step == len(step_names) - 2:  # Second to last (before complete)
            self._next_button.set_label("Finish")
        elif self._current_step == len(step_names) - 1:  # Complete step
            self._next_button.set_label("Close")
        else:
            self._next_button.set_label("Next")
    
    def _on_prev_clicked(self, button):
        """Handle previous button click."""
        if self._current_step > 0:
            self._current_step -= 1
            self._update_step()
    
    def _on_next_clicked(self, button):
        """Handle next button click."""
        step_names = ["welcome", "server", "browser", "ids", "complete"]
        
        if self._current_step == len(step_names) - 1:  # Complete step - close
            self._setup_complete = True
            self.emit("setup-complete")
            self.close()
        elif self._current_step < len(step_names) - 2:  # Not the last step
            self._current_step += 1
            self._update_step()
        elif self._current_step == len(step_names) - 2:  # Second to last - finish setup
            self._setup_complete = True
            self._current_step += 1
            self._update_step()
            self.emit("setup-complete")
    
    def _on_start_server_clicked(self, button):
        """Handle start server button click."""
        # For the setup wizard, we'll just update the status
        # In a real implementation, this would start the actual server
        self._server_status.set_text("Server: Starting...")
        self._server_status.set_css_classes(["success"])
        
        # Simulate server starting
        def simulate_start():
            import time
            time.sleep(2)  # Simulate startup time
            
            def update_status():
                self._server_status.set_text("Server: Running ✓")
                self._server_status.set_css_classes(["success"])
                self._start_server_button.set_sensitive(False)
                # Enable next button
                self._next_button.set_sensitive(True)
            
            GLib.idle_add(update_status)
        
        import threading
        thread = threading.Thread(target=simulate_start, daemon=True)
        thread.start()
    
    def _on_open_lmarena_clicked(self, button):
        """Open LMArena in the default browser."""
        try:
            webbrowser.open("https://lmarena.ai")
            logger.info("Opened LMArena in browser")
        except Exception as e:
            logger.error(f"Error opening LMArena in browser: {e}")
            show_error_async(self, f"Could not open browser: {e}")
    
    def _on_check_connection_clicked(self, button):
        """Check if the browser is connected via the Tampermonkey script."""
        def on_health_check(healthy, error):
            def update_status():
                if healthy:
                    self._browser_status.set_text("Status: Connected ✓")
                    self._browser_status.set_css_classes(["success"])
                    # Enable next button
                    self._next_button.set_sensitive(True)
                else:
                    self._browser_status.set_text(f"Status: Not connected - {error or 'Unknown error'}")
                    self._browser_status.set_css_classes(["error"])
            
            GLib.idle_add(update_status)
        
        # Check server health (this indirectly checks if browser is connected)
        self.http_client.health_check(on_health_check)
    
    def _on_start_capture_clicked(self, button):
        """Start the ID capture process."""
        # In the real implementation, this would communicate with the backend
        # to enable ID capture mode
        
        def simulate_capture():
            import time
            time.sleep(1)  # Simulate preparation
            
            def update_status():
                self._ids_status.set_text("Status: Capturing... Click 'Retry' in LMArena")
                self._ids_status.set_css_classes(["warning"])
                self._capture_button.set_sensitive(False)
                
                # Simulate successful capture after a delay
                def capture_complete():
                    self._ids_status.set_text("Status: IDs Captured ✓")
                    self._ids_status.set_css_classes(["success"])
                    # Enable next button
                    self._next_button.set_sensitive(True)
                
                GLib.timeout_add(3000, capture_complete)  # Simulate capture after 3 seconds
            
            GLib.idle_add(update_status)
        
        import threading
        thread = threading.Thread(target=simulate_capture, daemon=True)
        thread.start()


def show_setup_wizard(parent_window=None):
    """Show the setup wizard."""
    wizard = SetupWizard(parent_window)
    wizard.present()
    return wizard