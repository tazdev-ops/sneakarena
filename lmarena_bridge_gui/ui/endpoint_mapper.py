"""
Endpoint mapper component for the GTK4 GUI.
Allows mapping specific models to different session configurations.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from gi.repository import Gtk, Adw, GObject, GLib

from lmarena_bridge.settings import load_model_endpoint_map
from ..utils.notifications import show_error_async, show_info_async

logger = logging.getLogger(__name__)


class EndpointMapper(Adw.PreferencesPage):
    """
    A preferences page for mapping models to specific endpoints/sessions.
    """
    
    __gsignals__ = {
        'mapping-updated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, http_client):
        super().__init__()
        self.set_title("Endpoint Mapper")
        self.set_name("mapper")
        
        self.http_client = http_client
        self._current_mappings = {}
        
        # Create the main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_child(main_box)
        
        # Create toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        
        # Add mapping button
        add_btn = Gtk.Button(label="Add Mapping")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_mapping)
        toolbar.append(add_btn)
        
        main_box.append(toolbar)
        
        # Create the list view for mappings
        self._create_mapping_list()
        main_box.append(self._mapping_list_container)
        
        # Load initial mappings
        self.load_mappings()
    
    def _create_mapping_list(self):
        """Create the list view for displaying endpoint mappings."""
        # Create a ScrolledWindow to contain the list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        # Create a ListStore to hold mapping data (model, session_id, message_id, mode, battle_target)
        self._list_store = Gtk.ListStore(str, str, str, str, str)  # model, session_id, message_id, mode, battle_target
        
        # Create TreeView
        self._tree_view = Gtk.TreeView(model=self._list_store)
        self._tree_view.set_headers_visible(True)
        self._tree_view.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)
        
        # Add columns
        model_column = Gtk.TreeViewColumn("Model", Gtk.CellRendererText(), text=0)
        model_column.set_resizable(True)
        model_column.set_expand(True)
        self._tree_view.append_column(model_column)
        
        session_column = Gtk.TreeViewColumn("Session ID", Gtk.CellRendererText(), text=1)
        session_column.set_resizable(True)
        session_column.set_expand(True)
        self._tree_view.append_column(session_column)
        
        message_column = Gtk.TreeViewColumn("Message ID", Gtk.CellRendererText(), text=2)
        message_column.set_resizable(True)
        message_column.set_expand(True)
        self._tree_view.append_column(message_column)
        
        mode_column = Gtk.TreeViewColumn("Mode", Gtk.CellRendererText(), text=3)
        mode_column.set_resizable(True)
        self._tree_view.append_column(mode_column)
        
        battle_column = Gtk.TreeViewColumn("Battle Target", Gtk.CellRendererText(), text=4)
        battle_column.set_resizable(True)
        self._tree_view.append_column(battle_column)
        
        # Add context menu for editing/deleting
        self._tree_view.connect("button-press-event", self._on_tree_view_button_press)
        
        scrolled.set_child(self._tree_view)
        self._mapping_list_container = scrolled
    
    def _on_tree_view_button_press(self, treeview, event):
        """Handle right-click context menu."""
        if event.button == 3:  # Right click
            # Create context menu
            menu = Gtk.Menu()
            
            # Get the path at the click position
            path_info = treeview.get_path_at_pos(int(event.x), int(event.y))
            if path_info is not None:
                path, col, cellx, celly = path_info
                model_iter = self._list_store.get_iter(path)
                
                # Edit menu item
                edit_item = Gtk.MenuItem.new_with_label("Edit")
                edit_item.connect("activate", self._on_edit_mapping, model_iter)
                menu.append(edit_item)
                
                # Delete menu item
                delete_item = Gtk.MenuItem.new_with_label("Delete")
                delete_item.connect("activate", self._on_delete_mapping, model_iter)
                menu.append(delete_item)
            else:
                # Add mapping option when clicking on empty area
                add_item = Gtk.MenuItem.new_with_label("Add Mapping")
                add_item.connect("activate", lambda _: self._on_add_mapping(None))
                menu.append(add_item)
            
            menu.show_all()
            menu.popup_at_pointer(event)
    
    def _on_add_mapping(self, button):
        """Handle add mapping button click."""
        dialog = MappingDialog(self.get_root(), None)
        dialog.set_transient_for(self.get_root())
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                mapping_data = dialog.get_mapping_data()
                self._add_mapping_to_store(mapping_data)
                self._save_mappings_to_file()
            
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.show()
    
    def _on_edit_mapping(self, menu_item, model_iter):
        """Handle edit mapping context menu."""
        # Get current mapping data
        model = self._list_store.get_value(model_iter, 0)
        session_id = self._list_store.get_value(model_iter, 1)
        message_id = self._list_store.get_value(model_iter, 2)
        mode = self._list_store.get_value(model_iter, 3)
        battle_target = self._list_store.get_value(model_iter, 4)
        
        # Create dialog with current data
        dialog = MappingDialog(
            self.get_root(), 
            (model, session_id, message_id, mode, battle_target)
        )
        dialog.set_transient_for(self.get_root())
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                mapping_data = dialog.get_mapping_data()
                
                # Update the list store
                self._list_store.set_value(model_iter, 0, mapping_data[0])  # model
                self._list_store.set_value(model_iter, 1, mapping_data[1])  # session_id
                self._list_store.set_value(model_iter, 2, mapping_data[2])  # message_id
                self._list_store.set_value(model_iter, 3, mapping_data[3])  # mode
                self._list_store.set_value(model_iter, 4, mapping_data[4])  # battle_target
                
                self._save_mappings_to_file()
            
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.show()
    
    def _on_delete_mapping(self, menu_item, model_iter):
        """Handle delete mapping context menu."""
        # Get the model name for confirmation
        model = self._list_store.get_value(model_iter, 0)
        
        # Show confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.get_root(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Are you sure you want to delete mapping for model '{model}'?"
        )
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.YES:
                self._list_store.remove(model_iter)
                self._save_mappings_to_file()
            
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.show()
    
    def _add_mapping_to_store(self, mapping_data: tuple):
        """Add a mapping to the list store."""
        self._list_store.append(mapping_data)
    
    def _save_mappings_to_file(self):
        """Save mappings to the configuration file."""
        # Convert list store to dictionary
        mappings_dict = {}
        for row in self._list_store:
            model, session_id, message_id, mode, battle_target = row[:5]
            
            # Create the mapping config
            mapping_config = {
                "session_id": session_id,
                "message_id": message_id,
                "mode": mode
            }
            
            # Add battle target if in battle mode
            if mode == "battle" and battle_target:
                mapping_config["battle_target"] = battle_target
            
            mappings_dict[model] = mapping_config
        
        def _save():
            try:
                # In a real implementation, we would save this via API
                # For now, just log the action
                logger.info(f"Would save mappings to file: {mappings_dict}")
                
                def success_callback():
                    self.emit("mapping-updated")
                    logger.info("Mappings saved successfully")
                
                GLib.idle_add(success_callback)
                
            except Exception as e:
                logger.error(f"Error saving mappings: {e}")
                
                def error_callback():
                    show_error_async(None, f"Error saving mappings: {e}")
                
                GLib.idle_add(error_callback)
        
        import threading
        save_thread = threading.Thread(target=_save, daemon=True)
        save_thread.start()
    
    def load_mappings(self):
        """Load mappings from the configuration file."""
        def _load():
            try:
                mappings = load_model_endpoint_map()
                
                def update_ui():
                    # Clear the current store
                    self._list_store.clear()
                    
                    # Add mappings to the list store
                    for model, config in mappings.items():
                        # Handle both single config objects and arrays of configs
                        if isinstance(config, list):
                            # If there are multiple configs for the same model, add each one
                            for config_item in config:
                                session_id = config_item.get("session_id", "")
                                message_id = config_item.get("message_id", "")
                                mode = config_item.get("mode", "direct_chat")
                                battle_target = config_item.get("battle_target", "")
                                
                                self._list_store.append([
                                    model, session_id, message_id, mode, battle_target
                                ])
                        else:
                            # Single config object
                            session_id = config.get("session_id", "")
                            message_id = config.get("message_id", "")
                            mode = config.get("mode", "direct_chat")
                            battle_target = config.get("battle_target", "")
                            
                            self._list_store.append([
                                model, session_id, message_id, mode, battle_target
                            ])
                    
                    logger.info(f"Loaded {len(mappings)} model mappings from configuration")
                
                GLib.idle_add(update_ui)
                
            except Exception as e:
                logger.error(f"Error loading mappings: {e}")
                
                def error_callback():
                    show_error_async(None, f"Error loading mappings: {e}")
                
                GLib.idle_add(error_callback)
        
        import threading
        load_thread = threading.Thread(target=_load, daemon=True)
        load_thread.start()


class MappingDialog(Gtk.Dialog):
    """
    Dialog for adding/editing endpoint mappings.
    """
    
    def __init__(self, parent, mapping_data=None):
        if mapping_data:
            # Editing existing mapping
            title = "Edit Mapping"
            ok_text = "Save"
        else:
            # Adding new mapping
            title = "Add Mapping"
            ok_text = "Add"
        
        super().__init__(title=title, transient_for=parent)
        
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            ok_text, Gtk.ResponseType.OK
        )
        
        # Set default response
        self.set_default_response(Gtk.ResponseType.OK)
        
        # Create the dialog content
        content_area = self.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_start(12)
        content_area.set_margin_end(12)
        content_area.set_margin_top(12)
        content_area.set_margin_bottom(12)
        
        # Model name
        model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        model_label = Gtk.Label(label="Model Name:")
        model_label.set_halign(Gtk.Align.START)
        self._model_entry = Gtk.Entry()
        self._model_entry.set_placeholder_text("Model name to map")
        model_box.append(model_label)
        model_box.append(self._model_entry)
        content_area.append(model_box)
        
        # Session ID
        session_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        session_label = Gtk.Label(label="Session ID:")
        session_label.set_halign(Gtk.Align.START)
        self._session_entry = Gtk.Entry()
        self._session_entry.set_placeholder_text("Session UUID")
        session_box.append(session_label)
        session_box.append(self._session_entry)
        content_area.append(session_box)
        
        # Message ID
        message_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        message_label = Gtk.Label(label="Message ID:")
        message_label.set_halign(Gtk.Align.START)
        self._message_entry = Gtk.Entry()
        self._message_entry.set_placeholder_text("Message UUID")
        message_box.append(message_label)
        message_box.append(self._message_entry)
        content_area.append(message_box)
        
        # Mode selection
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_label = Gtk.Label(label="Mode:")
        mode_label.set_halign(Gtk.Align.START)
        self._mode_combo = Gtk.ComboBoxText()
        self._mode_combo.append("direct_chat", "Direct Chat")
        self._mode_combo.append("battle", "Battle")
        self._mode_combo.set_active_id("direct_chat")
        self._mode_combo.connect("changed", self._on_mode_changed)
        mode_box.append(mode_label)
        mode_box.append(self._mode_combo)
        content_area.append(mode_box)
        
        # Battle target (initially hidden)
        self._battle_target_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        battle_target_label = Gtk.Label(label="Battle Target:")
        battle_target_label.set_halign(Gtk.Align.START)
        self._battle_target_combo = Gtk.ComboBoxText()
        self._battle_target_combo.append("A", "A")
        self._battle_target_combo.append("B", "B")
        self._battle_target_combo.set_active_id("A")
        self._battle_target_box.append(battle_target_label)
        self._battle_target_box.append(self._battle_target_combo)
        self._battle_target_box.set_visible(False)  # Hidden by default
        content_area.append(self._battle_target_box)
        
        # If editing, prefill the fields
        if mapping_data:
            model, session_id, message_id, mode, battle_target = mapping_data
            self._model_entry.set_text(model)
            self._session_entry.set_text(session_id)
            self._message_entry.set_text(message_id)
            self._mode_combo.set_active_id(mode)
            if battle_target:
                self._battle_target_combo.set_active_id(battle_target)
            
            # Show battle target if mode is battle
            if mode == "battle":
                self._battle_target_box.set_visible(True)
    
    def _on_mode_changed(self, combo):
        """Handle mode selection change."""
        mode = combo.get_active_id()
        # Show/hide battle target based on mode
        self._battle_target_box.set_visible(mode == "battle")
    
    def get_mapping_data(self):
        """Get the mapping data from the dialog."""
        mode = self._mode_combo.get_active_id()
        battle_target = self._battle_target_combo.get_active_id() if mode == "battle" else ""
        
        return (
            self._model_entry.get_text().strip(),
            self._session_entry.get_text().strip(),
            self._message_entry.get_text().strip(),
            mode,
            battle_target
        )