"""
Log viewer component for the GTK4 GUI.
Displays application logs with filtering and search capabilities.
"""

import logging
import re
from typing import Optional, List
from gi.repository import Gtk, GObject, Pango, GLib, Gdk

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """
    Custom logging handler that emits signals when new log records are added.
    """
    
    def __init__(self, log_viewer):
        super().__init__()
        self.log_viewer = log_viewer
    
    def emit(self, record):
        """Emit the log record to the log viewer."""
        try:
            msg = self.format(record)
            GLib.idle_add(self.log_viewer._add_log_line, msg, record.levelname.lower())
        except Exception:
            self.handleError(record)


class LogViewer(Gtk.Box):
    """
    A log viewer widget that displays application logs with filtering capabilities.
    """
    
    __gsignals__ = {
        # Signal emitted when a log line is added
        'log-line-added': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),  # message, level
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        # Setup logging handler
        self._log_handler = LogHandler(self)
        self._log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Create the text view for logs
        self._text_buffer = Gtk.TextBuffer()
        self._text_view = Gtk.TextView(buffer=self._text_buffer)
        self._text_view.set_editable(False)
        self._text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self._text_view.set_monospace(True)
        
        # Create scrolled window for the text view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._text_view)
        self.append(scrolled)
        
        # Create filter controls
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls_box.set_margin_start(6)
        controls_box.set_margin_end(6)
        
        # Search entry
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search logs...")
        self._search_entry.connect("search-changed", self._on_search_changed)
        controls_box.append(self._search_entry)
        
        # Clear button
        clear_button = Gtk.Button(label="Clear")
        clear_button.connect("clicked", self._on_clear_clicked)
        controls_box.append(clear_button)
        
        # Filter dropdown
        self._filter_combo = Gtk.ComboBoxText()
        self._filter_combo.append("all", "All Levels")
        self._filter_combo.append("debug", "Debug")
        self._filter_combo.append("info", "Info")
        self._filter_combo.append("warning", "Warning")
        self._filter_combo.append("error", "Error")
        self._filter_combo.append("critical", "Critical")
        self._filter_combo.set_active_id("all")
        self._filter_combo.connect("changed", self._on_filter_changed)
        controls_box.append(self._filter_combo)
        
        self.append(controls_box)
        
        # Store all log lines for filtering
        self._all_log_lines = []
        self._filtered_log_lines = []
        
        # Set up text tags for different log levels
        self._setup_text_tags()
    
    def _setup_text_tags(self):
        """Setup text tags for different log levels."""
        # Debug: blue
        debug_tag = self._text_buffer.create_tag("debug", foreground="blue")
        
        # Info: green
        info_tag = self._text_buffer.create_tag("info", foreground="green")
        
        # Warning: orange
        warning_tag = self._text_buffer.create_tag("warning", foreground="orange")
        
        # Error: red
        error_tag = self._text_buffer.create_tag("error", foreground="red")
        
        # Critical: purple
        critical_tag = self._text_buffer.create_tag("critical", foreground="purple")
        
        # Timestamp: gray
        timestamp_tag = self._text_buffer.create_tag("timestamp", foreground="gray")
    
    def _add_log_line(self, message: str, level: str):
        """Add a log line to the viewer (called from logging handler)."""
        self._all_log_lines.append((message, level))
        
        # Check if this log should be displayed based on current filter
        current_filter = self._filter_combo.get_active_id()
        if current_filter == "all" or level == current_filter or (current_filter == "error" and level in ["error", "critical"]):
            # Check if search filter matches
            search_text = self._search_entry.get_text().lower()
            if not search_text or search_text in message.lower():
                self._insert_formatted_log_line(message, level)
        
        # Keep only the last 1000 lines to prevent memory issues
        if len(self._all_log_lines) > 1000:
            self._all_log_lines = self._all_log_lines[-750:]
    
    def _insert_formatted_log_line(self, message: str, level: str):
        """Insert a formatted log line into the text buffer."""
        # Get the end iter
        end_iter = self._text_buffer.get_end_iter()
        
        # Find timestamp part and format it
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', message)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            rest_of_message = message[len(timestamp):]
            
            # Insert timestamp with formatting
            self._text_buffer.insert_with_tags_by_name(end_iter, timestamp, "timestamp")
            
            # Insert the rest of the message with level formatting
            self._text_buffer.insert_with_tags_by_name(end_iter, rest_of_message, level)
        else:
            # Insert the whole message with level formatting
            self._text_buffer.insert_with_tags_by_name(end_iter, message, level)
        
        # Add a newline
        self._text_buffer.insert(end_iter, "\n")
        
        # Scroll to the end
        end_iter = self._text_buffer.get_end_iter()
        self._text_view.scroll_to_iter(end_iter, 0.0, True, 0.0, 1.0)
    
    def _on_search_changed(self, entry):
        """Handle search text changes."""
        self._apply_filters()
    
    def _on_filter_changed(self, combo):
        """Handle log level filter changes."""
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply both level and search filters to the logs."""
        self._text_buffer.set_text("")  # Clear the display
        
        search_text = self._search_entry.get_text().lower()
        level_filter = self._filter_combo.get_active_id()
        
        for message, level in self._all_log_lines:
            # Check level filter
            if level_filter != "all" and level_filter != level and not (level_filter == "error" and level in ["error", "critical"]):
                continue
            
            # Check search filter
            if search_text and search_text not in message.lower():
                continue
            
            # Add to display
            self._insert_formatted_log_line(message, level)
    
    def _on_clear_clicked(self, button):
        """Handle clear button click."""
        self._text_buffer.set_text("")
        self._all_log_lines.clear()
    
    def get_log_handler(self) -> LogHandler:
        """Get the logging handler for this log viewer."""
        return self._log_handler
    
    def attach_to_logger(self, logger_name: str = None):
        """Attach this log viewer to a logger (or root logger if none specified)."""
        if logger_name:
            log = logging.getLogger(logger_name)
        else:
            log = logging.getLogger()
        
        log.addHandler(self._log_handler)
    
    def detach_from_logger(self, logger_name: str = None):
        """Detach this log viewer from a logger."""
        if logger_name:
            log = logging.getLogger(logger_name)
        else:
            log = logging.getLogger()
        
        log.removeHandler(self._log_handler)


class LogWindow(Gtk.Window):
    """
    A standalone window for the log viewer.
    """
    
    def __init__(self):
        super().__init__(title="Log Viewer", default_width=800, default_height=600)
        
        # Create the log viewer
        self._log_viewer = LogViewer()
        
        # Add to window
        self.set_child(self._log_viewer)
        
        # Connect window close event
        self.connect("close-request", self._on_close)
    
    def _on_close(self, window):
        """Handle window close event."""
        # Detach from logger to prevent errors when the log viewer is destroyed
        self._log_viewer.detach_from_logger()
        return False  # Return False to allow the window to close


def create_log_viewer_window() -> LogWindow:
    """Create and return a new log viewer window."""
    return LogWindow()