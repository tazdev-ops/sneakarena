"""
Notification utilities for the GTK4 GUI.
Handles displaying notifications to the user using GLib.idle_add for thread safety.
"""

import logging
import subprocess
import sys
from typing import Optional
from gi.repository import Gtk, Adw, Gio, GLib

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages notifications for the GTK4 GUI application.
    Uses both desktop notifications (via notify-send) and in-app toast notifications.
    """
    
    @staticmethod
    def show_notification(title: str, message: str, priority: str = "normal") -> None:
        """
        Show a desktop notification using notify-send (if available).
        
        Args:
            title: Notification title
            message: Notification message
            priority: Priority level (low, normal, critical)
        """
        try:
            # Use notify-send command-line tool for desktop notifications
            subprocess.run([
                "notify-send", 
                f"--app-name=LMArena Bridge",
                f"--urgency={priority[0]}",  # low=l, normal=n, critical=c
                f"--expire-time=3000",  # 3 seconds
                title,
                message
            ], check=False)  # Don't raise exception if notify-send fails
        except Exception as e:
            logger.debug(f"Could not send desktop notification: {e}")
    
    @staticmethod
    def show_toast(window: Adw.ApplicationWindow, message: str, timeout: int = 3) -> None:
        """
        Show an in-app toast notification.
        
        Args:
            window: The main application window
            message: The message to display
            timeout: How long to show the toast (in seconds)
        """
        toast = Adw.Toast.new(message)
        toast.set_timeout(timeout)
        window.get_content().get_first_child().add_toast(toast)  # Assuming standard layout
    
    @staticmethod
    def show_error_dialog(parent_window: Optional[Gtk.Window], message: str) -> None:
        """
        Show an error dialog to the user.
        
        Args:
            parent_window: The parent window (can be None)
            message: The error message to display
        """
        dialog = Gtk.MessageDialog(
            transient_for=parent_window,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=message
        )
        dialog.run()
        dialog.destroy()
    
    @staticmethod
    def show_info_dialog(parent_window: Optional[Gtk.Window], message: str) -> None:
        """
        Show an information dialog to the user.
        
        Args:
            parent_window: The parent window (can be None)
            message: The information message to display
        """
        dialog = Gtk.MessageDialog(
            transient_for=parent_window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()
    
    @staticmethod
    def show_confirmation_dialog(
        parent_window: Gtk.Window, 
        title: str, 
        message: str,
        callback: callable
    ) -> None:
        """
        Show a confirmation dialog to the user.
        
        Args:
            parent_window: The parent window
            title: Dialog title
            message: Confirmation message
            callback: Function to call with result (True for OK, False for Cancel)
        """
        dialog = Gtk.MessageDialog(
            transient_for=parent_window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=message
        )
        
        def on_response(dialog, response_id):
            dialog.destroy()
            callback(response_id == Gtk.ResponseType.OK)
        
        dialog.connect("response", on_response)
        dialog.show()


def show_notification_async(title: str, message: str, priority: str = "normal") -> None:
    """
    Show notification asynchronously using GLib.idle_add to ensure thread safety.
    """
    def _show():
        NotificationManager.show_notification(title, message, priority)
    
    GLib.idle_add(_show)


def show_toast_async(window: Adw.ApplicationWindow, message: str, timeout: int = 3) -> None:
    """
    Show toast notification asynchronously using GLib.idle_add for thread safety.
    """
    def _show():
        NotificationManager.show_toast(window, message, timeout)
    
    GLib.idle_add(_show)


def show_error_async(window: Optional[Gtk.Window], message: str) -> None:
    """
    Show error dialog asynchronously using GLib.idle_add for thread safety.
    """
    def _show():
        NotificationManager.show_error_dialog(window, message)
    
    GLib.idle_add(_show)


def show_info_async(window: Optional[Gtk.Window], message: str) -> None:
    """
    Show info dialog asynchronously using GLib.idle_add for thread safety.
    """
    def _show():
        NotificationManager.show_info_dialog(window, message)
    
    GLib.idle_add(_show)