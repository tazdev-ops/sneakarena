"""
Main window for the LMArena Bridge GTK4 GUI application.
"""

import logging
import sys
import threading
from typing import Optional
from gi.repository import Gtk, Adw, Gio, GLib, GObject

from .setup_wizard import show_setup_wizard
from .chat_playground import ChatPlayground
from .config_editor import ConfigEditor
from .model_manager import ModelManager
from .endpoint_mapper import EndpointMapper
from .log_viewer import LogViewer
from ..utils.http_client import get_gui_http_client
from ..utils.notifications import show_error_async, show_info_async
from .widgets import ServerControlBar, StatusIndicator

logger = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    """
    Main application window for the LMArena Bridge GUI.
    """
    
    def __init__(self, app):
        super().__init__(application=app)
        
        self.app = app
        self.http_client = get_gui_http_client()
        
        self.set_title("LMArena Bridge")
        self.set_default_size(1000, 700)
        
        # Create the main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # Create header bar
        self._create_header_bar()
        main_box.append(self._header_bar)
        
        # Create server control bar
        self._server_control = ServerControlBar()
        self._server_control.connect("start-server", self._on_start_server)
        self._server_control.connect("stop-server", self._on_stop_server)
        main_box.append(self._server_control)
        
        # Create the main content area with tabbed interface
        self._create_content_area()
        main_box.append(self._content_area)
        
        # Create status bar
        self._create_status_bar()
        main_box.append(self._status_bar)
        
        # Initialize connection status
        self._is_server_running = False
        self._last_status_check = 0
        
        # Check server status periodically
        GLib.timeout_add(5000, self._check_server_status)  # Check every 5 seconds
        
        # Show initial setup wizard if needed
        self._show_setup_wizard_if_needed()
    
    def _create_header_bar(self):
        """Create the header bar with menu and actions."""
        self._header_bar = Adw.HeaderBar()
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic")
        menu_button.set_child(menu_icon)
        
        # Create menu model
        menu_model = Gio.Menu()
        
        # File section
        file_section = Gio.Menu()
        file_section.append("New Window", "win.new-window")
        file_section.append("Preferences", "win.preferences")
        file_section.append("Quit", "app.quit")
        menu_model.append_section(None, file_section)
        
        # Tools section
        tools_section = Gio.Menu()
        tools_section.append("Setup Wizard", "win.setup-wizard")
        tools_section.append("Logs", "win.show-logs")
        menu_model.append_section(None, tools_section)
        
        # Help section
        help_section = Gio.Menu()
        help_section.append("About", "win.about")
        help_section.append("Documentation", "win.documentation")
        menu_model.append_section(None, help_section)
        
        menu_button.set_menu_model(menu_model)
        self._header_bar.pack_end(menu_button)
        
        # Add window actions
        self._add_window_actions()
    
    def _add_window_actions(self):
        """Add window-specific actions."""
        action_group = Gio.SimpleActionGroup()
        self.insert_action_group("win", action_group)
        
        # Setup wizard action
        setup_action = Gio.SimpleAction.new("setup-wizard", None)
        setup_action.connect("activate", self._on_setup_wizard)
        action_group.add_action(setup_action)
        
        # Show logs action
        logs_action = Gio.SimpleAction.new("show-logs", None)
        logs_action.connect("activate", self._on_show_logs)
        action_group.add_action(logs_action)
        
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        action_group.add_action(about_action)
        
        # Documentation action
        docs_action = Gio.SimpleAction.new("documentation", None)
        docs_action.connect("activate", self._on_documentation)
        action_group.add_action(docs_action)
        
        # Preferences action
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        action_group.add_action(prefs_action)
    
    def _create_content_area(self):
        """Create the main content area with tabbed interface."""
        # Create a leaflet for responsive layout, or a simple stack
        self._content_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        # Create the navigation sidebar
        sidebar = self._create_sidebar()
        self._content_area.append(sidebar)
        
        # Create the main content stack
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        
        # Create pages
        self._chat_page = ChatPlayground(self.http_client)
        self._config_page = ConfigEditor(self.http_client)
        self._models_page = ModelManager(self.http_client)
        self._mapper_page = EndpointMapper(self.http_client)
        self._logs_page = LogViewer()
        
        # Add pages to stack
        self._stack.add_titled(self._chat_page, "chat", "Chat")
        self._stack.add_titled(self._config_page, "config", "Configuration")
        self._stack.add_titled(self._models_page, "models", "Models")
        self._stack.add_titled(self._mapper_page, "mapper", "Endpoint Map")
        self._stack.add_titled(self._logs_page, "logs", "Logs")
        
        # Attach log viewer to the logger
        self._logs_page.attach_to_logger()
        
        # Add to content area
        self._content_area.append(self._stack)
        
        # Add stack switcher
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self._stack)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        
        # Add switcher to header bar
        self._header_bar.set_title_widget(stack_switcher)
    
    def _create_sidebar(self):
        """Create the navigation sidebar."""
        list_box = Gtk.ListBox()
        list_box.add_css_class("navigation-sidebar")
        
        # Add rows for each page
        pages = [
            ("chat", "Chat", "dialog-messages-symbolic"),
            ("config", "Configuration", "preferences-system-symbolic"),
            ("models", "Models", "applications-science-symbolic"),
            ("mapper", "Endpoint Map", "network-server-symbolic"),
            ("logs", "Logs", "document-open-recent-symbolic")
        ]
        
        for page_id, title, icon in pages:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_icon_name(icon)
            row.set_action_name(f"stack.switcher")
            row.set_action_target_value(GLib.Variant.new_string(page_id))
            
            list_box.append(row)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(list_box)
        scrolled.set_vexpand(True)
        scrolled.set_max_content_width(200)
        
        return scrolled
    
    def _create_status_bar(self):
        """Create the status bar."""
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._status_bar.set_margin_start(12)
        self._status_bar.set_margin_end(12)
        self._status_bar.set_margin_top(6)
        self._status_bar.set_margin_bottom(6)
        
        # Connection status indicator
        self._status_indicator = StatusIndicator()
        self._status_bar.append(self._status_indicator)
        
        # Server status
        self._server_status_label = Gtk.Label()
        self._server_status_label.set_text("Server: Unknown")
        self._status_bar.append(self._server_status_label)
        
        # Clients count
        self._clients_label = Gtk.Label()
        self._clients_label.set_text("Clients: 0")
        self._status_bar.append(self._clients_label)
        
        # Add stretch to push content to the sides
        stretch = Gtk.Box()
        stretch.set_hexpand(True)
        self._status_bar.append(stretch)
    
    def _show_setup_wizard_if_needed(self):
        """Show the setup wizard on first run."""
        # For now, always show if no config exists
        # In the future, this could be based on a first-run flag
        from ...settings import CONFIG_DIR
        config_file = CONFIG_DIR / "config.jsonc"
        
        if not config_file.exists():
            self._show_setup_wizard()
        else:
            # Check if basic config is done (has real session IDs)
            from ...settings import load_settings
            settings = load_settings()
            if settings.session_id == "YOUR_SESSION_ID" or settings.message_id == "YOUR_MESSAGE_ID":
                self._show_setup_wizard()
    
    def _show_setup_wizard(self):
        """Show the setup wizard."""
        wizard = show_setup_wizard(self)
        wizard.present()
    
    def _on_setup_wizard(self, action, parameter):
        """Handle setup wizard action."""
        self._show_setup_wizard()
    
    def _on_show_logs(self, action, parameter):
        """Handle show logs action."""
        log_window = Gtk.Window()
        log_window.set_title("Application Logs")
        log_window.set_default_size(800, 600)
        log_window.set_transient_for(self)
        
        log_viewer = LogViewer()
        log_viewer.attach_to_logger()
        log_window.set_content(log_viewer)
        
        log_window.present()
    
    def _on_about(self, action, parameter):
        """Handle about action."""
        about = Adw.AboutWindow(
            transient_for=self,
            application_name="LMArena Bridge",
            application_icon="application-x-executable",  # We'll set the correct icon later
            developer_name="LMArena Bridge Team",
            version="3.0.0",
            developers=["You"],
            copyright="© 2024 LMArena Bridge Team"
        )
        about.present()
    
    def _on_documentation(self, action, parameter):
        """Handle documentation action."""
        import webbrowser
        webbrowser.open("https://github.com/Lianues/LMArenaBridge")
    
    def _on_preferences(self, action, parameter):
        """Handle preferences action."""
        self._stack.set_visible_child_name("config")
    
    def _on_start_server(self, control_bar):
        """Handle start server button click."""
        # In a real implementation, this would start the actual server
        # For now, we'll simulate server starting
        
        def simulate_start():
            def update_ui():
                self._server_control.update_server_status(True)
                self._server_status_label.set_text("Server: Running")
                self._status_indicator.update_status("Connected", True)
                show_info_async(self, "Server started successfully")
            
            # Simulate startup time
            import time
            time.sleep(1)
            GLib.idle_add(update_ui)
        
        start_thread = threading.Thread(target=simulate_start, daemon=True)
        start_thread.start()
    
    def _on_stop_server(self, control_bar):
        """Handle stop server button click."""
        # In a real implementation, this would stop the actual server
        # For now, we'll simulate server stopping
        
        def simulate_stop():
            def update_ui():
                self._server_control.update_server_status(False)
                self._server_status_label.set_text("Server: Stopped")
                self._status_indicator.update_status("Disconnected", False)
                show_info_async(self, "Server stopped")
            
            # Simulate shutdown time
            import time
            time.sleep(0.5)
            GLib.idle_add(update_ui)
        
        stop_thread = threading.Thread(target=simulate_stop, daemon=True)
        stop_thread.start()
    
    def _check_server_status(self):
        """Periodically check the server status."""
        def on_health_check(healthy, error):
            def update_status():
                if healthy:
                    self._status_indicator.update_status("Connected", True)
                    self._server_status_label.set_text("Server: Running")
                    self._server_control.update_server_status(True)
                else:
                    self._status_indicator.update_status("Disconnected", False)
                    self._server_status_label.set_text("Server: Stopped")
                    self._server_control.update_server_status(False)
            
            GLib.idle_add(update_status)
        
        # Check server health
        self.http_client.health_check(on_health_check)
        
        # Continue the periodic check (return True to repeat)
        return True