"""
Annotate Overview panel for SEM Image Workflow Manager.
Provides tools for annotating overview images with a metadata data bar.
Uses Matplotlib for enhanced visualization and interaction.
"""

import os
import numpy as np
from qtpy import QtWidgets, QtCore, QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from PIL import Image
from utils.logger import Logger

logger = Logger(__name__)


class MatplotlibCanvas(FigureCanvas):
    """Canvas for displaying images with Matplotlib."""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """Initialize the canvas."""
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set background color to match the application
        self.fig.patch.set_facecolor('#f0f0f0')
        
        # Enable the axes
        self.axes.set_visible(True)
        
        # Improve layout
        self.fig.tight_layout()
        
        # Store image and annotation data
        self.image_obj = None
        self.marked_locations = []
        self.selected_locations = []
        self.coord_text = None
        
        # Connect events
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.mpl_connect('scroll_event', self.on_scroll)
        self.mpl_connect('button_press_event', self.on_button_press)
        
        # Set initial view limits
        self.axes.set_xlim(0, 100)
        self.axes.set_ylim(0, 100)
        
        # Create coordinate display text
        self.coord_text = self.fig.text(0.02, 0.02, 'Pixel: (-, -) | Microscope: (-, -)', 
                                        bbox=dict(facecolor='white', alpha=0.8))
        
        # Store microscope coordinate system information
        self.overview_center_x = 0
        self.overview_center_y = 0
        self.um_per_pixel_x = 1
        self.um_per_pixel_y = 1
    
    def set_microscope_coordinates(self, center_x, center_y, um_per_pixel_x=1, um_per_pixel_y=1):
        """Set the microscope coordinate system parameters."""
        self.overview_center_x = center_x
        self.overview_center_y = center_y
        self.um_per_pixel_x = um_per_pixel_x
        self.um_per_pixel_y = um_per_pixel_y
    
    def on_mouse_move(self, event):
        """Handle mouse movement to update coordinate display."""
        if event.inaxes:
            # Calculate microscope coordinates (microscope coordinates increase in opposite directions)
            # For X: increases going to the left from center
            # For Y: increases going up from center
            if hasattr(self, 'image_obj') and self.image_obj is not None:
                img_height = self.image_obj.get_array().shape[0]
                img_width = self.image_obj.get_array().shape[1]
                
                # Convert to distances from center in pixels
                center_x = img_width / 2
                center_y = img_height / 2
                
                delta_x_pixels = center_x - event.xdata  # Positive when moving left from center
                delta_y_pixels = center_y - event.ydata  # Positive when moving down from center (in matplotlib coords)
                
                # Convert to microscope coordinates
                # In SEM microscope coordinates: 
                # - Moving right decreases X (opposite of pixel coordinates)
                # - Moving down decreases Y (opposite of pixel coordinates)
                microscope_x = self.overview_center_x - delta_x_pixels * self.um_per_pixel_x  # Note the minus sign - moving right decreases X
                microscope_y = self.overview_center_y + delta_y_pixels * self.um_per_pixel_y  # Note no minus sign - moving down decreases Y
                
                # Display with full precision
                self.coord_text.set_text(f'Pixel: ({event.xdata:.1f}, {event.ydata:.1f}) | Microscope: ({microscope_x}, {microscope_y})μm')
            else:
                self.coord_text.set_text(f'Pixel: ({event.xdata:.1f}, {event.ydata:.1f})')
            
            self.draw_idle()
    
    def on_scroll(self, event):
        """Handle mouse scroll for zooming."""
        # Matplotlib's zoom is handled by the navigation toolbar
        pass
    
    def on_button_press(self, event):
        """Handle mouse click."""
        # For custom click handling if needed
        pass
    
    def reset_view(self):
        """Reset the view to show the entire image."""
        if self.image_obj:
            self.axes.set_xlim(0, self.image_obj.get_array().shape[1])
            self.axes.set_ylim(self.image_obj.get_array().shape[0], 0)
            self.draw_idle()


class CoordinateDisplayDialog(QtWidgets.QDialog):
    """Dialog to display mouse coordinates and image pixel values."""
    
    def __init__(self, parent=None):
        """Initialize the dialog."""
        super().__init__(parent)
        self.setWindowTitle("Coordinates Info")
        self.setMinimumWidth(300)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Coordinate labels
        self.coord_label = QtWidgets.QLabel("Position: (-, -)")
        self.value_label = QtWidgets.QLabel("Pixel Value: -")
        
        layout.addWidget(self.coord_label)
        layout.addWidget(self.value_label)
        
        # Close button
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)
    
    def update_coordinates(self, x, y, value=None):
        """Update the coordinate display."""
        self.coord_label.setText(f"Position: ({x:.1f}, {y:.1f})")
        
        if value is not None:
            if isinstance(value, (tuple, list, np.ndarray)) and len(value) >= 3:
                self.value_label.setText(f"Pixel Value: RGB({int(value[0])}, {int(value[1])}, {int(value[2])})")
            else:
                self.value_label.setText(f"Pixel Value: {value}")
        else:
            self.value_label.setText("Pixel Value: -")


