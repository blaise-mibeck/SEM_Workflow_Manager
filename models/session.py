"""
Session data model for SEM Image Workflow Manager.
Handles session information storage and retrieval.
"""

import os
import json
import datetime
from utils.logger import Logger

logger = Logger(__name__)


class SessionInfo:
    """
    Stores and manages session information for a set of SEM images.
    """
    
    def __init__(self, session_folder):
        """
        Initialize session information.
        
        Args:
            session_folder (str): Path to the session folder
        """
        self.session_folder = session_folder
        self.info_file = os.path.join(session_folder, "session_info.json")
        
        # Basic session information
        self.session_type = "EDX"  # Default session type
        self.sample_id = ""
        self.sample_name = ""  # Sample name field
        self.client_sample_id = ""  # Changed from client_sample_name to match SEM_Session_Manager
        self.tcl_sample_id = ""  # Changed from tcl_id to match SEM_Session_Manager
        self.project_number = ""  # Added project number
        self.sample_type = ""
        self.stub_type = "Standard 12.5mm"  # Default stub type
        self.electrically_conductive = False  # Added conductive property
        self.preparation_method = ""
        self.gold_coating_thickness = ""  # Added coating thickness
        self.vacuum_drying_time = ""  # Added vacuum drying time
        self.stage_position = ""  # Added stage position
        self.operator_name = ""
        self.notes = ""
        
        # Timestamps (in ISO format to match SEM_Session_Manager)
        self.creation_time = datetime.datetime.now().isoformat()
        self.start_time = ""
        self.end_time = ""
        self.total_time_seconds = 0
        self.is_active = False
        
        # For backward compatibility
        self.creation_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_modified = self.creation_date
        self.history = []
        
        # Try to load existing session information
        if os.path.exists(self.info_file):
            self.load()
        else:
            logger.info(f"Creating new session info for: {session_folder}")
    
    def load(self):
        """
        Load session information from JSON file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.info_file, 'r') as f:
                data = json.load(f)
            
            # Check if this is a SEM_Session_Manager format file
            if "session_type" in data and "tcl_sample_id" in data:
                # Load fields using SEM_Session_Manager format
                self.session_type = data.get("session_type", "EDX")
                self.sample_id = data.get("client_sample_id", "")  # Map to appropriate field
                self.sample_name = data.get("client_sample_id", "")  # For backward compatibility
                self.client_sample_id = data.get("client_sample_id", "")
                self.tcl_sample_id = data.get("tcl_sample_id", "")
                self.project_number = data.get("project_number", "")
                self.sample_type = data.get("sample_type", "")
                self.stub_type = data.get("stub_type", "Standard 12.5mm")
                self.electrically_conductive = data.get("electrically_conductive", False)
                self.preparation_method = data.get("preparation_method", "")
                self.gold_coating_thickness = data.get("gold_coating_thickness", "")
                self.vacuum_drying_time = data.get("vacuum_drying_time", "")
                self.stage_position = data.get("stage_position", "")
                self.operator_name = data.get("operator_name", "")
                
                # Handle timestamps
                self.creation_time = data.get("creation_time", self.creation_time)
                self.start_time = data.get("start_time", "")
                self.end_time = data.get("end_time", "")
                self.total_time_seconds = data.get("total_time_seconds", 0)
                self.is_active = data.get("is_active", False)
                
                # Set backward compatible fields
                creation_dt = datetime.datetime.fromisoformat(self.creation_time.replace('Z', '+00:00'))
                self.creation_date = creation_dt.strftime("%Y-%m-%d %H:%M:%S")
                self.last_modified = self.creation_date
                self.notes = data.get("notes", "")  # Notes might not be in SEM_Session_Manager format
                self.history = []  # Reset history for clean start
            else:
                # Load using original SEM_Workflow_Manager format
                self.sample_id = data.get("sample_id", "")
                self.sample_name = data.get("sample_name", "")
                
                # Map old field names to new ones if present
                self.client_sample_id = data.get("client_sample_name", "")
                self.tcl_sample_id = data.get("tcl_id", "")
                
                # Load fields from original format
                self.sample_type = data.get("sample_type", "")
                self.preparation_method = data.get("preparation_method", "")
                self.operator_name = data.get("operator_name", "")
                self.notes = data.get("notes", "")
                self.creation_date = data.get("creation_date", self.creation_date)
                self.last_modified = data.get("last_modified", self.last_modified)
                self.history = data.get("history", [])
                
                # Set new fields with defaults
                self.session_type = "EDX"
                self.project_number = ""
                self.stub_type = "Standard 12.5mm"
                self.electrically_conductive = False
                self.gold_coating_thickness = ""
                self.vacuum_drying_time = ""
                self.stage_position = ""
                
                # Set timestamps to be compatible with new format
                creation_dt = datetime.datetime.strptime(self.creation_date, "%Y-%m-%d %H:%M:%S")
                self.creation_time = creation_dt.isoformat()
                self.start_time = self.creation_time
                self.end_time = ""
                self.total_time_seconds = 0
                self.is_active = False
            
            logger.info(f"Loaded session info: {self.info_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load session info: {str(e)}")
            return False
    
    def save(self):
        """
        Save session information to JSON file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update last modified timestamp (for backward compatibility)
            self.last_modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Record change in history (for backward compatibility)
            self.history.append({
                "timestamp": self.last_modified,
                "action": "Session information updated"
            })
            
            # Create data dictionary compatible with SEM_Session_Manager
            data = {
                "session_type": self.session_type,
                "operator_name": self.operator_name,
                "project_number": self.project_number,
                "tcl_sample_id": self.tcl_sample_id,
                "client_sample_id": self.client_sample_id,
                "sample_type": self.sample_type,
                "stub_type": self.stub_type,
                "electrically_conductive": self.electrically_conductive,
                "preparation_method": self.preparation_method,
                "gold_coating_thickness": self.gold_coating_thickness,
                "vacuum_drying_time": self.vacuum_drying_time,
                "stage_position": self.stage_position,
                "creation_time": self.creation_time,
                "start_time": self.start_time if self.start_time else self.creation_time,
                "end_time": self.end_time,
                "total_time_seconds": self.total_time_seconds,
                "is_active": self.is_active,
                "session_folder": os.path.basename(self.session_folder),
                
                # Include original fields for backward compatibility
                "sample_id": self.sample_id,
                "sample_name": self.sample_name,
                "notes": self.notes,
                "creation_date": self.creation_date,
                "last_modified": self.last_modified,
                "history": self.history
            }
            
            # Save to file
            with open(self.info_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            logger.info(f"Saved session info: {self.info_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session info: {str(e)}")
            return False
    
    def update_field(self, field_name, value):
        """
        Update a specific field and record the change in history.
        
        Args:
            field_name (str): Name of the field to update
            value (str): New value for the field
            
        Returns:
            bool: True if successful, False otherwise
        """
        if hasattr(self, field_name):
            old_value = getattr(self, field_name)
            setattr(self, field_name, value)
            
            # Record change in history
            self.history.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": f"Updated {field_name}",
                "old_value": old_value,
                "new_value": value
            })
            
            return True
        else:
            logger.warning(f"Attempted to update unknown field: {field_name}")
            return False

