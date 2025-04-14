"""
Workflow selection and control panel for SEM Image Workflow Manager.
"""

from qtpy import QtWidgets, QtCore, QtGui
from utils.logger import Logger

logger = Logger(__name__)


class WorkflowPanel(QtWidgets.QGroupBox):
    """
    Panel for selecting workflows and managing collections.
    """
    
    # Custom signals
    workflow_selected = QtCore.Signal(str)  # Workflow name
    collection_selected = QtCore.Signal(object)  # Collection object
    create_grid_requested = QtCore.Signal(object, object, object)  # Collection, layout, options
    
    def __init__(self, workflows):
        """
        Initialize workflow panel.
        
        Args:
            workflows (dict): Dictionary of workflow objects
        """
        super().__init__("Workflows")
        
        self.workflows = workflows
        self.current_workflow = None
        
        # Initialize UI
        self._init_ui()
        
        logger.info("Workflow panel initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Workflow selection
        workflow_layout = QtWidgets.QHBoxLayout()
        workflow_label = QtWidgets.QLabel("Workflow:")
        workflow_layout.addWidget(workflow_label)
        
        self.workflow_combo = QtWidgets.QComboBox()
        for name, workflow in self.workflows.items():
            self.workflow_combo.addItem(workflow.name(), name)
        
        self.workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        workflow_layout.addWidget(self.workflow_combo)
        
        layout.addLayout(workflow_layout)
        
        # Workflow description
        self.desc_label = QtWidgets.QLabel()
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # Collections list
        collections_group = QtWidgets.QGroupBox("Collections")
        collections_layout = QtWidgets.QVBoxLayout(collections_group)
        
        self.collections_list = QtWidgets.QListWidget()
        self.collections_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.collections_list.currentItemChanged.connect(self._on_collection_changed)
        collections_layout.addWidget(self.collections_list)
        
        # Collection controls
        controls_layout = QtWidgets.QHBoxLayout()
        
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        controls_layout.addWidget(self.refresh_button)
        
        collections_layout.addLayout(controls_layout)
        
        layout.addWidget(collections_group)
        
        # Grid layout controls
        layout_group = QtWidgets.QGroupBox("Grid Layout")
        layout_form = QtWidgets.QFormLayout(layout_group)
        
        # Layout selection
        self.layout_combo = QtWidgets.QComboBox()
        self.layout_combo.addItem("Automatic", None)
        self.layout_combo.addItem("2x1 (2 rows, 1 column)", (2, 1))
        self.layout_combo.addItem("1x2 (1 row, 2 columns)", (1, 2))
        self.layout_combo.addItem("2x2 (2 rows, 2 columns)", (2, 2))
        self.layout_combo.addItem("3x2 (3 rows, 2 columns)", (3, 2))
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        layout_form.addRow("Layout:", self.layout_combo)
        
        layout.addWidget(layout_group)
        
        # Annotation options (initially hidden)
        self.annotation_group = QtWidgets.QGroupBox("Annotation Options")
        self.annotation_group.setVisible(False)
        annotation_form = QtWidgets.QFormLayout(self.annotation_group)
        
        # Box style selection
        self.box_style_combo = QtWidgets.QComboBox()
        self.box_style_combo.addItem("None", "none")
        self.box_style_combo.addItem("Solid", "solid")
        self.box_style_combo.addItem("Dotted", "dotted")
        self.box_style_combo.addItem("Corners", "corners")
        annotation_form.addRow("Box Style:", self.box_style_combo)
        
        # Line color selection
        self.line_color_combo = QtWidgets.QComboBox()
        self.line_color_combo.addItem("Colored", "colored")
        self.line_color_combo.addItem("White", "white")
        annotation_form.addRow("Line Color:", self.line_color_combo)
        
        # Line thickness slider
        self.thickness_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.thickness_slider.setMinimum(1)
        self.thickness_slider.setMaximum(5)
        self.thickness_slider.setValue(2)
        self.thickness_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.thickness_slider.setTickInterval(1)
        self.thickness_value = QtWidgets.QLabel("2")
        self.thickness_slider.valueChanged.connect(lambda v: self.thickness_value.setText(str(v)))
        
        thickness_layout = QtWidgets.QHBoxLayout()
        thickness_layout.addWidget(self.thickness_slider)
        thickness_layout.addWidget(self.thickness_value)
        annotation_form.addRow("Line Thickness:", thickness_layout)
        
        # Label options
        self.label_combo = QtWidgets.QComboBox()
        self.label_combo.addItem("None", "none")
        self.label_combo.addItem("File Name", "filename")
        annotation_form.addRow("Labels:", self.label_combo)
        
        layout.addWidget(self.annotation_group)
        
        # Apply button
        self.apply_button = QtWidgets.QPushButton("Apply Layout")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        layout.addWidget(self.apply_button)
        
        # Update UI based on initial selection
        self._on_workflow_changed(self.workflow_combo.currentIndex())
    
    def get_current_workflow(self):
        """
        Get the currently selected workflow object.
        
        Returns:
            Workflow object or None
        """
        return self.current_workflow
    
    def update_collections(self):
        """Update the collections list for the current workflow."""
        self.collections_list.clear()
        
        if not self.current_workflow:
            return
        
        # Add collections to list
        for collection in self.current_workflow.collections:
            # Create a descriptive item text based on workflow type
            if self.current_workflow.__class__.__name__ == "MagGridWorkflow":
                mags = collection.get("magnifications", [])
                mag_str = " → ".join([f"{mag}x" for mag in mags])
                count = len(collection.get("images", []))
                item_text = f"MagGrid: {mag_str} ({count} images)"
            else:
                # Generic handling for other workflow types
                count = len(collection.get("images", []))
                item_text = f"Collection: {count} images"
            
            # Create list item
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, collection)
            self.collections_list.addItem(item)
    
    def clear_collections(self):
        """Clear the collections list."""
        self.collections_list.clear()
    
    def get_annotation_options(self):
        """
        Get the current annotation options.
        
        Returns:
            dict: Annotation options
        """
        return {
            "box_style": self.box_style_combo.currentData(),
            "label_style": self.label_combo.currentData(),
            "line_color": self.line_color_combo.currentData(),
            "line_thickness": self.thickness_slider.value()
        }
    
    def _on_workflow_changed(self, index):
        """Handle workflow selection change."""
        if index < 0:
            self.current_workflow = None
            self.desc_label.setText("")
            self.clear_collections()
            self.annotation_group.setVisible(False)
            return
        
        # Get the workflow name and object
        workflow_name = self.workflow_combo.itemData(index)
        self.current_workflow = self.workflows.get(workflow_name)
        
        if self.current_workflow:
            # Update description
            self.desc_label.setText(self.current_workflow.description())
            
            # Update collections
            self.update_collections()
            
            # Show annotation options for MagGrid workflow
            self.annotation_group.setVisible(workflow_name == "MagGrid")
            
            # Emit signal
            self.workflow_selected.emit(workflow_name)
        else:
            self.desc_label.setText("")
            self.clear_collections()
            self.annotation_group.setVisible(False)
    
    def _on_collection_changed(self, current, previous):
        """Handle collection selection change."""
        if not current:
            self.collection_selected.emit(None)
            return
        
        # Get collection data from item
        collection = current.data(QtCore.Qt.UserRole)
        
        # Emit signal
        self.collection_selected.emit(collection)
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        if not self.current_workflow:
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
            self.current_workflow.discover_collections()
            progress.setValue(90)
            
            # Update UI
            self.update_collections()
            progress.setValue(100)
        except Exception as e:
            logger.exception(f"Error refreshing collections: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Refresh Error",
                f"Error refreshing collections: {str(e)}"
            )
    
    def _on_layout_changed(self, index):
        """Handle layout selection change."""
        # Update apply button state
        self.apply_button.setEnabled(self.collections_list.currentItem() is not None)
    
    def _on_apply_clicked(self):
        """Handle apply button click."""
        # Get current collection
        current_item = self.collections_list.currentItem()
        if not current_item:
            return
        
        collection = current_item.data(QtCore.Qt.UserRole)
        
        # Get selected layout
        layout = self.layout_combo.currentData()
        
        # Get annotation options
        options = self.get_annotation_options()
        
        # Emit signal
        self.create_grid_requested.emit(collection, layout, options)
