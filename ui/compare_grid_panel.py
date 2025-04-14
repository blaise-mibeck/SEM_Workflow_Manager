"""
CompareGrid panel for SEM Image Workflow Manager.
Allows selection of multiple sessions for comparison.
"""

import os
from qtpy import QtWidgets, QtCore, QtGui
from utils.logger import Logger
from workflows.compare_grid import CompareGridWorkflow

logger = Logger(__name__)


class SessionSelectionDialog(QtWidgets.QDialog):
    """
    Dialog for selecting multiple session folders.
    """
    
    def __init__(self, parent=None, initial_folder=None):
        """Initialize dialog."""
        super().__init__(parent)
        
        self.setWindowTitle("Select Sessions for Comparison")
        self.resize(700, 400)
        
        # Initialize UI
        self._init_ui()
        
        # Set initial folder if provided
        if initial_folder and os.path.exists(initial_folder):
            self.folder_edit.setText(initial_folder)
            self.current_folder = initial_folder
            self.refresh_session_list()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Folder selection
        folder_layout = QtWidgets.QHBoxLayout()
        
        folder_label = QtWidgets.QLabel("Session Folder:")
        folder_layout.addWidget(folder_label)
        
        self.folder_edit = QtWidgets.QLineEdit()
        self.folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_edit)
        
        browse_button = QtWidgets.QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_parent_folder)
        folder_layout.addWidget(browse_button)
        
        layout.addLayout(folder_layout)
        
        # Sessions list
        list_layout = QtWidgets.QHBoxLayout()
        
        # Available sessions
        available_group = QtWidgets.QGroupBox("Available Sessions")
        available_layout = QtWidgets.QVBoxLayout(available_group)
        
        self.available_list = QtWidgets.QListWidget()
        self.available_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        available_layout.addWidget(self.available_list)
        
        list_layout.addWidget(available_group)
        
        # Buttons for adding/removing
        buttons_layout = QtWidgets.QVBoxLayout()
        
        self.add_button = QtWidgets.QPushButton("Add >")
        self.add_button.clicked.connect(self._add_sessions)
        buttons_layout.addWidget(self.add_button)
        
        self.remove_button = QtWidgets.QPushButton("< Remove")
        self.remove_button.clicked.connect(self._remove_sessions)
        buttons_layout.addWidget(self.remove_button)
        
        buttons_layout.addStretch()
        
        list_layout.addLayout(buttons_layout)
        
        # Selected sessions
        selected_group = QtWidgets.QGroupBox("Selected Sessions")
        selected_layout = QtWidgets.QVBoxLayout(selected_group)
        
        self.selected_list = QtWidgets.QListWidget()
        self.selected_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        selected_layout.addWidget(self.selected_list)
        
        list_layout.addWidget(selected_group)
        
        layout.addLayout(list_layout)
        
        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _browse_parent_folder(self):
        """Browse for parent folder containing session folders."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Parent Folder",
            os.path.expanduser("~")
        )
        
        if folder:
            self.folder_edit.setText(folder)
            self.current_folder = folder
            self.refresh_session_list()
    
    def refresh_session_list(self):
        """Refresh the list of available sessions."""
        self.available_list.clear()
        
        if not hasattr(self, 'current_folder') or not os.path.exists(self.current_folder):
            return
        
        # Look for session folders (those with session_info.json)
        for entry in os.listdir(self.current_folder):
            folder_path = os.path.join(self.current_folder, entry)
            if os.path.isdir(folder_path):
                info_file = os.path.join(folder_path, "session_info.json")
                if os.path.exists(info_file):
                    item = QtWidgets.QListWidgetItem(entry)
                    item.setData(QtCore.Qt.UserRole, folder_path)
                    self.available_list.addItem(item)
    
    def _add_sessions(self):
        """Add selected sessions to comparison."""
        for item in self.available_list.selectedItems():
            folder_path = item.data(QtCore.Qt.UserRole)
            
            # Check if already in selected list
            existing = False
            for i in range(self.selected_list.count()):
                if self.selected_list.item(i).data(QtCore.Qt.UserRole) == folder_path:
                    existing = True
                    break
            
            if not existing:
                new_item = QtWidgets.QListWidgetItem(item.text())
                new_item.setData(QtCore.Qt.UserRole, folder_path)
                self.selected_list.addItem(new_item)
    
    def _remove_sessions(self):
        """Remove sessions from comparison."""
        for item in self.selected_list.selectedItems():
            self.selected_list.takeItem(self.selected_list.row(item))
    
    def get_selected_sessions(self):
        """Get list of selected session folders."""
        sessions = []
        for i in range(self.selected_list.count()):
            sessions.append(self.selected_list.item(i).data(QtCore.Qt.UserRole))
        return sessions


class CompareGridPanel(QtWidgets.QGroupBox):
    """
    Panel for controlling the CompareGrid workflow.
    """
    
    # Custom signals
    grid_created = QtCore.Signal(object, object)  # Grid image, collection
    
    def __init__(self, session_manager, parent=None):
        """
        Initialize CompareGrid panel.
        
        Args:
            session_manager: Session manager instance
            parent: Parent widget
        """
        super().__init__("CompareGrid Control", parent)
        
        self.session_manager = session_manager
        self.workflow = CompareGridWorkflow(session_manager)
        
        # Initialize UI
        self._init_ui()
        
        logger.info("CompareGrid panel initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Session selection
        session_group = QtWidgets.QGroupBox("Sessions")
        session_layout = QtWidgets.QVBoxLayout(session_group)
        
        # Main session
        main_session_layout = QtWidgets.QHBoxLayout()
        main_session_label = QtWidgets.QLabel("Main Session:")
        main_session_layout.addWidget(main_session_label)
        
        self.main_session_edit = QtWidgets.QLineEdit()
        self.main_session_edit.setReadOnly(True)
        main_session_layout.addWidget(self.main_session_edit)
        session_layout.addLayout(main_session_layout)
        
        # Selected sessions list
        self.session_list = QtWidgets.QListWidget()
        self.session_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        session_layout.addWidget(self.session_list)
        
        # Session buttons
        session_buttons_layout = QtWidgets.QHBoxLayout()
        
        # FIXED: Changed method name in connect to match class method name
        self.add_session_button = QtWidgets.QPushButton("Add Sessions...")
        self.add_session_button.clicked.connect(self.add_sessions)  # No underscore
        session_buttons_layout.addWidget(self.add_session_button)
        
        # FIXED: Changed method name in connect to match class method name
        self.remove_session_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_session_button.clicked.connect(self.remove_sessions)  # No underscore
        session_buttons_layout.addWidget(self.remove_session_button)
        
        session_layout.addLayout(session_buttons_layout)
        
        layout.addWidget(session_group)
        
        # Collection selection with tree structure
        collection_group = QtWidgets.QGroupBox("Collections")
        collection_layout = QtWidgets.QVBoxLayout(collection_group)
        
        self.collection_tree = QtWidgets.QTreeWidget()
        self.collection_tree.setHeaderLabels(["Description", "Status"])
        self.collection_tree.setColumnWidth(0, 300)
        self.collection_tree.setColumnWidth(1, 100)
        self.collection_tree.itemSelectionChanged.connect(self._on_collection_selected)
        collection_layout.addWidget(self.collection_tree)
        
        # FIXED: Changed method name in connect to match class method name
        # Collection discovery button
        self.discover_button = QtWidgets.QPushButton("Discover Collections")
        self.discover_button.clicked.connect(self.discover_collections)  # No underscore
        collection_layout.addWidget(self.discover_button)
        
        layout.addWidget(collection_group)
        
        # Label options
        label_group = QtWidgets.QGroupBox("Label Options")
        label_layout = QtWidgets.QFormLayout(label_group)
        
        self.label_combo = QtWidgets.QComboBox()
        self.label_combo.addItem("Sample ID", "id")
        self.label_combo.addItem("Sample Name", "name")
        self.label_combo.addItem("Both ID and Name", "both")
        label_layout.addRow("Label Type:", self.label_combo)
        
        # Font size control with direct entry box
        font_size_layout = QtWidgets.QHBoxLayout()
        
        self.font_size_edit = QtWidgets.QSpinBox()
        self.font_size_edit.setMinimum(6)
        self.font_size_edit.setMaximum(72)
        self.font_size_edit.setValue(16)  # Default value
        self.font_size_edit.setSuffix(" pt")
        
        font_size_layout.addWidget(QtWidgets.QLabel("Font Size:"))
        font_size_layout.addWidget(self.font_size_edit)
        
        label_layout.addRow("", font_size_layout)
        
        layout.addWidget(label_group)
        
        # Layout options
        layout_group = QtWidgets.QGroupBox("Grid Layout")
        layout_form = QtWidgets.QFormLayout(layout_group)
        
        self.layout_combo = QtWidgets.QComboBox()
        self.layout_combo.addItem("Automatic", None)
        self.layout_combo.addItem("1 row", (1, 0))
        self.layout_combo.addItem("2 rows", (2, 0))
        self.layout_combo.addItem("3 rows", (3, 0))
        self.layout_combo.addItem("4 rows", (4, 0))
        layout_form.addRow("Layout:", self.layout_combo)
        
        layout.addWidget(layout_group)
        
        # FIXED: Changed method name in connect to match class method name
        # Apply button
        self.apply_button = QtWidgets.QPushButton("Create Grid")
        self.apply_button.clicked.connect(self.create_grid)  # No underscore
        self.apply_button.setEnabled(False)
        layout.addWidget(self.apply_button)
        
        # Alternative image selection
        self.alt_image_menu = QtWidgets.QMenu(self)
        
        # Update UI if there's a main session
        self._update_main_session()
    
    def _update_main_session(self):
        """Update UI with main session information."""
        if self.session_manager and self.session_manager.session_folder:
            self.main_session_edit.setText(self.session_manager.session_folder)
            
            # Add main session to workflow if not already there
            self.workflow.main_session_folder = self.session_manager.session_folder
            
            # Make sure main session is in the session list
            self._add_session_to_list(self.session_manager.session_folder)
    
    def add_sessions(self):  # Method name without underscore
        """Open dialog to add sessions for comparison."""
        # Determine initial folder based on main session
        initial_folder = None
        if self.session_manager and self.session_manager.session_folder:
            initial_folder = os.path.dirname(self.session_manager.session_folder)
        
        dialog = SessionSelectionDialog(self, initial_folder)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_sessions = dialog.get_selected_sessions()
            
            for session_folder in selected_sessions:
                # Add to workflow
                if self.workflow.add_session(session_folder):
                    # Add to list if successful
                    self._add_session_to_list(session_folder)
                else:
                    logger.error(f"Failed to add session: {session_folder}")
    
    def _add_session_to_list(self, session_folder):
        """Add a session to the list if not already there."""
        # Check if already in list
        for i in range(self.session_list.count()):
            if self.session_list.item(i).data(QtCore.Qt.UserRole) == session_folder:
                return
        
        # Add to list
        session_name = os.path.basename(session_folder)
        
        # Try to get sample ID
        sample_id = "Unknown"
        session_info = self.workflow.get_session_info(session_folder)
        if session_info:
            sample_id = session_info.sample_id
            
        # Create item
        item = QtWidgets.QListWidgetItem(f"{session_name} ({sample_id})")
        item.setData(QtCore.Qt.UserRole, session_folder)
        self.session_list.addItem(item)
    
    def remove_sessions(self):  # Method name without underscore
        """Remove selected sessions from comparison."""
        selected_items = self.session_list.selectedItems()
        
        for item in selected_items:
            session_folder = item.data(QtCore.Qt.UserRole)
            
            # Don't remove the main session
            if session_folder == self.workflow.main_session_folder:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Cannot Remove Session",
                    "The main session cannot be removed from the comparison."
                )
                continue
            
            # Remove from workflow
            if self.workflow.remove_session(session_folder):
                # Remove from list
                self.session_list.takeItem(self.session_list.row(item))
            else:
                logger.error(f"Failed to remove session: {session_folder}")
    
    def discover_collections(self):  # Method name without underscore
        """Discover CompareGrid collections."""
        if len(self.workflow.sessions) < 2:
            QtWidgets.QMessageBox.warning(
                self,
                "Insufficient Sessions",
                "At least two sessions are required for comparison. Please add more sessions."
            )
            return
        
        # Show progress dialog
        progress = QtWidgets.QProgressDialog(
            "Discovering collections...",
            "Cancel",
            0,
            100,
            self
        )
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setValue(10)
        
        try:
            # Discover collections
            self.workflow.discover_collections()
            progress.setValue(90)
            
            # Update collections list
            self._update_collections_list()
            progress.setValue(100)
            
        except Exception as e:
            logger.exception(f"Error discovering collections: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Discovery Error",
                f"Error discovering collections: {str(e)}"
            )
    
    def _update_collections_list(self):
        """Update the collections tree."""
        self.collection_tree.clear()
        
        # Add collections to tree
        for collection in self.workflow.collections:
            desc = collection.get("description", "")
            count = len(collection.get("images", []))
            
            # Create top-level item
            item_text = f"{desc} ({count} samples)"
            collection_item = QtWidgets.QTreeWidgetItem([item_text, ""])
            collection_item.setData(0, QtCore.Qt.UserRole, collection)
            self.collection_tree.addTopLevelItem(collection_item)
            
            # Add image items as children
            for img_index, img_data in enumerate(collection.get("images", [])):
                img_path = img_data.get("path", "Unknown path")
                sample_id = img_data.get("sample_id", "Unknown")
                img_filename = os.path.basename(img_path)
                
                # Check if file exists and set status accordingly
                status = "OK"
                if not os.path.exists(img_path):
                    status = "Missing"
                
                # Create child item with image details
                img_text = f"[{sample_id}] {img_filename}"
                img_item = QtWidgets.QTreeWidgetItem([img_text, status])
                img_item.setData(0, QtCore.Qt.UserRole, img_data)
                
                # Set color based on status
                if status == "Missing":
                    img_item.setForeground(1, QtGui.QBrush(QtGui.QColor(255, 0, 0)))  # Red for missing
                else:
                    img_item.setForeground(1, QtGui.QBrush(QtGui.QColor(0, 128, 0)))  # Green for OK
                
                # Add file path as tooltip
                img_item.setToolTip(0, img_path)
                
                collection_item.addChild(img_item)
            
            # Auto-expand collection items
            collection_item.setExpanded(True)
    
    def _on_collection_selected(self):
        """Handle collection selection."""
        current_item = self.collection_tree.currentItem()
        
        # Only enable the apply button if a top-level collection item is selected
        if current_item and current_item.parent() is None:
            self.apply_button.setEnabled(True)
        else:
            self.apply_button.setEnabled(False)
    
    def create_grid(self):  # Method name without underscore
        """Create grid visualization for selected collection."""
        current_item = self.collection_tree.currentItem()
        
        # If a child item is selected, get its parent (the collection)
        if current_item:
            if current_item.parent():
                current_item = current_item.parent()
            
            collection = current_item.data(0, QtCore.Qt.UserRole)
        else:
            return
        
        # Get label options
        label_style = self.label_combo.currentData()
        font_size = self.font_size_edit.value()
        options = {
            "label_style": label_style,
            "font_size": font_size
        }
        
        # Get layout
        layout_data = self.layout_combo.currentData()
        if layout_data:
            rows, cols = layout_data
            # Calculate columns if not specified
            if cols == 0:
                cols = (len(collection.get("images", [])) + rows - 1) // rows
            layout = (rows, cols)
        else:
            layout = None
        
        # Create grid visualization
        try:
            grid_image = self.workflow.create_grid(collection, layout, options)
            if grid_image:
                # Emit signal with grid image and collection
                self.grid_created.emit(grid_image, collection)
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Grid Creation Error",
                    "Failed to create grid visualization."
                )
        except Exception as e:
            logger.exception(f"Error creating grid: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Grid Creation Error",
                f"Error creating grid visualization: {str(e)}"
            )
    
    def show_alternative_menu(self, grid_widget, pos, collection):
        """
        Show context menu for selecting alternative images.
        
        Args:
            grid_widget: Widget containing the grid visualization
            pos: Position where right-click occurred
            collection: Current collection
        """
        if not collection or "images" not in collection:
            return
        
        # Convert position to grid widget coordinates
        global_pos = grid_widget.mapToGlobal(pos)
        
        # Find which image was clicked
        grid_img_size = grid_widget.pixmap().size()
        img_width = grid_img_size.width()
        img_height = grid_img_size.height()
        
        # Get layout information from collection
        images = collection.get("images", [])
        num_images = len(images)
        
        # Determine layout
        if num_images <= 4:
            cols = num_images
            rows = 1
        else:
            cols = (num_images + 1) // 2
            rows = 2
        
        # Calculate cell size (approximate)
        cell_width = img_width / cols
        cell_height = img_height / rows
        
        # Convert click position to cell indices
        click_x = pos.x()
        click_y = pos.y()
        
        col_index = int(click_x / cell_width)
        row_index = int(click_y / cell_height)
        
        # Calculate index in the collection
        image_index = row_index * cols + col_index
        
        if image_index >= 0 and image_index < num_images:
            # Get the image data
            image_data = images[image_index]
            
            # Check if it has alternatives
            alternatives = image_data.get("alternatives", [])
            
            if alternatives:
                # Clear previous menu
                self.alt_image_menu.clear()
                
                # Add action for each alternative
                for alt_path in alternatives:
                    alt_filename = os.path.basename(alt_path)
                    action = self.alt_image_menu.addAction(f"Switch to: {alt_filename}")
                    
                    # Connect action to switch function
                    action.triggered.connect(
                        lambda checked=False, 
                               c=collection, 
                               idx=image_index, 
                               path=alt_path: self._switch_alternative(c, idx, path)
                    )
                
                # Show the menu
                self.alt_image_menu.popup(global_pos)
    
    def _switch_alternative(self, collection, image_index, alt_path):
        """
        Switch to an alternative image.
        
        Args:
            collection: Collection data
            image_index: Index of the image to replace
            alt_path: Path to the alternative image
        """
        # Update collection with alternative image
        updated_collection = self.workflow.switch_image_alternative(collection, image_index, alt_path)
        
        # Re-create the grid
        try:
            # Get label options
            label_style = self.label_combo.currentData()
            font_size = self.font_size_edit.value()
            options = {
                "label_style": label_style,
                "font_size": font_size
            }
            
            # Get layout
            layout_data = self.layout_combo.currentData()
            if layout_data:
                rows, cols = layout_data
                # Calculate columns if not specified
                if cols == 0:
                    cols = (len(updated_collection.get("images", [])) + rows - 1) // rows
                layout = (rows, cols)
            else:
                layout = None
            
            grid_image = self.workflow.create_grid(updated_collection, layout, options)
            if grid_image:
                # Emit signal with grid image and collection
                self.grid_created.emit(grid_image, updated_collection)
        except Exception as e:
            logger.exception(f"Error updating grid: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Update Error",
                f"Error updating grid visualization: {str(e)}"
            )
