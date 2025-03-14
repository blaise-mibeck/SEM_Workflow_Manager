"""
SEM Image Workflow Manager - Application Entry Point

A desktop application for organizing, processing, and visualizing
Scanning Electron Microscope (SEM) images.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import traceback
from qtpy import QtWidgets, QtCore
from ui.main_window import MainWindow
from utils.logger import Logger, app_logger

# Initialize logger
logger = Logger(__name__)


def setup_exception_handling():
    """Set up global exception handling to log unhandled exceptions."""
    def excepthook(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions by logging them."""
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        # Log the exception
        logger.critical(f"Unhandled exception: {tb_text}")
        
        # Show error dialog
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.setText("An unexpected error has occurred.")
        error_dialog.setInformativeText(str(exc_value))
        error_dialog.setDetailedText(tb_text)
        error_dialog.setWindowTitle("Application Error")
        error_dialog.exec_()
        
        # Call the default exception handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Set the exception hook
    sys.excepthook = excepthook


def main():
    """Application entry point."""
    # Set up exception handling
    setup_exception_handling()
    
    # Create application
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("SEM Image Workflow Manager")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    main_window = MainWindow()
    main_window.show()
    
    # Start the application event loop
    app_logger.info("Application started")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
