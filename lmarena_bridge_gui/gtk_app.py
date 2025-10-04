"""
Main entry point for the LMArena Bridge GTK4 GUI application.
"""

import sys
import logging
import signal
from gi.repository import Gtk, Adw, Gio

from .ui.main_window import MainWindow
from .utils.http_client import shutdown_gui_http_client
from .utils.notifications import NotificationManager
from .ui.log_viewer import LogViewer

# Initialize logging first
from ..logging_config import setup_logging
setup_logging(debug=False)


class LMArenaBridgeApplication(Adw.Application):
    """
    Main GTK4 application class for LMArena Bridge.
    """
    
    def __init__(self):
        super().__init__(
            application_id="com.lmarena.bridge",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.window = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def do_activate(self):
        """Create and show the main application window."""
        self.window = MainWindow(self)
        self.window.present()
    
    def do_startup(self):
        """Application startup tasks."""
        Adw.Application.do_startup(self)
        
        # Create actions for the application menu
        self._setup_actions()
    
    def _setup_actions(self):
        """Setup application actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)
        
        # New window action
        new_window_action = Gio.SimpleAction.new("new-window", None)
        new_window_action.connect("activate", self._on_new_window)
        self.add_action(new_window_action)
        
        # Add accelerators
        self.set_accels_for_action("app.quit", ["<primary>q"])
        self.set_accels_for_action("win.setup-wizard", ["<primary>s"])
        self.set_accels_for_action("win.show-logs", ["<primary>l"])
    
    def _on_quit(self, action, parameter):
        """Handle quit action."""
        self.quit()
    
    def _on_new_window(self, action, parameter):
        """Handle new window action."""
        if self.window:
            # Create a new window (for now, just present the existing one)
            self.window.present()
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.quit()
    
    def do_shutdown(self):
        """Application shutdown tasks."""
        logging.info("Shutting down LMArena Bridge GUI...")
        
        # Shutdown HTTP client
        shutdown_gui_http_client()
        
        # Call parent shutdown
        Adw.Application.do_shutdown(self)


def main():
    """Main entry point for the GTK application."""
    # Set up logging
    setup_logging(debug=False)
    
    # Create and run the application
    app = LMArenaBridgeApplication()
    
    # Add CSS for styling (optional)
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(
        b"""
        /* Custom styling for the application */
        .success {
            color: #4CAF50;
        }
        
        .error {
            color: #F44336;
        }
        
        .warning {
            color: #FF9800;
        }
        
        .user-message {
            background-color: #E3F2FD;
            padding: 8px;
            border-radius: 8px;
        }
        
        .assistant-message {
            background-color: #F5F5F5;
            padding: 8px;
            border-radius: 8px;
        }
        
        .system-message {
            background-color: #FFF3E0;
            padding: 8px;
            border-radius: 8px;
            font-style: italic;
        }
        
        .navigation-sidebar {
            border-right: 1px solid @borders;
        }
        """
    )
    
    # Import Gdk here to avoid issues
    from gi.repository import Gdk
    
    # Apply the CSS provider to the default display
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    
    try:
        exit_code = app.run(sys.argv)
        return exit_code
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        logging.error(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())