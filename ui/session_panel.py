"""
Session information panel for SEM Image Workflow Manager.
"""

import os
from qtpy import QtWidgets, QtCore, QtGui
from utils.logger import Logger

logger = Logger(__name__)


class SessionPanel(QtWidgets.QGroupBox):
    """
    Panel for displaying and editing session information.
    """
    
    # Custom signals
    session_opened = QtCore.Signal(str)  # Session folder path
    session_info_updated = QtCore.Signal()
    
    def __init__(self, session_manager):
        """
        Initialize session panel.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__("Session Information")
        
        self.session_manager = session_manager
        
        # Initialize UI
        self._init_ui()
        
        logger.info("Session panel initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Session folder section
        folder_layout = QtWidgets.QHBoxLayout()
        folder_label = QtWidgets.QLabel("Session Folder:")
        folder_layout.addWidget(folder_label)
        
        self.folder_edit = QtWidgets.QLineEdit()
        self.folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_edit)
        
        browse_button = QtWidgets.QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_session_folder)
        folder_layout.addWidget(browse_button)
        
        layout.addLayout(folder_layout)
        
        # Session info form
        form_layout = QtWidgets.QFormLayout()
        
        # Sample ID
        self.sample_id_edit = QtWidgets.QLineEdit()
        self.sample_id_edit.setPlaceholderText("Required")
        form_layout.addRow("Sample ID:", self.sample_id_edit)
        
        # Sample Type
        self.sample_type_edit = QtWidgets.QLineEdit()
        self.sample_type_edit.setPlaceholderText("Required")
        form_layout.addRow("Sample Type:", self.sample_type_edit)
        
        # Preparation Method
        self.prep_method_edit = QtWidgets.QLineEdit()
        self.prep_method_edit.setPlaceholderText("Required")
        form_layout.addRow("Preparation Method:", self.prep_method_edit)
        
        # Operator Name
        self.operator_name_edit = QtWidgets.QLineEdit()
        self.operator_name_edit.setPlaceholderText("Required")
        form_layout.addRow("Operator Name:", self.operator_name_edit)
        
        # Notes
        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes about this session")
        self.notes_edit.setMaximumHeight(80)
        form_layout.addRow("Notes:", self.notes_edit)
        
        layout.addLayout(form_layout)
        
        # Session info buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self._save_session_info)
        button_layout.addWidget(self.save_button)
        
        self.reset_button = QtWidgets.QPushButton("Reset")
        self.reset_button.clicked.connect(self._reset_session_info)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
        
        # Session stats
        stats_group = QtWidgets.QGroupBox("Session Statistics")
        stats_layout = QtWidgets.QVBoxLayout(stats_group)
        
        self.stats_label = QtWidgets.QLabel()
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        # Disable form initially
        self._set_form_enabled(False)
        
        # Connect signals
        self.sample_id_edit.textChanged.connect(self._validate_form)
        self.sample_type_edit.textChanged.connect(self._validate_form)
        self.prep_method_edit.textChanged.connect(self._validate_form)
        self.operator_name_edit.textChanged.connect(self._validate_form)
    
    def _browse_session_folder(self):
        """Open a folder dialog to select a session folder."""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Session Folder",
            os.path.expanduser("~")
        )
        
        if folder_path:
            self._open_session_folder(folder_path)
    
    def _open_session_folder(self, folder_path):
        """Open a session from the specified folder."""
        try:
            # Open the session
            if self.session_manager.open_session(folder_path):
                # Update UI with session info
                self.update_session_info()
                
                # Emit signal
                self.session_opened.emit(folder_path)
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Session Error",
                    f"Failed to open session: {folder_path}"
                )
        except Exception as e:
            logger.exception(f"Error opening session folder: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self,
                "Session Error",
                f"Error opening session folder: {str(e)}"
            )
    
    def update_session_info(self):
        """Update UI with current session information."""
        # Clear form
        self.folder_edit.clear()
        self.sample_id_edit.clear()
        self.sample_type_edit.clear()
        self.prep_method_edit.clear()
        self.operator_name_edit.clear()
        self.notes_edit.clear()
        self.stats_label.clear()
        
        # If no session is open, disable form
        if not self.session_manager.current_session:
            self._set_form_enabled(False)
            return
        
        # Enable form
        self._set_form_enabled(True)
        
        # Update form with session info
        session = self.session_manager.current_session
        self.folder_edit.setText(session.session_folder)
        self.sample_id_edit.setText(session.sample_id)
        self.sample_type_edit.setText(session.sample_type)
        self.prep_method_edit.setText(session.preparation_method)
        self.operator_name_edit.setText(session.operator_name)
        self.notes_edit.setText(session.notes)
        
        # Update statistics
        image_count = len(self.session_manager.image_files)
        metadata_count = len(self.session_manager.metadata)
        
        stats_text = (
            f"Images: {image_count}\n"
            f"With metadata: {metadata_count}\n"
            f"Created: {session.creation_date}\n"
            f"Last modified: {session.last_modified}"
        )
        self.stats_label.setText(stats_text)
        
        # Validate form
        self._validate_form()
    
    def _save_session_info(self):
        """Save session information from form to the session object."""
        if not self.session_manager.current_session:
            return
        
        session = self.session_manager.current_session
        
        # Update session object with form values
        session.update_field("sample_id", self.sample_id_edit.text())
        session.update_field("sample_type", self.sample_type_edit.text())
        session.update_field("preparation_method", self.prep_method_edit.text())
        session.update_field("operator_name", self.operator_name_edit.text())
        session.update_field("notes", self.notes_edit.toPlainText())
        
        # Save to file
        if session.save():
            logger.info("Session information saved successfully")
            self.update_session_info()  # Refresh UI
            
            # Emit signal
            self.session_info_updated.emit()
        else:
            logger.error("Failed to save session information")
            QtWidgets.QMessageBox.warning(
                self,
                "Save Error",
                "Failed to save session information."
            )
    
    def _reset_session_info(self):
        """Reset form to current session information."""
        self.update_session_info()
    
    def _validate_form(self):
        """Validate form fields and update UI state."""
        if not self.session_manager.current_session:
            return
        
        # Check if required fields are filled
        is_valid = (
            bool(self.sample_id_edit.text()) and
            bool(self.sample_type_edit.text()) and
            bool(self.prep_method_edit.text()) and
            bool(self.operator_name_edit.text())
        )
        
        # Highlight required fields if empty
        self._highlight_field(self.sample_id_edit, bool(self.sample_id_edit.text()))
        self._highlight_field(self.sample_type_edit, bool(self.sample_type_edit.text()))
        self._highlight_field(self.prep_method_edit, bool(self.prep_method_edit.text()))
        self._highlight_field(self.operator_name_edit, bool(self.operator_name_edit.text()))
        
        # Enable save button if form is valid
        self.save_button.setEnabled(is_valid)
    
    def _highlight_field(self, field, is_valid):
        """Highlight a field if it's invalid."""
        if is_valid:
            field.setStyleSheet("")
        else:
            field.setStyleSheet("background-color: #FFDDDD;")
    
    def _set_form_enabled(self, enabled):
        """Enable or disable the form fields."""
        self.sample_id_edit.setEnabled(enabled)
        self.sample_type_edit.setEnabled(enabled)
        self.prep_method_edit.setEnabled(enabled)
        self.operator_name_edit.setEnabled(enabled)
        self.notes_edit.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
