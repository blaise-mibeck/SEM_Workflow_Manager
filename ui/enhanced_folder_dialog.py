"""
Enhanced folder selection dialog with memory of previously visited locations
"""

import os
from qtpy import QtWidgets, QtCore, QtGui
from utils.logger import Logger
from utils.config import config

logger = Logger(__name__)


class EnhancedFolderDialog(QtWidgets.QDialog):
    """
    Enhanced folder selection dialog with memory of previously visited folders.
    """
    
    def __init__(self, parent=None, title="Select Folder", initial_dir=None):
        """Initialize dialog."""
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.resize(700, 500)
        self.selected_folder = None
        
        # Load recent folders from config
        self.recent_folders = config.get('recent_folders', [])
        
        # Initialize UI
        self._init_ui()
        
        # Set initial directory if provided
        if initial_dir and os.path.exists(initial_dir):
            self.current_dir = initial_dir
            self.dir_edit.setText(initial_dir)
            self._update_folder_list()
        elif self.recent_folders:
            # Use the most recent folder as default
            self.current_dir = self.recent_folders[0]
            self.dir_edit.setText(self.current_dir)
            self._update_folder_list()
        else:
            # Default to user's home directory
            self.current_dir = os.path.expanduser("~")
            self.dir_edit.setText(self.current_dir)
            self._update_folder_list()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Recent folders section
        if self.recent_folders:
            recent_group = QtWidgets.QGroupBox("Recent Folders")
            recent_layout = QtWidgets.QVBoxLayout(recent_group)
            
            # Create a list of recent folders
            self.recent_list = QtWidgets.QListWidget()
            for folder in self.recent_folders:
                if os.path.exists(folder):
                    item = QtWidgets.QListWidgetItem(folder)
                    item.setData(QtCore.Qt.UserRole, folder)
                    self.recent_list.addItem(item)
            
            self.recent_list.itemDoubleClicked.connect(self._on_recent_folder_selected)
            recent_layout.addWidget(self.recent_list)
            
            layout.addWidget(recent_group)
        
        # Current directory section
        current_dir_layout = QtWidgets.QHBoxLayout()
        
        dir_label = QtWidgets.QLabel("Current Directory:")
        current_dir_layout.addWidget(dir_label)
        
        self.dir_edit = QtWidgets.QLineEdit()
        self.dir_edit.setReadOnly(True)
        current_dir_layout.addWidget(self.dir_edit)
        
        browse_button = QtWidgets.QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_directory)
        current_dir_layout.addWidget(browse_button)
        
        layout.addLayout(current_dir_layout)
        
        # Folder contents
        contents_group = QtWidgets.QGroupBox("Contents")
        contents_layout = QtWidgets.QVBoxLayout(contents_group)
        
        self.folder_list = QtWidgets.QListWidget()
        self.folder_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.folder_list.itemDoubleClicked.connect(self._on_folder_double_clicked)
        contents_layout.addWidget(self.folder_list)
        
        layout.addWidget(contents_group)
        
        # Dialog buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.parent_button = QtWidgets.QPushButton("Parent Directory")
        self.parent_button.clicked.connect(self._go_to_parent)
        button_layout.addWidget(self.parent_button)
        
        button_layout.addStretch()
        
        self.select_button = QtWidgets.QPushButton("Select")
        self.select_button.clicked.connect(self._select_current_dir)
        button_layout.addWidget(self.select_button)
        
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def _browse_directory(self):
        """Open system folder browser dialog."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            self.current_dir
        )
        
        if folder:
            self.current_dir = folder
            self.dir_edit.setText(folder)
            self._update_folder_list()
    
    def _update_folder_list(self):
        """Update the folder list with current directory contents."""
        self.folder_list.clear()
        
        try:
            # First add the special ".." parent directory
            parent_item = QtWidgets.QListWidgetItem("..")
            parent_item.setData(QtCore.Qt.UserRole, os.path.dirname(self.current_dir))
            parent_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogToParent))
            self.folder_list.addItem(parent_item)
            
            # Add all directories in the current folder
            for entry in sorted(os.listdir(self.current_dir)):
                path = os.path.join(self.current_dir, entry)
                if os.path.isdir(path):
                    item = QtWidgets.QListWidgetItem(entry)
                    item.setData(QtCore.Qt.UserRole, path)
                    item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
                    self.folder_list.addItem(item)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                f"Could not read directory contents: {str(e)}"
            )
    
    def _go_to_parent(self):
        """Navigate to parent directory."""
        parent = os.path.dirname(self.current_dir)
        if parent and os.path.exists(parent):
            self.current_dir = parent
            self.dir_edit.setText(parent)
            self._update_folder_list()
    
    def _on_folder_double_clicked(self, item):
        """Handle double-click on folder item."""
        path = item.data(QtCore.Qt.UserRole)
        if os.path.exists(path) and os.path.isdir(path):
            self.current_dir = path
            self.dir_edit.setText(path)
            self._update_folder_list()
    
    def _on_recent_folder_selected(self, item):
        """Handle selection of a recent folder."""
        path = item.data(QtCore.Qt.UserRole)
        if os.path.exists(path):
            self.current_dir = path
            self.dir_edit.setText(path)
            self._update_folder_list()
    
    def _select_current_dir(self):
        """Select the current directory and accept the dialog."""
        self.selected_folder = self.current_dir
        
        # Add to recent folders if not already present
        recent_folders = config.get('recent_folders', [])
        
        # Remove if already in list (will be re-added at the beginning)
        if self.selected_folder in recent_folders:
            recent_folders.remove(self.selected_folder)
        
        # Add to beginning of list
        recent_folders.insert(0, self.selected_folder)
        
        # Limit to 10 recent folders
        recent_folders = recent_folders[:10]
        
        # Save back to config
        config.set('recent_folders', recent_folders)
        
        self.accept()
    
    @staticmethod
    def get_folder(parent=None, title="Select Folder", initial_dir=None):
        """
        Static method to get a folder from the dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            initial_dir: Initial directory
            
        Returns:
            str: Selected folder path or None if canceled
        """
        dialog = EnhancedFolderDialog(parent, title, initial_dir)
        result = dialog.exec_()
        
        if result == QtWidgets.QDialog.Accepted:
            return dialog.selected_folder
        else:
            return None