class SessionManager:
    """
    Manages SEM session folders and metadata extraction.
    """
    
    def __init__(self):
        """Initialize session manager."""
        self.current_session = None
        self.session_folder = None
        self.image_files = []
        self.metadata = {}
        
        logger.info("SessionManager initialized")
    
    def _load_metadata_csv(self):
        """
        Load extracted metadata from CSV file in the session folder.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.session_folder:
            return False
        
        try:
            import csv
            from models.metadata_extractor import ImageMetadata
            
            csv_file = os.path.join(self.session_folder, "metadata.csv")
            
            if not os.path.exists(csv_file):
                logger.info(f"Metadata CSV file not found: {csv_file}")
                return False
            
            # Load metadata from CSV
            self.metadata = {}
            
            with open(csv_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Convert string values to appropriate types
                    for key, value in row.items():
                        if value == '':
                            row[key] = None
                        elif value == 'None':
                            row[key] = None
                        else:
                            try:
                                # Try to convert to numeric types if possible
                                if '.' in value:
                                    row[key] = float(value)
                                else:
                                    row[key] = int(value)
                            except (ValueError, TypeError):
                                # Keep as string if conversion fails
                                pass
                    
                    # Create metadata object from row
                    metadata = ImageMetadata.from_dict(row)
                    
                    # Store metadata object by image path
                    if metadata.image_path:
                        self.metadata[metadata.image_path] = metadata
            
            logger.info(f"Loaded metadata for {len(self.metadata)} images from CSV file")
            return True
        except Exception as e:
            logger.error(f"Error loading metadata from CSV: {str(e)}")
            return False


    def open_session(self, folder_path):
        """
        Open a session from the specified folder.
        
        Args:
            folder_path (str): Path to the session folder
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(folder_path):
            logger.error(f"Session folder does not exist: {folder_path}")
            return False
        
        try:
            # Create or load session info
            self.session_folder = folder_path
            self.current_session = SessionInfo(folder_path)
            
            # Find all image files ONLY in the top level of the session folder (no recursion)
            self.image_files = []
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                # Only include files (not directories) that have .tif or .tiff extension
                if os.path.isfile(file_path) and file.lower().endswith(('.tif', '.tiff')):
                    self.image_files.append(file_path)
            
            # Load metadata from CSV if it exists
            self._load_metadata_csv()
            
            logger.info(f"Opened session with {len(self.image_files)} image files: {folder_path}")
            return True
        except Exception as e:
            logger.error(f"Error opening session: {str(e)}")
            return False
    
    def close_session(self):
        """
        Close the current session and save any changes.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.current_session:
            success = self.current_session.save()
            self.current_session = None
            self.session_folder = None
            self.image_files = []
            self.metadata = {}
            
            logger.info("Session closed")
            return success
        return True
    
    def extract_metadata(self, extractor):
        """
        Extract metadata for all image files in the session.
        
        Args:
            extractor: Metadata extractor instance
            
        Returns:
            dict: Dictionary mapping file paths to metadata objects
        """
        self.metadata = {}
        
        for image_path in self.image_files:
            try:
                metadata = extractor.extract_metadata(image_path)
                if metadata:
                    self.metadata[image_path] = metadata
                    logger.debug(f"Extracted metadata: {os.path.basename(image_path)}")
            except Exception as e:
                logger.error(f"Error extracting metadata from {image_path}: {str(e)}")
        
        # Save metadata to CSV file
        self._save_metadata_csv()
        
        logger.info(f"Extracted metadata for {len(self.metadata)} image files")
        return self.metadata
    
    """
    Improvements to SessionManager metadata handling
    """

    def _save_metadata_csv(self):
        """
        Save extracted metadata to CSV file in the session folder.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.metadata or not self.session_folder:
            return False
        
        try:
            import csv
            
            # Get session ID for filename
            session_id = os.path.basename(self.session_folder)
            
            # Use session ID in the metadata filename
            csv_file = os.path.join(self.session_folder, f"{session_id}_metadata.csv")
            
            # Also save with the original name for backward compatibility
            legacy_csv_file = os.path.join(self.session_folder, "metadata.csv")
            
            # Get all possible field names from metadata
            fieldnames = set()
            for metadata in self.metadata.values():
                fieldnames.update(metadata.to_dict().keys())
            
            # Add session_id field
            fieldnames.add("session_id")
            
            # Sort fieldnames for consistent ordering
            fieldnames = sorted(list(fieldnames))
            
            # Write metadata to CSV
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for image_path, metadata in self.metadata.items():
                    # Create a copy of the metadata dict
                    meta_dict = metadata.to_dict()
                    
                    # Add session_id
                    meta_dict["session_id"] = session_id
                    
                    writer.writerow(meta_dict)
            
            # Also save with original name for backward compatibility
            with open(legacy_csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for image_path, metadata in self.metadata.items():
                    # Create a copy of the metadata dict
                    meta_dict = metadata.to_dict()
                    
                    # Add session_id
                    meta_dict["session_id"] = session_id
                    
                    writer.writerow(meta_dict)
            
            logger.info(f"Saved metadata to: {csv_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving metadata CSV: {str(e)}")
            return False

    def _load_metadata_csv(self):
        """
        Load extracted metadata from CSV file in the session folder.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.session_folder:
            return False
        
        try:
            import csv
            from models.metadata_extractor import ImageMetadata
            
            # Get session ID for filename
            session_id = os.path.basename(self.session_folder)
            
            # Check for session ID prefixed metadata file first
            csv_file = os.path.join(self.session_folder, f"{session_id}_metadata.csv")
            
            # Fall back to legacy filename if not found
            if not os.path.exists(csv_file):
                csv_file = os.path.join(self.session_folder, "metadata.csv")
                
                if not os.path.exists(csv_file):
                    logger.info(f"Metadata CSV file not found: {csv_file}")
                    return False
            
            # Load metadata from CSV
            self.metadata = {}
            
            with open(csv_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Remove session_id field if present (not needed in ImageMetadata)
                    row.pop("session_id", None)
                    
                    # Convert string values to appropriate types
                    for key, value in row.items():
                        if value == '':
                            row[key] = None
                        elif value == 'None':
                            row[key] = None
                        else:
                            try:
                                # Try to convert to numeric types if possible
                                if '.' in value:
                                    row[key] = float(value)
                                else:
                                    row[key] = int(value)
                            except (ValueError, TypeError):
                                # Keep as string if conversion fails
                                pass
                    
                    # Create metadata object from row
                    metadata = ImageMetadata.from_dict(row)
                    
                    # Store metadata object by image path
                    if metadata.image_path:
                        self.metadata[metadata.image_path] = metadata
            
            logger.info(f"Loaded metadata for {len(self.metadata)} images from CSV file")
            return True
        except Exception as e:
            logger.error(f"Error loading metadata from CSV: {str(e)}")
            return False
