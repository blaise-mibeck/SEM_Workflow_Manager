"""
Logging utility for SEM Image Workflow Manager.
Provides consistent logging across the application.
"""

import os
import logging
import datetime
from logging.handlers import RotatingFileHandler


class Logger:
    """
    Logger class for SEM Image Workflow Manager.
    Provides file and console logging with configurable levels.
    """
    
    # Log levels
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    def __init__(self, name, log_dir="logs", level=logging.INFO, max_size=5*1024*1024, backup_count=3):
        """
        Initialize logger with file and console handlers.
        
        Args:
            name (str): Logger name (usually module name)
            log_dir (str): Directory to store log files
            level (int): Logging level
            max_size (int): Maximum log file size in bytes
            backup_count (int): Number of backup logs to keep
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Clear existing handlers if any
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create log directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create timestamp for log filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_size, 
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # Create formatter and add to handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.debug(f"Logger initialized: {name}")
    
    def debug(self, message):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message):
        """Log critical message."""
        self.logger.critical(message)
    
    def exception(self, message):
        """Log exception with traceback."""
        self.logger.exception(message)


# Create a default application logger
app_logger = Logger("sem_workflow_manager", level=logging.INFO)
