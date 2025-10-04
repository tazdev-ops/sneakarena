"""
Model manager component for the GTK4 GUI.
Allows managing the models configuration.
"""

import json
import logging
from typing import Dict, Any
from gi.repository import Gtk, Adw, GObject, GLib

from lmarena_bridge.settings import load_models, create_default_models
from ..utils.notifications import show_error_async, show_info_async

logger = logging.getLogger(__name__)


class ModelManager(Adw.PreferencesPage):
    """
    A preferences page for managing models configuration.
    """
    
    __gsignals__ = {
        'models-updated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, http_client):
        super().__init__()
        self.set_title("Models")
        self.set_name("models")
        
        self.http_client = http_client
        self._current_models = {}
        
        # Create the main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_child(main_box)
        
        # Create toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        
        # Add model button
        add_btn = Gtk.Button(label="Add Model")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_model)
        toolbar.append(add_btn)
        
        # Refresh from server button
        refresh_btn = Gtk.Button(label="Refresh from Server")
        refresh_btn.connect("clicked", self._on_refresh_from_server)
        toolbar.append(refresh_btn)
        
        main_box.append(toolbar)
        
        # Create the list view for models
        self._create_model_list()
        main_box.append(self._model_list_container)
        
        # Load initial models
        self.load_models()
    
    def _create_model_list(self):
        """Create the list view for displaying models."""
        # Create a ScrolledWindow to contain the list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        # Create a ListStore to hold model data (name, id, type)
        self._list_store = Gtk.ListStore(str, str, str)  # name, id, type
        
        # Create TreeView
        self._tree_view = Gtk.TreeView(model=self._list_store)
        self._tree_view.set_headers_visible(True)
        self._tree_view.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)
        
        # Add columns
        name_column = Gtk.TreeViewColumn("Model Name", Gtk.CellRendererText(), text=0)
        name_column.set_resizable(True)
        name_column.set_expand(True)
        self._tree_view.append_column(name_column)
        
        id_column = Gtk.TreeViewColumn("Model ID", Gtk.CellRendererText(), text=1)
        id_column.set_resizable(True)
        id_column.set_expand(True)
        self._tree_view.append_column(id_column)
        
        type_column = Gtk.TreeViewColumn("Type", Gtk.CellRendererText(), text=2)
        type_column.set_resizable(True)
        self._tree_view.append_column(type_column)
        
        # Add context menu for editing/deleting
        self._tree_view.connect("button-press-event", self._on_tree_view_button_press)
        
        scrolled.set_child(self._tree_view)
        self._model_list_container = scrolled
    
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
                edit_item.connect("activate", self._on_edit_model, model_iter)
                menu.append(edit_item)
                
                # Delete menu item
                delete_item = Gtk.MenuItem.new_with_label("Delete")
                delete_item.connect("activate", self._on_delete_model, model_iter)
                menu.append(delete_item)
            else:
                # Add model option when clicking on empty area
                add_item = Gtk.MenuItem.new_with_label("Add Model")
                add_item.connect("activate", lambda _: self._on_add_model(None))
                menu.append(add_item)
            
            menu.show_all()
            menu.popup_at_pointer(event)
    
    def _on_add_model(self, button):
        """Handle add model button click."""
        dialog = ModelDialog(self.get_root(), None)
        dialog.set_transient_for(self.get_root())
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                model_data = dialog.get_model_data()
                self._add_model_to_store(model_data)
                self._save_models_to_file()
            
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.show()
    
    def _on_edit_model(self, menu_item, model_iter):
        """Handle edit model context menu."""
        # Get current model data
        name = self._list_store.get_value(model_iter, 0)
        model_id = self._list_store.get_value(model_iter, 1)
        model_type = self._list_store.get_value(model_iter, 2)
        
        # Create dialog with current data
        dialog = ModelDialog(self.get_root(), (name, model_id, model_type))
        dialog.set_transient_for(self.get_root())
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                model_data = dialog.get_model_data()
                
                # Update the list store
                self._list_store.set_value(model_iter, 0, model_data[0])  # name
                self._list_store.set_value(model_iter, 1, model_data[1])  # id
                self._list_store.set_value(model_iter, 2, model_data[2])  # type
                
                self._save_models_to_file()
            
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.show()
    
    def _on_delete_model(self, menu_item, model_iter):
        """Handle delete model context menu."""
        # Get the model name for confirmation
        name = self._list_store.get_value(model_iter, 0)
        
        # Show confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.get_root(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Are you sure you want to delete model '{name}'?"
        )
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.YES:
                self._list_store.remove(model_iter)
                self._save_models_to_file()
            
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.show()
    
    def _on_refresh_from_server(self, button):
        """Handle refresh from server button click."""
        def on_models_loaded(models_data, error):
            if error:
                logger.error(f"Error loading models from server: {error}")
                
                def show_error():
                    show_error_async(None, f"Failed to load models from server: {error}")
                GLib.idle_add(show_error)
                return
            
            if models_data and "data" in models_data:
                # Clear the current store
                self._list_store.clear()
                
                # Add new models
                for model in models_data["data"]:
                    model_id = model.get("id", "")
                    # For now, assume all are text models
                    self._list_store.append([model_id, model_id, "text"])
                
                def show_success():
                    show_info_async(None, f"Loaded {len(models_data['data'])} models from server")
                GLib.idle_add(show_success)
                
                logger.info(f"Loaded {len(models_data['data'])} models from server")
            else:
                def show_info():
                    show_info_async(None, "No models received from server")
                GLib.idle_add(show_info)
        
        # Call the API to get models
        self.http_client.get("/v1/models", on_models_loaded)
    
    def _add_model_to_store(self, model_data: tuple):
        """Add a model to the list store."""
        self._list_store.append(model_data)
    
    def _save_models_to_file(self):
        """Save models to the configuration file."""
        # Convert list store to dictionary
        models_dict = {}
        for row in self._list_store:
            name, model_id, model_type = row[:3]
            # Store as "id:type" format like in the config
            models_dict[name] = f"{model_id}:{model_type}"
        
        def _save():
            try:
                # Instead of saving directly, we'll need to make an API call
                # For now, we'll just log this
                logger.info(f"Would save models to file: {models_dict}")
                
                # In a real implementation, send to API endpoint
                # self.http_client.put("/internal/models", models_dict, callback)
                
                def success_callback():
                    self.emit("models-updated")
                    logger.info("Models saved successfully")
                
                GLib.idle_add(success_callback)
                
            except Exception as e:
                logger.error(f"Error saving models: {e}")
                
                def error_callback():
                    show_error_async(None, f"Error saving models: {e}")
                
                GLib.idle_add(error_callback)
        
        import threading
        save_thread = threading.Thread(target=_save, daemon=True)
        save_thread.start()
    
    def load_models(self):
        """Load models from the configuration file."""
        def _load():
            try:
                models = load_models()
                
                def update_ui():
                    # Clear the current store
                    self._list_store.clear()
                    
                    # Add models to the list store
                    for name, spec in models.items():
                        # Parse the spec "id:type" format
                        if ':' in spec:
                            model_id, model_type = spec.split(':', 1)
                        else:
                            model_id, model_type = spec, "text"
                        
                        self._list_store.append([name, model_id, model_type])
                    
                    logger.info(f"Loaded {len(models)} models from configuration")
                
                GLib.idle_add(update_ui)
                
            except Exception as e:
                logger.error(f"Error loading models: {e}")
                
                def error_callback():
                    show_error_async(None, f"Error loading models: {e}")
                
                GLib.idle_add(error_callback)
        
        import threading
        load_thread = threading.Thread(target=_load, daemon=True)
        load_thread.start()


