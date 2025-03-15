"""
Main window UI for SEM Image Workflow Manager.
"""

import os
import sys
from qtpy import QtWidgets, QtGui, QtCore
from utils.logger import Logger
from models.metadata_extractor import MetadataExtractor
from workflows.mag_grid import MagGridWorkflow
from workflows.compare_grid import CompareGridWorkflow
from ui.session_panel import SessionPanel
from ui.workflow_panel import WorkflowPanel
from ui.grid_preview import GridPreviewPanel
from ui.compare_grid_panel import CompareGridPanel

logger = Logger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """
    Main window for the SEM Image Workflow Manager application.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        self.setWindowTitle("SEM Image Workflow Manager")
        self.resize(1400, 900)
        
        # Initialize metadata extractor
        self.metadata_extractor = MetadataExtractor()
        
        # Create session manager
        from models.session import SessionManager
        self.session_manager = SessionManager()
        
        # Create workflows
        self.workflows = {
            "MagGrid": MagGridWorkflow(self.session_manager),
            "CompareGrid": CompareGridWorkflow(self.session_manager)
        }
        
        # Initialize UI components
        self._init_ui()
        
        logger.info("Main window initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        
        # Create a splitter for resizable layout
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Session and workflow selection
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        
        # Create tab widget for different panel modes
        self.left_tabs = QtWidgets.QTabWidget()
        left_layout.addWidget(self.left_tabs)
        
        # Standard workflow tab
        standard_tab = QtWidgets.QWidget()
        standard_layout = QtWidgets.QVBoxLayout(standard_tab)
        
        # Session panel
        self.session_panel = SessionPanel(self.session_manager)
        standard_layout.addWidget(self.session_panel)
        
        # Workflow panel
        self.workflow_panel = WorkflowPanel(self.workflows)
        standard_layout.addWidget(self.workflow_panel)
        
        self.left_tabs.addTab(standard_tab, "Standard")
        
        # CompareGrid tab
        compare_tab = QtWidgets.QWidget()
        compare_layout = QtWidgets.QVBoxLayout(compare_tab)
        
        # CompareGrid panel
        self.compare_grid_panel = CompareGridPanel(self.session_manager)
        compare_layout.addWidget(self.compare_grid_panel)
        
        self.left_tabs.addTab(compare_tab, "Compare Grid")
        
        # Right panel - Grid preview and export
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        
        # Grid preview panel
        self.grid_preview = GridPreviewPanel()
        right_layout.addWidget(self.grid_preview)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (30% left, 70% right)
        splitter.setSizes([300, 700])
        
        # Set minimum sizes to enforce proportions
        left_panel.setMinimumWidth(250)
        right_panel.setMinimumWidth(600)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Connect signals
        self._connect_signals()
    
    def _create_menu_bar(self):
        """Create the application menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Open session action
        open_action = QtWidgets.QAction("&Open Session Folder...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_session_folder)
        file_menu.addAction(open_action)
        
        # Close session action
        close_action = QtWidgets.QAction("&Close Session", self)
        close_action.triggered.connect(self._close_session)
        file_menu.addAction(close_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QtWidgets.QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        # Extract metadata action
        extract_action = QtWidgets.QAction("&Extract Metadata", self)
        extract_action.triggered.connect(self._extract_metadata)
        tools_menu.addAction(extract_action)
        
        # FIXED: Changed method name in connect to match class method name
        # Refresh collections action
        refresh_action = QtWidgets.QAction("&Refresh Collections", self)
        refresh_action.triggered.connect(self.refresh_collections)  # Removed underscore
        tools_menu.addAction(refresh_action)
        
        # Compare menu
        compare_menu = menu_bar.addMenu("&Compare")
        
        # FIXED: Changed method name in connect to match class method name
        # Add sessions action
        add_sessions_action = QtWidgets.QAction("&Add Sessions for Comparison...", self)
        add_sessions_action.triggered.connect(self.add_comparison_sessions)  # Removed underscore
        compare_menu.addAction(add_sessions_action)
        
        # FIXED: Changed method name in connect to match class method name
        # Discover comparisons action
        discover_action = QtWidgets.QAction("&Discover Comparisons", self)
        discover_action.triggered.connect(self.discover_comparisons)  # Removed underscore
        compare_menu.addAction(discover_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        # About action
        about_action = QtWidgets.QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Connect session panel signals
        self.session_panel.session_opened.connect(self._on_session_opened)
        self.session_panel.session_info_updated.connect(self._on_session_info_updated)
        
        # Connect workflow panel signals
        self.workflow_panel.workflow_selected.connect(self._on_workflow_selected)
        self.workflow_panel.collection_selected.connect(self._on_collection_selected)
        self.workflow_panel.create_grid_requested.connect(self._on_create_grid_requested)
        
        # Connect grid preview signals
        self.grid_preview.export_requested.connect(self._on_export_requested)
        
        # Connect CompareGrid panel signals
        self.compare_grid_panel.grid_created.connect(self._on_compare_grid_created)
        
        # Connect tab change signals
        self.left_tabs.currentChanged.connect(self._on_tab_changed)
        
        # Connect context menu for grid preview
        self.grid_preview.preview_label.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.grid_preview.preview_label.customContextMenuRequested.connect(self._on_grid_preview_context_menu)
    
    def _open_session_folder(self):
        """Open a session folder dialog."""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Session Folder",
            os.path.expanduser("~")
        )
        
        if folder_path:
            self._load_session(folder_path)
    
    def _load_session(self, folder_path):
        """Load a session from the specified folder."""
        try:
            # Open the session
            if self.session_manager.open_session(folder_path):
                # Update the session panel
                self.session_panel.update_session_info()
                
                # Extract metadata if available in the folder
                metadata_file = os.path.join(folder_path, "metadata.csv")
                if os.path.exists(metadata_file):
                    logger.info(f"Metadata file found: {metadata_file}")
                    # TODO: Load metadata from CSV
                else:
                    # Ask if metadata should be extracted
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Extract Metadata",
                        "No metadata found for this session. Extract metadata now?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        QtWidgets.QMessageBox.Yes
                    )
                    
                    if reply == QtWidgets.QMessageBox.Yes:
                        self._extract_metadata()
                
                # Load existing collections for workflows
                self._load_workflow_collections()
                
                # Update status bar
                self.statusBar().showMessage(f"Session opened: {folder_path}")
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Session Error",
                    f"Failed to open session: {folder_path}"
                )
        except Exception as e:
            logger.exception(f"Error loading session: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self,
                "Session Error",
                f"Error loading session: {str(e)}"
            )
    
    def _close_session(self):
        """Close the current session."""
        if self.session_manager.current_session:
            # Save any changes to session info
            self.session_manager.current_session.save()
            
            # Close the session
            self.session_manager.close_session()
            
            # Update UI
            self.session_panel.update_session_info()
            self.workflow_panel.clear_collections()
            self.grid_preview.clear_preview()
            
            # Update status bar
            self.statusBar().showMessage("Session closed")
    
    def _extract_metadata(self):
        """Extract metadata for all images in the session."""
        if not self.session_manager.current_session:
            QtWidgets.QMessageBox.warning(
                self,
                "No Session",
                "Please open a session folder first."
            )
            return
        
        # Show progress dialog
        progress = QtWidgets.QProgressDialog(
            "Extracting metadata...",
            "Cancel",
            0,
            len(self.session_manager.image_files),
            self
        )
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        try:
            # Extract metadata
            metadata = {}
            for i, image_path in enumerate(self.session_manager.image_files):
                progress.setValue(i)
                if progress.wasCanceled():
                    break
                
                try:
                    metadata_obj = self.metadata_extractor.extract_metadata(image_path)
                    metadata[image_path] = metadata_obj
                    progress.setLabelText(f"Extracting metadata: {os.path.basename(image_path)}")
                except Exception as e:
                    logger.error(f"Error extracting metadata from {image_path}: {str(e)}")
            
            # Store metadata in session manager
            self.session_manager.metadata = metadata
            self.session_manager._save_metadata_csv()
            
            # Complete the progress
            progress.setValue(len(self.session_manager.image_files))
            
            # Show success message
            valid_count = sum(1 for m in metadata.values() if m.is_valid())
            QtWidgets.QMessageBox.information(
                self,
                "Metadata Extraction",
                f"Extracted metadata for {len(metadata)} images.\n"
                f"{valid_count} images have valid metadata for workflows."
            )
            
            # Discover collections based on the extracted metadata
            self._discover_collections()
            
        except Exception as e:
            logger.exception(f"Error during metadata extraction: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self,
                "Metadata Error",
                f"Error extracting metadata: {str(e)}"
            )
    
    def _discover_collections(self):
        """Discover collections for all workflows."""
        if not self.session_manager.metadata:
            logger.warning("No metadata available for collection discovery")
            return
        
        for workflow_name, workflow in self.workflows.items():
            try:
                collections = workflow.discover_collections()
                logger.info(f"Discovered {len(collections)} collections for {workflow_name}")
            except Exception as e:
                logger.error(f"Error discovering collections for {workflow_name}: {str(e)}")
        
        # Update workflow panel with collections
        self.workflow_panel.update_collections()
    
    def _load_workflow_collections(self):
        """Load existing collections for all workflows."""
        for workflow_name, workflow in self.workflows.items():
            try:
                collections = workflow.load_collections()
                logger.info(f"Loaded {len(collections)} collections for {workflow_name}")
            except Exception as e:
                logger.error(f"Error loading collections for {workflow_name}: {str(e)}")
        
        # Update workflow panel with collections
        self.workflow_panel.update_collections()
    
    # FIXED: Renamed method to not have underscore prefix
    def refresh_collections(self):
        """Refresh collections for the current workflow."""
        current_tab = self.left_tabs.currentIndex()
        
        if current_tab == 0:  # Standard workflow tab
            current_workflow = self.workflow_panel.get_current_workflow()
            if current_workflow:
                try:
                    collections = current_workflow.discover_collections()
                    logger.info(f"Refreshed {len(collections)} collections for {current_workflow.name()}")
                    
                    # Update workflow panel with collections
                    self.workflow_panel.update_collections()
                except Exception as e:
                    logger.error(f"Error refreshing collections: {str(e)}")
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Refresh Error",
                        f"Error refreshing collections: {str(e)}"
                    )
        elif current_tab == 1:  # CompareGrid tab
            self.discover_comparisons()  # Also fixed this call
    
    def _show_about(self):
        """Show about dialog."""
        QtWidgets.QMessageBox.about(
            self,
            "About SEM Image Workflow Manager",
            "SEM Image Workflow Manager\n\n"
            "A tool for organizing, processing, and visualizing "
            "Scanning Electron Microscope (SEM) images."
        )
    
    def _on_session_opened(self, session_folder):
        """Handle session opened signal."""
        logger.info(f"Session opened signal received: {session_folder}")
    
    def _on_session_info_updated(self):
        """Handle session info updated signal."""
        logger.info("Session info updated signal received")
    
    def _on_workflow_selected(self, workflow_name):
        """Handle workflow selected signal."""
        logger.info(f"Workflow selected signal received: {workflow_name}")
    
    def _on_collection_selected(self, collection):
        """Handle collection selected signal."""
        if not collection:
            self.grid_preview.clear_preview()
            return
        
        logger.info(f"Collection selected signal received: {collection.get('id', 'unknown')}")
        
        # Get the current workflow
        current_workflow = self.workflow_panel.get_current_workflow()
        if not current_workflow:
            return
        
        # Get annotation options
        options = self.workflow_panel.get_annotation_options()
        
        # Create grid visualization
        try:
            grid_image = current_workflow.create_grid(collection, None, options)
            if grid_image:
                self.grid_preview.set_preview(grid_image, collection)
        except Exception as e:
            logger.error(f"Error creating grid visualization: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Grid Error",
                f"Error creating grid visualization: {str(e)}"
            )
    
    def _on_create_grid_requested(self, collection, layout, options):
        """Handle create grid requested signal."""
        logger.info(f"Create grid requested signal received: {collection.get('id', 'unknown')}")
        
        # Get the current workflow
        current_workflow = self.workflow_panel.get_current_workflow()
        if not current_workflow:
            return
        
        # Create grid visualization with the specified layout and options
        try:
            grid_image = current_workflow.create_grid(collection, layout, options)
            if grid_image:
                self.grid_preview.set_preview(grid_image, collection)
        except Exception as e:
            logger.error(f"Error creating grid visualization: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Grid Error",
                f"Error creating grid visualization: {str(e)}"
            )
    
    def _on_export_requested(self, grid_image, collection):
        """Handle export requested signal."""
        if not grid_image or not collection:
            return
        
        logger.info(f"Export requested signal received: {collection.get('id', 'unknown')}")
        
        # Determine which workflow to use based on collection type
        collection_type = collection.get("type", "")
        
        if collection_type == "CompareGrid":
            workflow = self.workflows["CompareGrid"]
        else:
            # Get the current workflow
            workflow = self.workflow_panel.get_current_workflow()
        
        if not workflow:
            return
        
        # Export the grid visualization
        try:
            image_path, caption_path = workflow.export_grid(grid_image, collection)
            
            QtWidgets.QMessageBox.information(
                self,
                "Export Successful",
                f"Grid exported successfully:\n"
                f"Image: {os.path.basename(image_path)}\n"
                f"Caption: {os.path.basename(caption_path)}"
            )
        except Exception as e:
            logger.error(f"Error exporting grid: {str(e)}")
            QtWidgets.QMessageBox.warning(
                self,
                "Export Error",
                f"Error exporting grid: {str(e)}"
            )
    
    # FIXED: Renamed method to not have underscore prefix
    def add_comparison_sessions(self):
        """Open dialog to add sessions for comparison."""
        self.left_tabs.setCurrentIndex(1)  # Switch to CompareGrid tab
        
        # Forward to CompareGrid panel
        self.compare_grid_panel.add_sessions()
    
    # FIXED: Renamed method to not have underscore prefix
    def discover_comparisons(self):
        """Discover CompareGrid collections."""
        self.left_tabs.setCurrentIndex(1)  # Switch to CompareGrid tab
        
        # Forward to CompareGrid panel
        self.compare_grid_panel.discover_collections()
    
    def _on_compare_grid_created(self, grid_image, collection):
        """Handle grid created signal from CompareGrid panel."""
        if grid_image and collection:
            self.grid_preview.set_preview(grid_image, collection)
            
            # Store the current CompareGrid collection for context menu
            self.current_compare_collection = collection
    
    def _on_tab_changed(self, index):
        """Handle tab change events."""
        # Clear the grid preview when switching tabs
        self.grid_preview.clear_preview()
    
    def _on_grid_preview_context_menu(self, pos):
        """Handle context menu request on grid preview."""
        # Get the current collection
        current_tab = self.left_tabs.currentIndex()
        current_collection = None
        
        if current_tab == 0:  # Standard workflow tab
            if hasattr(self, 'current_collection'):
                current_collection = self.current_collection
        else:  # CompareGrid tab
            if hasattr(self, 'current_compare_collection'):
                current_collection = self.current_compare_collection
        
        if not current_collection:
            # Try to get it from the preview
            if self.grid_preview.current_collection:
                current_collection = self.grid_preview.current_collection
        
        if not current_collection:
            return
        
        # Only show context menu if the collection has alternatives
        has_alternatives = False
        if "images" in current_collection:
            for img in current_collection["images"]:
                if img.get("alternatives"):
                    has_alternatives = True
                    break
        
        if not has_alternatives:
            return
        
        # Show alternatives menu based on collection type
        if current_collection.get("type") == "CompareGrid":
            self.compare_grid_panel.show_alternative_menu(
                self.grid_preview.preview_label,
                pos,
                current_collection
            )
        else:
            # Handle for other workflow types if needed
            pass