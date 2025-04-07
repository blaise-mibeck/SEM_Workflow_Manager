"""
Session information panel for SEM Image Workflow Manager.
"""

import os
import datetime
from qtpy import QtWidgets, QtCore, QtGui
from utils.logger import Logger
from ui.enhanced_folder_dialog import EnhancedFolderDialog
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
        
        # Session type selection
        session_type_layout = QtWidgets.QHBoxLayout()
        session_type_label = QtWidgets.QLabel("Session Type:")
        session_type_layout.addWidget(session_type_label)
        
        self.session_type_combo = QtWidgets.QComboBox()
        self.session_type_combo.addItems(["EDX", "SEM"])
        session_type_layout.addWidget(self.session_type_combo)
        
        layout.addLayout(session_type_layout)
        
        # Create tabs for better organization of fields
        tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(tab_widget)
        
        # Tab 1: Sample Information
        sample_tab = QtWidgets.QWidget()
        sample_layout = QtWidgets.QVBoxLayout(sample_tab)
        sample_form = QtWidgets.QFormLayout()
        
        # Project Number
        self.project_number_edit = QtWidgets.QLineEdit()
        self.project_number_edit.setPlaceholderText("Required")
        sample_form.addRow("Project Number:", self.project_number_edit)
        
        # TCL Sample ID
        self.tcl_sample_id_edit = QtWidgets.QLineEdit()
        self.tcl_sample_id_edit.setPlaceholderText("Required")
        sample_form.addRow("TCL Sample ID:", self.tcl_sample_id_edit)
        
        # Client Sample ID
        self.client_sample_id_edit = QtWidgets.QLineEdit()
        self.client_sample_id_edit.setPlaceholderText("Required")
        sample_form.addRow("Client Sample ID:", self.client_sample_id_edit)
        
        # Sample Type
        self.sample_type_edit = QtWidgets.QLineEdit()
        self.sample_type_edit.setPlaceholderText("Required")
        sample_form.addRow("Sample Type:", self.sample_type_edit)
        
        # Electrically Conductive
        self.conductive_checkbox = QtWidgets.QCheckBox("Electrically Conductive")
        sample_form.addRow("", self.conductive_checkbox)
        
        sample_layout.addLayout(sample_form)
        tab_widget.addTab(sample_tab, "Sample Info")
        
        # Tab 2: Preparation Details
        prep_tab = QtWidgets.QWidget()
        prep_layout = QtWidgets.QVBoxLayout(prep_tab)
        prep_form = QtWidgets.QFormLayout()
        
        # Stub Type
        self.stub_type_combo = QtWidgets.QComboBox()
        self.stub_type_combo.addItems(["Standard 12.5mm", "Large 25mm", "Custom", "Other"])
        self.stub_type_combo.setEditable(True)
        prep_form.addRow("Stub Type:", self.stub_type_combo)
        
        # Preparation Method
        self.prep_method_edit = QtWidgets.QLineEdit()
        self.prep_method_edit.setPlaceholderText("Required")
        prep_form.addRow("Preparation Method:", self.prep_method_edit)
        
        # Gold Coating Thickness
        self.gold_coating_edit = QtWidgets.QLineEdit()
        self.gold_coating_edit.setPlaceholderText("Optional")
        prep_form.addRow("Gold Coating (nm):", self.gold_coating_edit)
        
        # Vacuum Drying Time
        self.vacuum_drying_edit = QtWidgets.QLineEdit()
        self.vacuum_drying_edit.setPlaceholderText("Optional")
        prep_form.addRow("Vacuum Drying Time:", self.vacuum_drying_edit)
        
        # Stage Position
        self.stage_position_combo = QtWidgets.QComboBox()
        self.stage_position_combo.addItems(["", "1", "2", "3", "4", "5", "Custom"])
        self.stage_position_combo.setEditable(True)
        prep_form.addRow("Stage Position:", self.stage_position_combo)
        
        prep_layout.addLayout(prep_form)
        tab_widget.addTab(prep_tab, "Preparation")
        
        # Tab 3: Additional Information
        add_tab = QtWidgets.QWidget()
        add_layout = QtWidgets.QVBoxLayout(add_tab)
        add_form = QtWidgets.QFormLayout()
        
        # Operator Name
        self.operator_name_edit = QtWidgets.QLineEdit()
        self.operator_name_edit.setPlaceholderText("Required")
        add_form.addRow("Operator Name:", self.operator_name_edit)
        
        # Sample ID (for backward compatibility)
        self.sample_id_edit = QtWidgets.QLineEdit()
        self.sample_id_edit.setPlaceholderText("Optional (Legacy)")
        add_form.addRow("Sample ID (Legacy):", self.sample_id_edit)
        
        # Notes
        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes about this session")
        self.notes_edit.setMaximumHeight(80)
        add_form.addRow("Notes:", self.notes_edit)
        
        add_layout.addLayout(add_form)
        tab_widget.addTab(add_tab, "Additional Info")
        
        # Session buttons
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
        
        # Connect signals for validation
        self.project_number_edit.textChanged.connect(self._validate_form)
        self.tcl_sample_id_edit.textChanged.connect(self._validate_form)
        self.client_sample_id_edit.textChanged.connect(self._validate_form)
        self.sample_type_edit.textChanged.connect(self._validate_form)
        self.prep_method_edit.textChanged.connect(self._validate_form)
        self.operator_name_edit.textChanged.connect(self._validate_form)
    
    def _browse_session_folder(self):
        """Open a folder dialog to select a session folder."""

        folder_path = EnhancedFolderDialog.get_folder(self, "Select Session Folder", os.path.expanduser("~"))
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
        self.project_number_edit.clear()
        self.tcl_sample_id_edit.clear()
        self.client_sample_id_edit.clear()
        self.prep_method_edit.clear()
        self.operator_name_edit.clear()
        self.gold_coating_edit.clear()
        self.vacuum_drying_edit.clear()
        self.notes_edit.clear()
        self.stats_label.clear()
        self.conductive_checkbox.setChecked(False)
        
        # Reset comboboxes
        self.session_type_combo.setCurrentIndex(0)  # Default to EDX
        self.stub_type_combo.setCurrentIndex(0)     # Default to Standard 12.5mm
        self.stage_position_combo.setCurrentIndex(0)  # Default to empty
        
        # If no session is open, disable form
        if not self.session_manager.current_session:
            self._set_form_enabled(False)
            return
        
        # Enable form
        self._set_form_enabled(True)
        
        # Update form with session info
        session = self.session_manager.current_session
        self.folder_edit.setText(session.session_folder)
        
        # Set session type
        session_type_index = self.session_type_combo.findText(session.session_type)
        if session_type_index >= 0:
            self.session_type_combo.setCurrentIndex(session_type_index)
        else:
            # If not found, add it and select it
            self.session_type_combo.addItem(session.session_type)
            self.session_type_combo.setCurrentText(session.session_type)
        
        # Set sample info
        self.sample_id_edit.setText(session.sample_id)
        self.project_number_edit.setText(session.project_number)
        self.tcl_sample_id_edit.setText(session.tcl_sample_id)
        self.client_sample_id_edit.setText(session.client_sample_id)
        self.sample_type_edit.setText(session.sample_type)
        self.conductive_checkbox.setChecked(session.electrically_conductive)
        
        # Set preparation info
        # Set stub type
        stub_type_index = self.stub_type_combo.findText(session.stub_type)
        if stub_type_index >= 0:
            self.stub_type_combo.setCurrentIndex(stub_type_index)
        else:
            self.stub_type_combo.setCurrentText(session.stub_type)
        
        self.prep_method_edit.setText(session.preparation_method)
        self.gold_coating_edit.setText(session.gold_coating_thickness)
        self.vacuum_drying_edit.setText(session.vacuum_drying_time)
        
        # Set stage position
        stage_pos = str(session.stage_position) if session.stage_position else ""
        stage_pos_index = self.stage_position_combo.findText(stage_pos)
        if stage_pos_index >= 0:
            self.stage_position_combo.setCurrentIndex(stage_pos_index)
        else:
            self.stage_position_combo.setCurrentText(stage_pos)
        
        # Set additional info
        self.operator_name_edit.setText(session.operator_name)
        self.notes_edit.setText(session.notes)
        
        # Update statistics
        image_count = len(self.session_manager.image_files)
        metadata_count = len(self.session_manager.metadata)
        
        # Format creation_time for display
        creation_date = "Unknown"
        if hasattr(session, 'creation_time') and session.creation_time:
            try:
                # Try to parse ISO format datetime
                dt = datetime.datetime.fromisoformat(session.creation_time.replace('Z', '+00:00'))
                creation_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                # Fall back to creation_date if parsing fails
                creation_date = session.creation_date
        
        # Add session status
        status = "Active" if session.is_active else "Inactive"
        
        # Calculate total time
        total_time = "N/A"
        if session.total_time_seconds > 0:
            minutes, seconds = divmod(int(session.total_time_seconds), 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                total_time = f"{hours}h {minutes}m {seconds}s"
            else:
                total_time = f"{minutes}m {seconds}s"
        
        stats_text = (
            f"Status: {status}\n"
            f"Images: {image_count}\n"
            f"With metadata: {metadata_count}\n"
            f"Created: {creation_date}\n"
            f"Total Time: {total_time}"
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
        session.update_field("session_type", self.session_type_combo.currentText())
        
        # Sample information
        session.update_field("project_number", self.project_number_edit.text())
        session.update_field("tcl_sample_id", self.tcl_sample_id_edit.text())
        session.update_field("client_sample_id", self.client_sample_id_edit.text())
        session.update_field("sample_type", self.sample_type_edit.text())
        session.update_field("electrically_conductive", self.conductive_checkbox.isChecked())
        
        # Backward compatibility fields
        session.update_field("sample_id", self.sample_id_edit.text())
        
        # Preparation information
        session.update_field("stub_type", self.stub_type_combo.currentText())
        session.update_field("preparation_method", self.prep_method_edit.text())
        session.update_field("gold_coating_thickness", self.gold_coating_edit.text())
        session.update_field("vacuum_drying_time", self.vacuum_drying_edit.text())
        session.update_field("stage_position", self.stage_position_combo.currentText())
        
        # Additional information
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
            bool(self.project_number_edit.text()) and
            bool(self.tcl_sample_id_edit.text()) and
            bool(self.client_sample_id_edit.text()) and
            bool(self.sample_type_edit.text()) and
            bool(self.prep_method_edit.text()) and
            bool(self.operator_name_edit.text())
        )
        
        # Highlight required fields if empty
        self._highlight_field(self.project_number_edit, bool(self.project_number_edit.text()))
        self._highlight_field(self.tcl_sample_id_edit, bool(self.tcl_sample_id_edit.text()))
        self._highlight_field(self.client_sample_id_edit, bool(self.client_sample_id_edit.text()))
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
        # Session type
        self.session_type_combo.setEnabled(enabled)
        
        # Sample information
        self.project_number_edit.setEnabled(enabled)
        self.tcl_sample_id_edit.setEnabled(enabled)
        self.client_sample_id_edit.setEnabled(enabled)
        self.sample_type_edit.setEnabled(enabled)
        self.conductive_checkbox.setEnabled(enabled)
        
        # Preparation information
        self.stub_type_combo.setEnabled(enabled)
        self.prep_method_edit.setEnabled(enabled)
        self.gold_coating_edit.setEnabled(enabled)
        self.vacuum_drying_edit.setEnabled(enabled)
        self.stage_position_combo.setEnabled(enabled)
        
        # Additional information
        self.operator_name_edit.setEnabled(enabled)
        self.sample_id_edit.setEnabled(enabled)
        self.notes_edit.setEnabled(enabled)
        
        # Buttons
        self.save_button.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
        
        # If form is enabled, validate it to update save button state
        if enabled:
            self._validate_form()
