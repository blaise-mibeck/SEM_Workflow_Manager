"""
Configuration management for SEM Image Workflow Manager.
"""

import os
import json
from utils.logger import Logger

logger = Logger(__name__)


class Config:
    """
    Configuration manager for application settings.
    """
    
    def __init__(self, config_file="config.json"):
        """
        Initialize configuration manager.
        
        Args:
            config_file (str): Path to configuration file
        """
        self.config_file = config_file
        self.config = {}
        
        # Default configuration
        self.defaults = {
            "recent_sessions": [],
            "max_recent_sessions": 10,
            "default_export_path": os.path.expanduser("~/Documents"),
            "log_level": "INFO",
            "template_match_threshold": 0.1,
            "ui": {
                "theme": "default",
                "font_size": 10,
                "window_size": [1200, 800],
                "window_position": [100, 100]
            },
            "mode_grid": {
                "scene_match_tolerance": 0.01,
                "label_font_size": 36,
                "preferred_modes_order": ["sed", "bsd", "topo", "edx"],
                "label_mode": True,
                "label_voltage": True,
                "label_current": True,
                "label_integrations": True
            }
        }
        
        # Load configuration
        self.load()
    
    def load(self):
        """
        Load configuration from file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
                return True
            else:
                # Use defaults
                self.config = self.defaults.copy()
                logger.info("Using default configuration")
                return self.save()
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            # Use defaults
            self.config = self.defaults.copy()
            return False
    
    def save(self):
        """
        Save configuration to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get(self, key, default=None):
        """
        Get a configuration value.
        
        Args:
            key (str): Configuration key (dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            # Try to get from defaults
            try:
                value = self.defaults
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default
    
    def set(self, key, value):
        """
        Set a configuration value.
        
        Args:
            key (str): Configuration key (dot notation for nested keys)
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        keys = key.split('.')
        target = self.config
        
        # Navigate to the correct nested dictionary
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Set the value
        target[keys[-1]] = value
        
        # Save the configuration
        return self.save()
    
    def add_recent_session(self, session_path):
        """
        Add a session to the recent sessions list.
        
        Args:
            session_path (str): Path to session folder
            
        Returns:
            bool: True if successful, False otherwise
        """
        recent_sessions = self.get('recent_sessions', [])
        
        # Remove if already exists
        if session_path in recent_sessions:
            recent_sessions.remove(session_path)
        
        # Add to beginning of list
        recent_sessions.insert(0, session_path)
        
        # Limit to max recent sessions
        max_recent = self.get('max_recent_sessions', 10)
        recent_sessions = recent_sessions[:max_recent]
        
        # Update config
        return self.set('recent_sessions', recent_sessions)


# Create a global config instance
config = Config()