class ImageLocationTableDialog(QtWidgets.QDialog):
    """Dialog to display and select image locations."""
    
    # Signal to indicate when locations have been selected
    locations_selected = QtCore.Signal(list)
    
    def __init__(self, image_data, parent=None):
        """
        Initialize the dialog.
        
        Args:
            image_data: List of dictionaries with image metadata
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Session Image Locations")
        self.setMinimumSize(800, 600)
        
        # Store image data
        self.image_data = image_data
        self.selected_indices = []
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Create table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Select", "Filename", "Magnification", "X Coordinate (μm)", "Y Coordinate (μm)", "Detector"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Set column widths
        self.table.setColumnWidth(0, 60)  # Select checkbox
        self.table.setColumnWidth(1, 200)  # Filename
        self.table.setColumnWidth(2, 100)  # Magnification
        self.table.setColumnWidth(3, 100)  # X Position
        self.table.setColumnWidth(4, 100)  # Y Position
        self.table.setColumnWidth(5, 100)  # Detector
        
        layout.addWidget(self.table)
        
        # Create button layout
        button_layout = QtWidgets.QHBoxLayout()
        
        # Selection buttons
        self.select_all_button = QtWidgets.QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_button)
        
        self.select_none_button = QtWidgets.QPushButton("Select None")
        self.select_none_button.clicked.connect(self.select_none)
        button_layout.addWidget(self.select_none_button)
        
        self.select_low_mag_button = QtWidgets.QPushButton("Select Low Mag (<500x)")
        self.select_low_mag_button.clicked.connect(self.select_low_mag)
        button_layout.addWidget(self.select_low_mag_button)
        
        # Spacer
        button_layout.addStretch()
        
        # Apply and Cancel buttons
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_selection)
        button_layout.addWidget(self.apply_button)
        
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Populate table
        self.populate_table()
    
    def populate_table(self):
        """Populate the table with image data."""
        self.table.setRowCount(len(self.image_data))
        
        for row, img_data in enumerate(self.image_data):
            # Create checkbox
            checkbox = QtWidgets.QTableWidgetItem()
            checkbox.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            checkbox.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row, 0, checkbox)
            
            # Add image data
            filename = os.path.basename(img_data.get("path", ""))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(filename))
            
            # Get metadata
            metadata_dict = img_data.get("metadata_dict", {})
            
            # Magnification
            mag = metadata_dict.get("magnification", "Unknown")
            mag_item = QtWidgets.QTableWidgetItem(str(mag))
            self.table.setItem(row, 2, mag_item)
            
            # Position - First check for sample position (from metadata_extractor.py)
            # In microscope coordinates, y increases going up and x increases going to the left
            # NOTE: sample_position_x/y are in METERS, need to convert to MICROMETERS
            x_coordinate = metadata_dict.get("sample_position_x", None)
            y_coordinate = metadata_dict.get("sample_position_y", None)
            
            # Convert sample_position from meters to micrometers
            if x_coordinate is not None and y_coordinate is not None:
                # Check if values are very small (likely in meters)
                if abs(x_coordinate) < 1 and abs(y_coordinate) < 1:
                    # Convert from meters to micrometers (multiply by 1,000,000)
                    x_coordinate = x_coordinate * 1000000
                    y_coordinate = y_coordinate * 1000000
                    logger.info(f"Converted sample position from meters to micrometers: ({x_coordinate}, {y_coordinate})μm")
            
            # If sample position is not available, try stage position
            if not x_coordinate or not y_coordinate:
                x_coordinate = metadata_dict.get("stage_position_x", None)
                y_coordinate = metadata_dict.get("stage_position_y", None)
            
            # If stage position is not available, try stitch offsets
            if not x_coordinate or not y_coordinate:
                x_coordinate = metadata_dict.get("stitch_offset_x", None)
                y_coordinate = metadata_dict.get("stitch_offset_y", None)
                
            # If all else fails, check if there are any keys that might contain position information
            if not x_coordinate or not y_coordinate:
                for key in metadata_dict:
                    if "position_x" in key.lower() or "pos_x" in key.lower() or "posx" in key.lower():
                        x_coordinate = metadata_dict[key]
                    if "position_y" in key.lower() or "pos_y" in key.lower() or "posy" in key.lower():
                        y_coordinate = metadata_dict[key]
            
            # Format positions to μm with full precision if they're numeric
            try:
                # Keep full precision of the coordinates
                x_coordinate_str = f"{float(x_coordinate)}" if x_coordinate is not None else ""
                y_coordinate_str = f"{float(y_coordinate)}" if y_coordinate is not None else ""
            except (ValueError, TypeError):
                x_coordinate_str = str(x_coordinate) if x_coordinate is not None else ""
                y_coordinate_str = str(y_coordinate) if y_coordinate is not None else ""
                
            # Debug info
            if x_coordinate is not None and y_coordinate is not None:
                logger.info(f"Image {filename} coordinates: ({x_coordinate_str}, {y_coordinate_str})μm")
            else:
                logger.warning(f"No coordinates found for image {filename}")
                
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(x_coordinate_str))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(y_coordinate_str))
            
            # Detector
            detector = metadata_dict.get("detector", metadata_dict.get("mode", "Unknown"))
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(str(detector)))
    
    def select_all(self):
        """Select all images."""
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(QtCore.Qt.Checked)
    
    def select_none(self):
        """Deselect all images."""
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(QtCore.Qt.Unchecked)
    
    def select_low_mag(self):
        """Select only low magnification images (<500x)."""
        for row in range(self.table.rowCount()):
            mag_text = self.table.item(row, 2).text()
            try:
                mag = float(mag_text.replace('x', '').strip())
                if mag < 500:
                    self.table.item(row, 0).setCheckState(QtCore.Qt.Checked)
                else:
                    self.table.item(row, 0).setCheckState(QtCore.Qt.Unchecked)
            except ValueError:
                # If can't convert to number, uncheck
                self.table.item(row, 0).setCheckState(QtCore.Qt.Unchecked)
    
    def apply_selection(self):
        """Apply the current selection and emit signal."""
        selected_indices = []
        
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == QtCore.Qt.Checked:
                selected_indices.append(row)
        
        self.selected_indices = selected_indices
        self.locations_selected.emit(selected_indices)
        self.accept()


class AnnotateOverviewPanel(QtWidgets.QWidget):
    """
    Panel for annotating overview images with a metadata data bar.
    Uses Matplotlib for enhanced visualization and interaction.
    """
    
    # Custom signals
    grid_created = QtCore.Signal(object, object)  # Image and collection
    
    def __init__(self, session_manager):
        """
        Initialize the annotate overview panel.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__()
        
        self.session_manager = session_manager
        self.workflow = None
        self.current_collection = None
        self.annotations = []
        self.selected_locations = []
        self.coord_dialog = None
        
        # Initialize UI
        self._init_ui()
        
        logger.info("AnnotateOverview panel initialized with Matplotlib support")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Create top section with session info and controls
        top_layout = QtWidgets.QHBoxLayout()
        
        # Session info
        info_layout = QtWidgets.QVBoxLayout()
        
        session_layout = QtWidgets.QHBoxLayout()
        session_layout.addWidget(QtWidgets.QLabel("Session:"))
        self.session_label = QtWidgets.QLabel("No session loaded")
        session_layout.addWidget(self.session_label, 1)
        info_layout.addLayout(session_layout)
        
        # Add overview selection controls
        overview_layout = QtWidgets.QHBoxLayout()
        overview_layout.addWidget(QtWidgets.QLabel("Overview Image:"))
        self.overview_combo = QtWidgets.QComboBox()
        self.overview_combo.currentIndexChanged.connect(self._on_overview_selected)
        overview_layout.addWidget(self.overview_combo, 1)
        
        self.locate_button = QtWidgets.QPushButton("Locate Image...")
        self.locate_button.clicked.connect(self._on_locate_overview_clicked)
        overview_layout.addWidget(self.locate_button)
        
        info_layout.addLayout(overview_layout)
        
        top_layout.addLayout(info_layout)
        
        # Annotation options
        options_layout = QtWidgets.QVBoxLayout()
        
        # Data bar checkbox
        self.include_data_bar_check = QtWidgets.QCheckBox("Include Data Bar")
        self.include_data_bar_check.setChecked(True)
        self.include_data_bar_check.stateChanged.connect(self._refresh_preview)
        options_layout.addWidget(self.include_data_bar_check)
        
        # Mark session images checkbox
        self.mark_images_check = QtWidgets.QCheckBox("Mark Session Images")
        self.mark_images_check.setChecked(True)
        self.mark_images_check.stateChanged.connect(self._refresh_preview)
        options_layout.addWidget(self.mark_images_check)
        
        # Select images to mark button
        self.select_images_button = QtWidgets.QPushButton("Select Images to Mark...")
        self.select_images_button.clicked.connect(self._on_select_images_clicked)
        options_layout.addWidget(self.select_images_button)
        
        top_layout.addLayout(options_layout)
        
        main_layout.addLayout(top_layout)
        
        # Create matplotlib canvas for overview image
        self.canvas_layout = QtWidgets.QVBoxLayout()
        
        # Create matplotlib figure and canvas
        self.canvas = MatplotlibCanvas(self, width=8, height=6, dpi=100)
        self.canvas_layout.addWidget(self.canvas)
        
        # Create matplotlib toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.canvas_layout.addWidget(self.toolbar)
        
        # Add custom buttons to the toolbar area
        toolbar_buttons = QtWidgets.QHBoxLayout()
        
        # Add coordinate display button
        self.show_coords_button = QtWidgets.QPushButton("Show Coordinates")
        self.show_coords_button.clicked.connect(self._show_coordinates_dialog)
        toolbar_buttons.addWidget(self.show_coords_button)
        
        # Add refresh button
        self.refresh_button = QtWidgets.QPushButton("Refresh Preview")
        self.refresh_button.clicked.connect(self._refresh_preview)
        toolbar_buttons.addWidget(self.refresh_button)
        
        self.canvas_layout.addLayout(toolbar_buttons)
        
        main_layout.addLayout(self.canvas_layout, 1)  # Give the canvas more space
        
        # Add bottom controls
        bottom_layout = QtWidgets.QHBoxLayout()
        
        # Add action buttons
        self.refresh_images_button = QtWidgets.QPushButton("Refresh Images")
        self.refresh_images_button.clicked.connect(self.discover_collections)
        bottom_layout.addWidget(self.refresh_images_button)
        
        bottom_layout.addStretch()
        
        # Export button
        self.export_button = QtWidgets.QPushButton("Export Annotated Overview")
        self.export_button.clicked.connect(self._on_export_clicked)
        self.export_button.setEnabled(False)
        bottom_layout.addWidget(self.export_button)
        
        main_layout.addLayout(bottom_layout)
        
        # Set initial state
        self.canvas.setEnabled(False)
        self.toolbar.setEnabled(False)
        self.show_coords_button.setEnabled(False)
    
    def set_workflow(self, workflow):
        """
        Set the workflow to use for this panel.
        
        Args:
            workflow: AnnotateOverview workflow instance
        """
        self.workflow = workflow
        
        # Discover collections if a session is loaded
        if self.session_manager and self.session_manager.current_session:
            self.discover_collections()
    
    def update_session_info(self):
        """Update session information display."""
        if self.session_manager and self.session_manager.current_session:
            session_id = os.path.basename(self.session_manager.session_folder)
            sample_id = self.session_manager.current_session.sample_id or "Unknown"
            self.session_label.setText(f"{session_id} - Sample: {sample_id}")
        else:
            self.session_label.setText("No session loaded")
    
    def discover_collections(self):
        """Discover collections for the AnnotateOverview workflow."""
        self.overview_combo.clear()
        self.current_collection = None
        
        if not self.workflow or not self.session_manager or not self.session_manager.current_session:
            return
        
        try:
            # Update session info
            self.update_session_info()
            
            # Show progress dialog
            progress = QtWidgets.QProgressDialog(
                "Discovering overview images...",
                "Cancel",
                0,
                100,
                self
            )
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setValue(10)
            
            # Discover collections
            collections = self.workflow.discover_collections()
            progress.setValue(90)
            
            # Update UI with collections
            if collections:
                self.current_collection = collections[0]
                
                # Add images to combo box
                for i, img_data in enumerate(self.current_collection["images"]):
                    # Get metadata
                    metadata_dict = img_data["metadata_dict"]
                    
                    # Get filename
                    filename = os.path.basename(img_data["path"])
                    
                    # Get magnification
                    mag = metadata_dict.get("magnification", "Unknown")
                    
                    # Create item text
                    item_text = f"{filename} ({mag}x)"
                    if img_data.get("is_overview", False):
                        item_text += " [Overview]"
                    
                    # Add to combo box
                    self.overview_combo.addItem(item_text, i)
                
                # Enable UI elements
                self.canvas.setEnabled(True)
                self.toolbar.setEnabled(True)
                self.show_coords_button.setEnabled(True)
                self.export_button.setEnabled(True)
                
                # Select first item
                if self.overview_combo.count() > 0:
                    self.overview_combo.setCurrentIndex(0)
                
                logger.info(f"Found {len(self.current_collection['images'])} overview images")
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "No Overview Images",
                    "No overview images found in this session.\n\n"
                    "Use the 'Locate Image...' button to manually select an overview image."
                )
                
                # Disable UI elements that need a collection
                self.canvas.setEnabled(False)
                self.toolbar.setEnabled(False)
                self.show_coords_button.setEnabled(False)
                self.export_button.setEnabled(False)
            
            progress.setValue(100)
            
        except Exception as e:
            logger.error(f"Error discovering overview images: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Discovery Error",
                f"Error discovering overview images: {str(e)}"
            )
    
    def _on_overview_selected(self, index):
        """
        Handle overview image selection change.
        
        Args:
            index: Selected index in the combo box
        """
        if index < 0 or not self.current_collection:
            return
        
        # Get selected image index from combo box data
        image_index = self.overview_combo.itemData(index)
        
        # Update preview
        self._refresh_preview()
    
    def _show_coordinates_dialog(self):
        """Show the coordinates dialog."""
        if not self.coord_dialog:
            self.coord_dialog = CoordinateDisplayDialog(self)
            
        self.coord_dialog.show()
    
    def _on_select_images_clicked(self):
        """Handle select images button click."""
        if not self.current_collection:
            return
        
        # Get session images (excluding overview images)
        session_images = []
        error_messages = []
        metadata_count = 0
        no_position_count = 0
        
        if self.session_manager and self.session_manager.metadata:
            metadata_count = len(self.session_manager.metadata)
            # Get the selected overview image path
            index = self.overview_combo.currentIndex()
            if index < 0:
                return
                
            image_index = self.overview_combo.itemData(index)
            overview_path = self.current_collection["images"][image_index]["path"]
            
            # Add all images from the session folder directly to ensure we're not missing any
            session_folder = self.session_manager.session_folder
            all_session_files = []
            
            try:
                # Find all image files in the session folder
                for root, _, files in os.walk(session_folder):
                    for file in files:
                        if file.lower().endswith(('.tif', '.tiff', '.jpg', '.jpeg', '.png', '.bmp')):
                            img_path = os.path.join(root, file)
                            # Skip the overview image itself
                            if img_path == overview_path:
                                continue
                            all_session_files.append(img_path)
                
                logger.info(f"Found {len(all_session_files)} image files in session folder")
            except Exception as e:
                error_messages.append(f"Error scanning session folder: {str(e)}")
            
            # Process images with metadata first
            for img_path, metadata in self.session_manager.metadata.items():
                # Skip the overview image itself
                if img_path == overview_path:
                    continue
                
                # Skip images that don't have valid metadata
                if not metadata or not metadata.is_valid():
                    continue
                
                # Try to get position data
                has_position = False
                position_info = {}
                
                # Check various possible position attributes
                # First check for sample_position - this is the primary field from metadata_extractor.py
                if hasattr(metadata, 'sample_position_x') and hasattr(metadata, 'sample_position_y'):
                    sample_x = metadata.sample_position_x
                    sample_y = metadata.sample_position_y
                    if sample_x is not None and sample_y is not None:
                        position_info["sample_position_x"] = sample_x
                        position_info["sample_position_y"] = sample_y
                        has_position = True
                        logger.info(f"Found sample position for {os.path.basename(img_path)}: ({sample_x:.2f}, {sample_y:.2f})μm")
                
                # Try stage positions if sample_position is not available
                if not has_position and hasattr(metadata, 'stage_position_x') and hasattr(metadata, 'stage_position_y'):
                    stage_x = metadata.stage_position_x
                    stage_y = metadata.stage_position_y
                    if stage_x is not None and stage_y is not None:
                        position_info["stage_position_x"] = stage_x
                        position_info["stage_position_y"] = stage_y
                        has_position = True
                        logger.info(f"Using stage position for {os.path.basename(img_path)}: ({stage_x:.2f}, {stage_y:.2f})μm")
                
                # Try stitch coordinates if stage positions aren't available
                if not has_position and hasattr(metadata, 'stitch_offset_x') and hasattr(metadata, 'stitch_offset_y'):
                    stitch_x = metadata.stitch_offset_x
                    stitch_y = metadata.stitch_offset_y
                    if stitch_x is not None and stitch_y is not None:
                        position_info["stage_position_x"] = stitch_x  # Use the stage_position field for display
                        position_info["stage_position_y"] = stitch_y
                        has_position = True
                        logger.info(f"Using stitch position for {os.path.basename(img_path)}: ({stitch_x:.2f}, {stitch_y:.2f})μm")
                
                # As a last resort, check dictionary values if available
                if not has_position and hasattr(metadata, 'to_dict'):
                    md_dict = metadata.to_dict()
                    # Check sample position first in dictionary
                    if 'sample_position_x' in md_dict and 'sample_position_y' in md_dict:
                        sample_x = md_dict.get('sample_position_x')
                        sample_y = md_dict.get('sample_position_y')
                        if sample_x is not None and sample_y is not None:
                            position_info["sample_position_x"] = sample_x
                            position_info["sample_position_y"] = sample_y
                            has_position = True
                            logger.info(f"Found sample position from dict for {os.path.basename(img_path)}: ({sample_x:.2f}, {sample_y:.2f})μm")
                    # Then check stage position
                    elif 'stage_position_x' in md_dict and 'stage_position_y' in md_dict:
                        stage_x = md_dict.get('stage_position_x')
                        stage_y = md_dict.get('stage_position_y')
                        if stage_x is not None and stage_y is not None:
                            position_info["stage_position_x"] = stage_x
                            position_info["stage_position_y"] = stage_y
                            has_position = True
                    # Finally try stitch offsets
                    elif 'stitch_offset_x' in md_dict and 'stitch_offset_y' in md_dict:
                        stitch_x = md_dict.get('stitch_offset_x')
                        stitch_y = md_dict.get('stitch_offset_y')
                        if stitch_x is not None and stitch_y is not None:
                            position_info["stage_position_x"] = stitch_x
                            position_info["stage_position_y"] = stitch_y
                            has_position = True
                
                # If we found position information, add the image
                if has_position:
                    # Create metadata dictionary including position info
                    metadata_dict = metadata.to_dict()
                    metadata_dict.update(position_info)
                    
                    # Add to session images
                    session_images.append({
                        "path": img_path,
                        "metadata_dict": metadata_dict
                    })
                else:
                    no_position_count += 1
            
            # If we couldn't find many images with position data, use all session images as a fallback
            if len(session_images) < 2 and len(all_session_files) > 0:
                logger.warning(f"Found only {len(session_images)} images with position data. Adding all {len(all_session_files)} session images as fallback.")
                
                # Add all session files without position data
                for img_path in all_session_files:
                    # Skip if already included
                    if any(img["path"] == img_path for img in session_images):
                        continue
                    
                    # Create minimal metadata
                    filename = os.path.basename(img_path)
                    
                    # Default to center if no position data
                    session_images.append({
                        "path": img_path,
                        "metadata_dict": {
                            "filename": filename,
                            "magnification": "Unknown",
                            "stitch_x": 0,  # Center position as fallback
                            "stitch_y": 0   # Center position as fallback
                        }
                    })
        
        if not session_images:
            # Provide detailed error information
            details = "\n".join([
                f"Total metadata entries: {metadata_count}",
                f"Images without position data: {no_position_count}",
            ] + error_messages)
            
            QtWidgets.QMessageBox.information(
                self,
                "No Images",
                f"No session images with position data found.\n\nDetails:\n{details}"
            )
            return
        
        # Show the image location table dialog
        dialog = ImageLocationTableDialog(session_images, self)
        dialog.locations_selected.connect(self._on_locations_selected)
        dialog.exec_()
    
    def _on_locations_selected(self, selected_indices):
        """
        Handle locations selected from dialog.
        
        Args:
            selected_indices: List of selected image indices
        """
        # Store selected locations
        self.selected_locations = selected_indices
        
        # Update preview
        self._refresh_preview()
    
    def _on_locate_overview_clicked(self):
        """
        Handle locate overview image button click.
        Opens a file dialog to manually select an overview image.
        """
        if not self.workflow or not self.session_manager or not self.session_manager.current_session:
            QtWidgets.QMessageBox.warning(
                self,
                "No Session",
                "Please open a session folder first."
            )
            return
        
        # Show file dialog to select image file
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Overview Image",
            self.session_manager.session_folder,
            "Image Files (*.tif *.tiff *.jpg *.jpeg *.bmp *.png);;All Files (*.*)"
        )
        
        if not file_path:
            return  # User canceled
        
        try:
            # Create minimal metadata for the manually selected image
            filename = os.path.basename(file_path)
            
            # Create collection if it doesn't exist
            if not self.current_collection:
                self.current_collection = {
                    "type": "AnnotateOverview",
                    "id": "annotate_overview_collection",
                    "images": [],
                    "description": "Manually selected overview image"
                }
            
            # Create metadata dict
            metadata_dict = {
                "image_path": file_path,
                "filename": filename,
                "acquisition_date": "",  # Will be filled with current date when used
                "magnification": "Unknown",
                "working_distance_mm": "Unknown",
                "high_voltage_kV": "Unknown",
                "detector": "Unknown"
            }
            
            # Try to get metadata if available in session
            if self.session_manager.metadata and file_path in self.session_manager.metadata:
                metadata = self.session_manager.metadata[file_path]
                if metadata and metadata.is_valid():
                    metadata_dict = metadata.to_dict()
            
            # Create image data
            image_data = {
                "path": file_path,
                "metadata_dict": metadata_dict,
                "is_overview": True,
                "magnification": metadata_dict.get("magnification", "Unknown")
            }
            
            # Check if this image is already in the collection
            existing_index = -1
            if self.current_collection.get("images"):
                for i, img in enumerate(self.current_collection["images"]):
                    if img["path"] == file_path:
                        existing_index = i
                        break
            
            if existing_index >= 0:
                # Update existing image
                self.current_collection["images"][existing_index] = image_data
            else:
                # Add to collection
                self.current_collection["images"].append(image_data)
            
            # Update UI
            self.overview_combo.clear()
            
            # Add images to combo box
            for i, img_data in enumerate(self.current_collection["images"]):
                # Get metadata
                img_metadata_dict = img_data["metadata_dict"]
                
                # Get filename
                img_filename = os.path.basename(img_data["path"])
                
                # Get magnification
                mag = img_metadata_dict.get("magnification", "Unknown")
                
                # Create item text
                item_text = f"{img_filename} ({mag}x)"
                if img_data.get("is_overview", False):
                    item_text += " [Overview]"
                
                # Add to combo box
                self.overview_combo.addItem(item_text, i)
            
            # Select the manually added image
            for i in range(self.overview_combo.count()):
                image_index = self.overview_combo.itemData(i)
                if self.current_collection["images"][image_index]["path"] == file_path:
                    self.overview_combo.setCurrentIndex(i)
                    break
            
            # Enable UI elements
            self.canvas.setEnabled(True)
            self.toolbar.setEnabled(True)
            self.show_coords_button.setEnabled(True)
            self.export_button.setEnabled(True)
            
            logger.info(f"Manually selected overview image: {file_path}")
            
            # Preview the image
            self._refresh_preview()
            
        except Exception as e:
            logger.error(f"Error loading manually selected image: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Image Loading Error",
                f"Error loading the selected image: {str(e)}"
            )
    
    def _refresh_preview(self):
        """Update the preview with the current settings."""
        if not self.workflow or not self.current_collection:
            return
        
        # Get selected image index
        index = self.overview_combo.currentIndex()
        if index < 0:
            return
            
        image_index = self.overview_combo.itemData(index)
        
        # Create a modified collection with just the selected image
        preview_collection = {
            "type": "AnnotateOverview",
            "id": self.current_collection["id"],
            "images": [self.current_collection["images"][image_index]],
            "description": self.current_collection["description"]
        }
        
        # Create options
        options = {
            "annotations": self.annotations,
            "include_data_bar": self.include_data_bar_check.isChecked(),
            "mark_session_images": self.mark_images_check.isChecked(),
            "selected_locations": self.selected_locations if self.selected_locations else None
        }
        
        try:
            # Create grid visualization
            image = self.workflow.create_grid(preview_collection, None, options)
            
            if image:
                # Display the image in the matplotlib canvas
                self._display_image(image, preview_collection)
                
                # Emit signal with image and collection
                self.grid_created.emit(image, preview_collection)
                
                logger.info("Generated annotated overview preview")
            else:
                logger.error("Failed to generate annotated overview")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Preview Error",
                    "Failed to generate preview."
                )
        except Exception as e:
            logger.error(f"Error creating preview: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Preview Error",
                f"Error creating preview: {str(e)}"
            )
    
    def _display_image(self, pil_image, collection):
        """
        Display an image in the matplotlib canvas.
        
        Args:
            pil_image: PIL Image to display
            collection: Collection data
        """
        try:
            # Convert PIL image to numpy array
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            img_array = np.array(pil_image)
            
            # Clear the axes and display the new image
            self.canvas.axes.clear()
            self.canvas.image_obj = self.canvas.axes.imshow(img_array)
            
            # Get overview image microscope coordinates (center position) from metadata
            overview_stage_x = 0
            overview_stage_y = 0
            um_per_pixel_x = 1
            um_per_pixel_y = 1
            fov_width = 0
            
            try:
                if collection and collection.get("images") and collection["images"][0]:
                    img_data = collection["images"][0]
                    img_path = img_data.get("path", "")
                    metadata_dict = img_data.get("metadata_dict", {})
                    
                    # Try for sample_position first (convert from meters to micrometers)
                    if "sample_position_x" in metadata_dict and "sample_position_y" in metadata_dict:
                        sample_x = float(metadata_dict["sample_position_x"])
                        sample_y = float(metadata_dict["sample_position_y"])
                        
                        # Check if values are very small (likely in meters)
                        if abs(sample_x) < 1 and abs(sample_y) < 1:
                            # Convert from meters to micrometers
                            overview_stage_x = sample_x * 1000000
                            overview_stage_y = sample_y * 1000000
                            logger.info(f"Overview center coordinates from sample_position: ({overview_stage_x}, {overview_stage_y})μm (converted from meters)")
                        else:
                            overview_stage_x = sample_x
                            overview_stage_y = sample_y
                            logger.info(f"Overview center coordinates from sample_position: ({overview_stage_x}, {overview_stage_y})μm")
                    
                    # If sample_position not found, try stage_position
                    elif "stage_position_x" in metadata_dict and "stage_position_y" in metadata_dict:
                        overview_stage_x = float(metadata_dict["stage_position_x"])
                        overview_stage_y = float(metadata_dict["stage_position_y"])
                        logger.info(f"Overview center coordinates from stage_position: ({overview_stage_x}, {overview_stage_y})μm")
                    
                    # Try to get field of view for scaling
                    if "field_of_view_width" in metadata_dict:
                        fov_width = float(metadata_dict["field_of_view_width"])
                        # Calculate um per pixel
                        if fov_width > 0 and pil_image.width > 0:
                            um_per_pixel_x = fov_width / pil_image.width
                            um_per_pixel_y = um_per_pixel_x  # Assume square pixels
                            logger.info(f"Scale: {um_per_pixel_x}μm/pixel")
            except Exception as e:
                logger.error(f"Error extracting microscope coordinates: {str(e)}")
            
            # Set microscope coordinate system in the canvas
            self.canvas.set_microscope_coordinates(
                overview_stage_x, 
                overview_stage_y,
                um_per_pixel_x,
                um_per_pixel_y
            )
            
            # Add rulers with larger font size for better visibility
            self.canvas.axes.set_xlabel('Pixels', fontsize=14)
            self.canvas.axes.set_ylabel('Pixels', fontsize=14)
            
            # Set tick label sizes for better visibility
            self.canvas.axes.tick_params(axis='both', which='major', labelsize=12)
            
            # Set title with filename and center coordinates
            if collection and collection.get("images") and len(collection["images"]) > 0:
                img_data = collection["images"][0]
                filename = os.path.basename(img_data.get("path", ""))
                mag = img_data.get("metadata_dict", {}).get("magnification", "")
                
                # Create coordinate display string
                coord_display = ""
                if "sample_position_x" in metadata_dict and "sample_position_y" in metadata_dict:
                    # Get the raw sample position values
                    sample_x = metadata_dict["sample_position_x"]
                    sample_y = metadata_dict["sample_position_y"]
                    
                    # Check if values need to be converted from meters to micrometers
                    if abs(float(sample_x)) < 1 and abs(float(sample_y)) < 1:
                        sample_x_um = float(sample_x) * 1000000
                        sample_y_um = float(sample_y) * 1000000
                        coord_display = f" - Center: ({sample_x_um}, {sample_y_um})μm"
                    else:
                        coord_display = f" - Center: ({sample_x}, {sample_y})μm"
                
                # Set the title with filename, magnification, and coordinates
                if mag:
                    title = f"{filename} ({mag}x){coord_display}"
                else:
                    title = f"{filename}{coord_display}"
                    
                self.canvas.axes.set_title(title, fontsize=14)
                
                # Also add a text annotation at the center of the image
                if coord_display:
                    # Add a marker at the center with coordinates
                    center_x = img_array.shape[1] / 2
                    center_y = img_array.shape[0] / 2
                    self.canvas.axes.plot(center_x, center_y, 'ro', markersize=8)  # Red circle at center
                    
                    # Add a label with coordinates near center point
                    self.canvas.axes.annotate(
                        f"Center: ({overview_stage_x}, {overview_stage_y})μm", 
                        xy=(center_x, center_y), 
                        xytext=(center_x + 20, center_y + 20),
                        fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.8),
                        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2")
                    )
            
            # Draw gridlines for better position reference
            self.canvas.axes.grid(True, linestyle='--', alpha=0.6)
            
            # Update the canvas
            self.canvas.draw()
            
            # Reset view to show the entire image
            self.canvas.reset_view()
            
            # Update coordinate dialog if open
            if self.coord_dialog and self.coord_dialog.isVisible():
                # Just ensure it's showing the correct initial values
                self.coord_dialog.update_coordinates(0, 0)
            
        except Exception as e:
            logger.error(f"Error displaying image in matplotlib: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Display Error",
                f"Error displaying image: {str(e)}"
            )
    
    def _on_export_clicked(self):
        """Handle export button click."""
        if not self.workflow or not self.current_collection:
            return
        
        # Get selected image index
        index = self.overview_combo.currentIndex()
        if index < 0:
            return
            
        image_index = self.overview_combo.itemData(index)
        
        # Create a modified collection with just the selected image
        export_collection = {
            "type": "AnnotateOverview",
            "id": self.current_collection["id"],
            "images": [self.current_collection["images"][image_index]],
            "description": self.current_collection["description"]
        }
        
        # Create options
        options = {
            "annotations": self.annotations,
            "include_data_bar": self.include_data_bar_check.isChecked(),
            "mark_session_images": self.mark_images_check.isChecked(),
            "selected_locations": self.selected_locations if self.selected_locations else None
        }
        
        try:
            # Create grid visualization
            image = self.workflow.create_grid(export_collection, None, options)
            
            if image:
                # Export the grid visualization
                image_path, caption_path = self.workflow.export_grid(image, export_collection)
                
                QtWidgets.QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Annotated overview exported successfully:\n"
                    f"Image: {os.path.basename(image_path)}\n"
                    f"Caption: {os.path.basename(caption_path)}"
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Export Error",
                    "Failed to generate annotated overview for export."
                )
        except Exception as e:
            logger.error(f"Error exporting annotated overview: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Export Error",
                f"Error exporting annotated overview: {str(e)}"
            )
