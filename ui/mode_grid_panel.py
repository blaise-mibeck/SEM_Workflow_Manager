"""
ModeGrid panel for SEM Image Workflow Manager.
Allows control of the ModeGrid workflow.
"""

import os
from qtpy import QtWidgets, QtCore, QtGui
from utils.logger import Logger
from utils.config import config
from workflows.mode_grid import ModeGridWorkflow

logger = Logger(__name__)


class ModeGridPanel(QtWidgets.QGroupBox):
    """
    Panel for controlling the ModeGrid workflow.
    """
    
    # Custom signals
    grid_created = QtCore.Signal(object, object)  # Grid image, collection
    
    def __init__(self, session_manager, parent=None):
        """
        Initialize ModeGrid panel.
        
        Args:
            session_manager: Session manager instance
            parent: Parent widget
        """
        super().__init__("ModeGrid Control", parent)
        
        self.session_manager = session_manager
        self.workflow = ModeGridWorkflow(session_manager)
        
        # Initialize UI
        self._init_ui()
        
        logger.info("ModeGrid panel initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Collection selection
        collection_group = QtWidgets.QGroupBox("Collections")
        collection_layout = QtWidgets.QVBoxLayout(collection_group)
        
        self.collection_list = QtWidgets.QListWidget()
        self.collection_list.itemSelectionChanged.connect(self._on_collection_selected)
        collection_layout.addWidget(self.collection_list)
        
        # Discover button
        self.discover_button = QtWidgets.QPushButton("Discover Collections")
        self.discover_button.clicked.connect(self.discover_collections)
        collection_layout.addWidget(self.discover_button)
        
        layout.addWidget(collection_group)
        
        # Label options
        label_group = QtWidgets.QGroupBox("Label Options")
        label_layout = QtWidgets.QGridLayout(label_group)
        
        # Mode label option
        self.label_mode_check = QtWidgets.QCheckBox("Show Mode")
        self.label_mode_check.setChecked(config.get('mode_grid.label_mode', True))
        label_layout.addWidget(self.label_mode_check, 0, 0)
        
        # Voltage label option
        self.label_voltage_check = QtWidgets.QCheckBox("Show Voltage")
        self.label_voltage_check.setChecked(config.get('mode_grid.label_voltage', True))
        label_layout.addWidget(self.label_voltage_check, 0, 1)
        
        # Current label option
        self.label_current_check = QtWidgets.QCheckBox("Show Current")
        self.label_current_check.setChecked(config.get('mode_grid.label_current', True))
        label_layout.addWidget(self.label_current_check, 1, 0)
        
        # Integrations label option
        self.label_int_check = QtWidgets.QCheckBox("Show Integrations")
        self.label_int_check.setChecked(config.get('mode_grid.label_integrations', True))
        label_layout.addWidget(self.label_int_check, 1, 1)
        
        # Font size option
        font_size_layout = QtWidgets.QHBoxLayout()
        font_size_label = QtWidgets.QLabel("Label Font Size:")
        font_size_layout.addWidget(font_size_label)
        
        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(config.get('mode_grid.label_font_size', 12))
        font_size_layout.addWidget(self.font_size_spin)
        
        label_layout.addLayout(font_size_layout, 2, 0, 1, 2)
        
        layout.addWidget(label_group)
        
        # Layout options
        layout_group = QtWidgets.QGroupBox("Grid Layout")
        layout_form = QtWidgets.QFormLayout(layout_group)
        
        self.layout_combo = QtWidgets.QComboBox()
        self.layout_combo.addItem("Automatic", None)
        self.layout_combo.addItem("1×2 (1 row, 2 columns)", (1, 2))
        self.layout_combo.addItem("2×1 (2 rows, 1 column)", (2, 1))
        self.layout_combo.addItem("2×2 (2 rows, 2 columns)", (2, 2))
        self.layout_combo.addItem("2×3 (2 rows, 3 columns)", (2, 3))
        self.layout_combo.addItem("3×2 (3 rows, 2 columns)", (3, 2))
        self.layout_combo.addItem("3×3 (3 rows, 3 columns)", (3, 3))
        layout_form.addRow("Layout:", self.layout_combo)
        
        layout.addWidget(layout_group)
        
        # Apply button
        self.apply_button = QtWidgets.QPushButton("Create Grid")
        self.apply_button.clicked.connect(self.create_grid)
        self.apply_button.setEnabled(False)
        layout.addWidget(self.apply_button)
        
        # Alternative image selection
        self.alt_image_menu = QtWidgets.QMenu(self)
    
    def discover_collections(self):
        """Discover ModeGrid collections."""
        if not self.session_manager or not self.session_manager.current_session:
            QtWidgets.QMessageBox.warning(
                self,
                "No Session",
                "Please open a session folder first."
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
        """Update the collections list."""
        self.collection_list.clear()
        
        # Add collections to list
        for collection in self.workflow.collections:
            num_images = len(collection.get("images", []))
            fov_width = collection.get("field_of_view_width", 0)
            fov_height = collection.get("field_of_view_height", 0)
            
            # Create display text
            item_text = f"ModeGrid: {num_images} modes, FOV {fov_width:.1f}×{fov_height:.1f}μm"
            
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, collection)
            self.collection_list.addItem(item)
    
    def _on_collection_selected(self):
        """Handle collection selection."""
        self.apply_button.setEnabled(self.collection_list.currentItem() is not None)
    
    def create_grid(self):
        """Create grid visualization for selected collection."""
        current_item = self.collection_list.currentItem()
        if not current_item:
            logger.error("No collection selected")
            return
        
        collection = current_item.data(QtCore.Qt.UserRole)
        if not collection:
            logger.error("Selected item has no collection data")
            return
            
        # Log collection before passing to workflow
        logger.debug(f"Attempting to create grid for collection: {collection.get('id', 'unknown')}")
        logger.debug(f"Collection has {len(collection.get('images', []))} images")
        
        # Get label options
        options = {
            "label_mode": self.label_mode_check.isChecked(),
            "label_voltage": self.label_voltage_check.isChecked(),
            "label_current": self.label_current_check.isChecked(),
            "label_integrations": self.label_int_check.isChecked(),
            "label_font_size": self.font_size_spin.value()
        }
        
        # Save options to config
        config.set('mode_grid.label_mode', options["label_mode"])
        config.set('mode_grid.label_voltage', options["label_voltage"])
        config.set('mode_grid.label_current', options["label_current"])
        config.set('mode_grid.label_integrations', options["label_integrations"])
        config.set('mode_grid.label_font_size', options["label_font_size"])
        
        # Get layout
        layout = self.layout_combo.currentData()
        
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
        
        # Get layout information
        images = collection.get("images", [])
        num_images = len(images)
        
        layout = None
        
        # Determine the layout based on number of images
        if num_images == 2:
            layout = (1, 2)  # 1 row, 2 columns
        elif num_images <= 4:
            layout = (2, 2)  # 2 rows, 2 columns
        elif num_images <= 6:
            layout = (2, 3)  # 2 rows, 3 columns
        else:
            layout = (3, 3)  # 3 rows, 3 columns
        
        rows, cols = layout
        
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
            options = {
                "label_mode": self.label_mode_check.isChecked(),
                "label_voltage": self.label_voltage_check.isChecked(),
                "label_current": self.label_current_check.isChecked(),
                "label_integrations": self.label_int_check.isChecked(),
                "label_font_size": self.font_size_spin.value()
            }
            
            # Get layout
            layout = self.layout_combo.currentData()
            
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