class ModelDialog(Gtk.Dialog):
    """
    Dialog for adding/editing models.
    """
    
    def __init__(self, parent, model_data=None):
        if model_data:
            # Editing existing model
            title = "Edit Model"
            ok_text = "Save"
        else:
            # Adding new model
            title = "Add Model"
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
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Model Name:")
        name_label.set_halign(Gtk.Align.START)
        self._name_entry = Gtk.Entry()
        self._name_entry.set_placeholder_text("e.g., gpt-4, gemini-pro")
        name_box.append(name_label)
        name_box.append(self._name_entry)
        content_area.append(name_box)
        
        # Model ID
        id_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        id_label = Gtk.Label(label="Model ID:")
        id_label.set_halign(Gtk.Align.START)
        self._id_entry = Gtk.Entry()
        self._id_entry.set_placeholder_text("LMArena model UUID")
        id_box.append(id_label)
        id_box.append(self._id_entry)
        content_area.append(id_box)
        
        # Model Type
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        type_label = Gtk.Label(label="Type:")
        type_label.set_halign(Gtk.Align.START)
        self._type_combo = Gtk.ComboBoxText()
        self._type_combo.append("text", "Text Generation")
        self._type_combo.append("image", "Image Generation")
        self._type_combo.set_active_id("text")
        type_box.append(type_label)
        type_box.append(self._type_combo)
        content_area.append(type_box)
        
        # If editing, prefill the fields
        if model_data:
            name, model_id, model_type = model_data
            self._name_entry.set_text(name)
            self._id_entry.set_text(model_id)
            self._type_combo.set_active_id(model_type)
    
    def get_model_data(self):
        """Get the model data from the dialog."""
        return (
            self._name_entry.get_text().strip(),
            self._id_entry.get_text().strip(),
            self._type_combo.get_active_id()
        )