"""
Grid visualization preview panel for SEM Image Workflow Manager.
"""

import os
import tempfile
from PIL import Image
from qtpy import QtWidgets, QtCore, QtGui
from utils.logger import Logger

logger = Logger(__name__)


class GridPreviewPanel(QtWidgets.QGroupBox):
    """
    Panel for previewing and exporting grid visualizations.
    """
    
    # Custom signals
    export_requested = QtCore.Signal(object, object)  # Grid image, collection
    
    def __init__(self):
        """Initialize grid preview panel."""
        super().__init__("Grid Preview")
        
        self.grid_image = None
        self.current_collection = None
        self.zoom_factor = 1.0
        
        # Initialize UI
        self._init_ui()
        
        logger.info("Grid preview panel initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Zoom controls
        zoom_layout = QtWidgets.QHBoxLayout()
        
        zoom_out_btn = QtWidgets.QPushButton("-")
        zoom_out_btn.setMaximumWidth(30)
        zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_layout.addWidget(zoom_out_btn)
        
        self.zoom_label = QtWidgets.QLabel("100%")
        self.zoom_label.setAlignment(QtCore.Qt.AlignCenter)
        zoom_layout.addWidget(self.zoom_label)
        
        zoom_in_btn = QtWidgets.QPushButton("+")
        zoom_in_btn.setMaximumWidth(30)
        zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_layout.addWidget(zoom_in_btn)
        
        reset_zoom_btn = QtWidgets.QPushButton("Fit")
        reset_zoom_btn.setMaximumWidth(40)
        reset_zoom_btn.clicked.connect(self._reset_zoom)
        zoom_layout.addWidget(reset_zoom_btn)
        
        layout.addLayout(zoom_layout)
        
        # Preview scroll area
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(QtCore.Qt.AlignCenter)
        # Set minimum size for the scroll area to make it larger
        scroll_area.setMinimumSize(800, 600)

        self.preview_widget = QtWidgets.QWidget()
        preview_layout = QtWidgets.QVBoxLayout(self.preview_widget)

        self.preview_label = QtWidgets.QLabel("No preview available")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setMinimumSize(700, 500)  # Larger minimum size for preview label

        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()

        scroll_area.setWidget(self.preview_widget)
        layout.addWidget(scroll_area)
        
        # Caption preview
        caption_group = QtWidgets.QGroupBox("Caption")
        caption_layout = QtWidgets.QVBoxLayout(caption_group)
        
        self.caption_edit = QtWidgets.QTextEdit()
        self.caption_edit.setReadOnly(True)
        self.caption_edit.setMaximumHeight(80)
        caption_layout.addWidget(self.caption_edit)
        
        layout.addWidget(caption_group)
        
        # Export button
        self.export_button = QtWidgets.QPushButton("Export Grid")
        self.export_button.clicked.connect(self._on_export_clicked)
        self.export_button.setEnabled(False)
        layout.addWidget(self.export_button)
    
    def _zoom_in(self):
        """Zoom in to the preview image."""
        self.zoom_factor = min(self.zoom_factor * 1.2, 5.0)
        self._update_zoom()
    
    def _zoom_out(self):
        """Zoom out of the preview image."""
        self.zoom_factor = max(self.zoom_factor / 1.2, 0.2)
        self._update_zoom()
    
    def _reset_zoom(self):
        """Reset zoom to fit the preview."""
        self.zoom_factor = 1.0
        self._update_zoom()
    
    def _update_zoom(self):
        """Update the preview with the current zoom factor."""
        self.zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
        
        if self.grid_image:
            self._display_image(self.grid_image)
    
    def set_preview(self, image, collection):
        """
        Set the preview image and collection.
        
        Args:
            image (PIL.Image): Grid visualization image
            collection (dict): Collection data
        """
        self.grid_image = image
        self.current_collection = collection
        
        if image:
            self._display_image(image)
            
            # Generate caption
            self._update_caption()
            
            # Enable export button
            self.export_button.setEnabled(True)
        else:
            self.clear_preview()
    
    def _display_image(self, image):
        """
        Display the image in the preview label with the current zoom.
        
        Args:
            image (PIL.Image): Image to display
        """
        try:
            # Resize the image according to zoom factor
            if self.zoom_factor != 1.0:
                width = int(image.width * self.zoom_factor)
                height = int(image.height * self.zoom_factor)
                display_image = image.resize((width, height), Image.LANCZOS)
            else:
                display_image = image
            
            # Handle different versions of PIL/Pillow
            # Method 1: Use QImage directly
            qim = QtGui.QImage(display_image.tobytes(), 
                               display_image.width, 
                               display_image.height, 
                               display_image.width * 3,  # Assuming RGB (3 bytes per pixel)
                               QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(qim)
            
            # If the above fails, try other methods
            if pixmap.isNull():
                # Method 2: Save to temporary file and load
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_filename = temp_file.name
                temp_file.close()
                
                display_image.save(temp_filename)
                pixmap = QtGui.QPixmap(temp_filename)
                
                try:
                    os.unlink(temp_filename)  # Delete the temporary file
                except:
                    pass
            
            # Set the pixmap
            self.preview_label.setPixmap(pixmap)
            self.preview_label.setMinimumSize(pixmap.width(), pixmap.height())
            
        except Exception as e:
            logger.error(f"Error displaying image: {str(e)}")
            self.preview_label.setText(f"Error displaying preview: {str(e)}")
    
    def clear_preview(self):
        """Clear the preview image and caption."""
        self.grid_image = None
        self.current_collection = None
        
        self.preview_label.setText("No preview available")
        self.preview_label.setPixmap(QtGui.QPixmap())
        self.caption_edit.clear()
        
        # Disable export button
        self.export_button.setEnabled(False)
    
    def _update_caption(self):
        """Update the caption preview based on the current collection."""
        if not self.current_collection:
            self.caption_edit.clear()
            return
        
        # Generate caption
        try:
            workflow_type = self.current_collection.get("type", "Unknown")
            
            if workflow_type == "MagGrid":
                # MagGrid specific caption
                sample_id = self.current_collection.get("sample_id", "Unknown")
                mode = self.current_collection.get("mode", "Unknown")
                voltage = self.current_collection.get("high_voltage", "Unknown")
                mags = self.current_collection.get("magnifications", [])
                
                mag_str = ", ".join([f"{mag}x" for mag in mags])
                
                caption = f"Sample {sample_id} imaged with {mode} detector at {voltage} kV.\n"
                caption += f"Magnification series: {mag_str}."
            else:
                # Generic caption
                count = len(self.current_collection.get("images", []))
                caption = f"{workflow_type} visualization with {count} images."
            
            self.caption_edit.setText(caption)
        except Exception as e:
            logger.error(f"Error generating caption: {str(e)}")
            self.caption_edit.setText("Error generating caption.")
    
    def _on_export_clicked(self):
        """Handle export button click."""
        if not self.grid_image or not self.current_collection:
            return
        
        # Emit signal
        self.export_requested.emit(self.grid_image, self.current_collection)
