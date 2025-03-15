"""
Base workflow class for SEM Image Workflow Manager.
Defines the common interface and functionality for all workflows.
"""

import os
import json
from abc import ABC, abstractmethod
from utils.logger import Logger

logger = Logger(__name__)


def convert_to_serializable(obj):
    """
    Convert numpy and pandas types to JSON serializable Python types.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON serializable object
    """
    # Try to import numpy and pandas
    try:
        import numpy as np
        import pandas as pd
        
        if isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return convert_to_serializable(obj.tolist())
        elif isinstance(obj, pd.Series):
            return convert_to_serializable(obj.tolist())
        elif isinstance(obj, pd.DataFrame):
            return convert_to_serializable(obj.to_dict(orient='records'))
        elif pd.isna(obj):
            return None
        else:
            return obj
    except ImportError:
        # If numpy or pandas aren't available, just return the object
        return obj


class WorkflowBase(ABC):
    """
    Base class for all workflow types.
    """
    
    def __init__(self, session_manager):
        """
        Initialize workflow with session manager.
        
        Args:
            session_manager: Session manager instance
        """
        self.session_manager = session_manager
        self.collections = []
        self.workflow_folder = None
        
        if session_manager and session_manager.session_folder:
            self._setup_workflow_folder()
    
    def _setup_workflow_folder(self):
        """
        Create the workflow-specific folder in the session folder.
        """
        if not self.session_manager or not self.session_manager.session_folder:
            return
        
        workflow_name = self.__class__.__name__
        self.workflow_folder = os.path.join(
            self.session_manager.session_folder,
            workflow_name
        )
        
        if not os.path.exists(self.workflow_folder):
            os.makedirs(self.workflow_folder)
            logger.info(f"Created workflow folder: {self.workflow_folder}")
    
    @abstractmethod
    def name(self):
        """
        Get the user-friendly name of the workflow.
        
        Returns:
            str: Workflow name
        """
        pass
    
    @abstractmethod
    def description(self):
        """
        Get the description of the workflow.
        
        Returns:
            str: Workflow description
        """
        pass
    
    @abstractmethod
    def discover_collections(self):
        """
        Discover and create collections based on workflow criteria.
        
        Returns:
            list: List of collections
        """
        pass
    
    @abstractmethod
    def create_grid(self, collection, layout=None):
        """
        Create a grid visualization for the collection.
        
        Args:
            collection: Collection to visualize
            layout (tuple, optional): Grid layout as (rows, columns)
            
        Returns:
            PIL.Image: Grid visualization image
        """
        pass
    
    def save_collection(self, collection):
        """
        Save a collection to a file in the workflow folder.
        
        Args:
            collection: Collection to save
            
        Returns:
            str: Path to saved collection file
        """
        # Make sure workflow folder is set up - important for CompareGrid!
        if not self.workflow_folder:
            self._setup_workflow_folder()
            
            # If still not set, use a default location in the main session folder
            if not self.workflow_folder and self.session_manager and self.session_manager.session_folder:
                workflow_name = self.__class__.__name__
                self.workflow_folder = os.path.join(
                    self.session_manager.session_folder, 
                    workflow_name
                )
                
                if not os.path.exists(self.workflow_folder):
                    os.makedirs(self.workflow_folder)
                    logger.info(f"Created fallback workflow folder: {self.workflow_folder}")
        
        # Create a unique ID for the collection if it doesn't have one
        if "id" not in collection:
            import uuid
            collection["id"] = str(uuid.uuid4())
        
        # Generate a filename for the collection
        filename = f"collection_{collection['id']}.json"
        
        # If workflow folder is still None, this will crash, but that means
        # there's a deeper issue with the session structure
        if not self.workflow_folder:
            logger.error("No workflow folder available for saving collection")
            # Use a temp folder as last resort
            import tempfile
            self.workflow_folder = tempfile.gettempdir()
            logger.info(f"Using temporary folder as fallback: {self.workflow_folder}")
        
        filepath = os.path.join(self.workflow_folder, filename)
        
        # Convert collection to JSON serializable format
        serializable_collection = convert_to_serializable(collection)
        
        # Save the collection to a JSON file
        with open(filepath, 'w') as f:
            json.dump(serializable_collection, f, indent=4)
        
        logger.info(f"Saved collection: {filepath}")
        return filepath
    
    def load_collections(self):
        """
        Load all collections from the workflow folder.
        
        Returns:
            list: List of collections
        """
        self.collections = []
        
        if not self.workflow_folder or not os.path.exists(self.workflow_folder):
            return self.collections
        
        # Load all JSON files in the workflow folder
        for filename in os.listdir(self.workflow_folder):
            if filename.endswith(".json"):
                filepath = os.path.join(self.workflow_folder, filename)
                try:
                    with open(filepath, 'r') as f:
                        collection = json.load(f)
                    self.collections.append(collection)
                    logger.debug(f"Loaded collection: {filepath}")
                except Exception as e:
                    logger.error(f"Error loading collection {filepath}: {str(e)}")
        
        logger.info(f"Loaded {len(self.collections)} collections")
        return self.collections
    
    def export_grid(self, grid_image, collection):
        """
        Export a grid visualization as a PNG file to the project folder.
        
        Args:
            grid_image: PIL Image object
            collection: Collection data
            
        Returns:
            tuple: (image_path, caption_path) paths to the exported files
        """
        # Add necessary imports
        import datetime
        
        try:
            # Determine project folder (parent of sessions)
            project_folder = None
            
            if self.session_manager and self.session_manager.session_folder:
                # Use the parent directory of the current session as the project folder
                project_folder = os.path.dirname(self.session_manager.session_folder)
            
            # If for some reason we can't determine the project folder, fall back to the workflow folder
            if not project_folder:
                if self.workflow_folder:
                    project_folder = self.workflow_folder
                elif self.session_manager and self.session_manager.session_folder:
                    project_folder = os.path.join(
                        self.session_manager.session_folder, 
                        self.__class__.__name__
                    )
                    if not os.path.exists(project_folder):
                        os.makedirs(project_folder)
                else:
                    # Last resort fallback to temp directory
                    import tempfile
                    project_folder = tempfile.gettempdir()
                    logger.warning(f"Using temporary folder as fallback: {project_folder}")
            
            # Create a "Grids" folder in the project folder
            grids_folder = os.path.join(project_folder, "Grids")
            if not os.path.exists(grids_folder):
                try:
                    os.makedirs(grids_folder)
                    logger.info(f"Created Grids folder: {grids_folder}")
                except Exception as e:
                    logger.error(f"Failed to create Grids folder, using project folder: {str(e)}")
                    grids_folder = project_folder
            
            # Get session information
            if self.session_manager and self.session_manager.current_session:
                sample_id = self.session_manager.current_session.sample_id
                session_folder_name = os.path.basename(self.session_manager.session_folder)
            else:
                sample_id = "Unknown"
                session_folder_name = "Session"
            
            # For CompareGrid, customize the export name with sample IDs from all sessions
            if collection.get("type") == "CompareGrid":
                workflow_name = "CompareGrid"
                
                # Collect sample IDs from all images in the collection
                sample_ids = []
                for img in collection.get("images", []):
                    if img.get("sample_id") and img.get("sample_id") not in sample_ids:
                        sample_ids.append(img.get("sample_id"))
                
                # Use combined sample IDs in filename (limit to first 3 for length)
                if sample_ids:
                    if len(sample_ids) <= 3:
                        sample_id = "_".join(sample_ids)
                    else:
                        sample_id = "_".join(sample_ids[:3]) + "_etc"
            else:
                workflow_name = self.__class__.__name__
            
            # Add magnification and mode to the filename for better identification
            mag = collection.get("magnification", "")
            mode = collection.get("mode", "")
            
            # Add timestamp for uniqueness
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # Generate a unique filename
            if mag and mode:
                base_filename = f"{workflow_name}_{mode}_{mag}x_{sample_id}_{timestamp}"
            else:
                base_filename = f"{workflow_name}_{sample_id}_{timestamp}"
            
            image_filename = f"{base_filename}.png"
            caption_filename = f"{base_filename}.txt"
            collection_filename = f"{base_filename}.json"
            
            # Create full paths
            image_path = os.path.join(grids_folder, image_filename)
            caption_path = os.path.join(grids_folder, caption_filename)
            collection_path = os.path.join(grids_folder, collection_filename)
            
            # Save the grid image
            logger.info(f"Saving grid image to: {image_path}")
            grid_image.save(image_path, format="PNG")
            
            # Create a caption file
            logger.info(f"Saving caption to: {caption_path}")
            with open(caption_path, 'w') as f:
                f.write(self._generate_caption(collection))
            
            # Convert to serializable format and save the collection data
            logger.info(f"Saving collection data to: {collection_path}")
            serializable_collection = convert_to_serializable(collection)
            with open(collection_path, 'w') as f:
                json.dump(serializable_collection, f, indent=4)
            
            logger.info(f"Export completed successfully")
            
            return image_path, caption_path
            
        except Exception as e:
            logger.exception(f"Error during export: {str(e)}")
            raise Exception(f"Failed to export grid: {str(e)}")
    
    def _generate_caption(self, collection):
        """
        Generate a caption for the grid visualization.
        
        Args:
            collection: Collection data
            
        Returns:
            str: Caption text
        """
        # Default implementation, to be overridden by subclasses
        sample_id = "Unknown"
        if self.session_manager and self.session_manager.current_session:
            sample_id = self.session_manager.current_session.sample_id
        
        workflow_name = self.__class__.__name__
        
        return f"Sample {sample_id} {workflow_name} visualization."