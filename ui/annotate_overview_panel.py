"""
Annotate Overview panel for SEM Image Workflow Manager.
Provides tools for annotating overview images with a metadata data bar.
Uses Matplotlib for enhanced visualization and interaction.
"""

import os
import datetime
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
    
    def __init__(self, image_data, match_results=None, parent=None):
        """
        Initialize the dialog.
        
        Args:
            image_data: List of dictionaries with image metadata
            match_results: Dictionary of template matching results (path -> results)
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Session Image Locations")
        self.setMinimumSize(1000, 700)
        
        # Store image data
        self.image_data = image_data
        self.match_results = match_results or {}
        self.selected_indices = []
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Create table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Select", "Filename", "Magnification", "Metadata X (μm)", "Metadata Y (μm)", 
            "Match X (px)", "Match Y (px)", "Confidence", "Detector"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Set column widths
        self.table.setColumnWidth(0, 60)   # Select checkbox
        self.table.setColumnWidth(1, 180)  # Filename
        self.table.setColumnWidth(2, 100)  # Magnification
        self.table.setColumnWidth(3, 100)  # Metadata X
        self.table.setColumnWidth(4, 100)  # Metadata Y
        self.table.setColumnWidth(5, 100)  # Match X
        self.table.setColumnWidth(6, 100)  # Match Y
        self.table.setColumnWidth(7, 100)  # Confidence
        self.table.setColumnWidth(8, 100)  # Detector
        
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
            filepath = img_data.get("path", "")
            filename = os.path.basename(filepath)
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
            
            # Add template matching results if available
            if filepath in self.match_results:
                match_info = self.match_results[filepath]
                
                # Match position
                match_x = match_info.get("center_x", "")
                match_y = match_info.get("center_y", "")
                match_confidence = match_info.get("confidence", "")
                
                # Add to table with highlighting based on confidence
                match_x_item = QtWidgets.QTableWidgetItem(str(match_x))
                match_y_item = QtWidgets.QTableWidgetItem(str(match_y))
                confidence_item = QtWidgets.QTableWidgetItem(f"{match_confidence:.3f}" if isinstance(match_confidence, float) else str(match_confidence))
                
                # Color code based on confidence
                if isinstance(match_confidence, float):
                    if match_confidence >= 0.8:
                        confidence_item.setBackground(QtGui.QColor(200, 255, 200))  # Light green for good matches
                    elif match_confidence >= 0.5:
                        confidence_item.setBackground(QtGui.QColor(255, 255, 200))  # Light yellow for moderate matches
                    else:
                        confidence_item.setBackground(QtGui.QColor(255, 200, 200))  # Light red for poor matches
                
                self.table.setItem(row, 5, match_x_item)
                self.table.setItem(row, 6, match_y_item)
                self.table.setItem(row, 7, confidence_item)
            else:
                # No match info
                self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(""))
            
            # Detector
            detector = metadata_dict.get("detector", metadata_dict.get("mode", "Unknown"))
            self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(str(detector)))
    
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


class LogWindow(QtWidgets.QDialog):
    """Window for displaying log messages."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Template Matching Log")
        self.setMinimumSize(800, 400)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Create log text area
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        font = QtGui.QFont("Courier New", 10)
        self.log_text.setFont(font)
        
        layout.addWidget(self.log_text)
        
        # Create button layout
        button_layout = QtWidgets.QHBoxLayout()
        
        # Clear button
        self.clear_button = QtWidgets.QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_button)
        
        # Save button
        self.save_button = QtWidgets.QPushButton("Save Log")
        self.save_button.clicked.connect(self.save_log)
        button_layout.addWidget(self.save_button)
        
        # Close button
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def add_log(self, message):
        """Add a message to the log."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.appendPlainText(f"[{timestamp}] {message}")
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def clear_log(self):
        """Clear the log."""
        self.log_text.clear()
    
    def save_log(self):
        """Save the log to a file."""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Log",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                
                QtWidgets.QMessageBox.information(
                    self,
                    "Save Successful",
                    f"Log saved successfully to {file_path}"
                )
            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Error saving log: {str(e)}"
                )


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
        self.log_window = None
        self.template_match_results = {}  # Store template matching results
        self.confidence_threshold = 0.8   # Default confidence threshold
        
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
        
        # Add rotation info
        rotation_info_layout = QtWidgets.QHBoxLayout()
        rotation_info_layout.addWidget(QtWidgets.QLabel("Scan Rotation:"))
        self.rotation_value_label = QtWidgets.QLabel("Unknown")
        rotation_info_layout.addWidget(self.rotation_value_label)
        info_layout.addLayout(rotation_info_layout)
        
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
        
        # Confidence threshold
        threshold_layout = QtWidgets.QHBoxLayout()
        threshold_layout.addWidget(QtWidgets.QLabel("Match Threshold:"))
        self.threshold_input = QtWidgets.QDoubleSpinBox()
        self.threshold_input.setRange(0.0, 1.0)
        self.threshold_input.setSingleStep(0.05)
        self.threshold_input.setValue(self.confidence_threshold)
        self.threshold_input.setDecimals(2)
        self.threshold_input.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(self.threshold_input)
        options_layout.addLayout(threshold_layout)
        
        # Rotation direction control
        rotation_layout = QtWidgets.QHBoxLayout()
        rotation_layout.addWidget(QtWidgets.QLabel("Rotation Direction:"))
        self.rotation_combo = QtWidgets.QComboBox()
        self.rotation_combo.addItem("Counter-Clockwise (CCW)", 1)
        self.rotation_combo.addItem("Clockwise (CW)", -1)
        self.rotation_combo.currentIndexChanged.connect(self._refresh_preview)
        rotation_layout.addWidget(self.rotation_combo)
        options_layout.addLayout(rotation_layout)
        
        # Select images to mark button
        buttons_layout = QtWidgets.QHBoxLayout()
        
        self.select_images_button = QtWidgets.QPushButton("Select Images to Mark...")
        self.select_images_button.clicked.connect(self._on_select_images_clicked)
        buttons_layout.addWidget(self.select_images_button)
        
        self.show_log_button = QtWidgets.QPushButton("Show Template Match Log")
        self.show_log_button.clicked.connect(self._show_log_window)
        buttons_layout.addWidget(self.show_log_button)
        
        options_layout.addLayout(buttons_layout)
        
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

    def _add_to_log(self, message):
        """Add a message to the log window."""
        # Create log window if it doesn't exist
        if not self.log_window:
            self.log_window = LogWindow(self)
        
        self.log_window.add_log(message)
    
    def _show_log_window(self):
        """Show the log window."""
        if not self.log_window:
            self.log_window = LogWindow(self)
            
        self.log_window.show()
    
    def _on_threshold_changed(self, value):
        """Handle threshold value change."""
        # Update the confidence threshold
        self.confidence_threshold = value
        
        # Refresh preview if we're displaying an image
        if self.current_collection:
            self._refresh_preview()
    
    def _show_coordinates_dialog(self):
        """Show the coordinates dialog."""
        if not self.coord_dialog:
            self.coord_dialog = CoordinateDisplayDialog(self)
            
        self.coord_dialog.show()
    
    def _refresh_preview(self):
        """Update the
