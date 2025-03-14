"""
Base workflow class for SEM Image Workflow Manager.
Defines the common interface and functionality for all workflows.
"""

import os
import json
from abc import ABC, abstractmethod
from utils.logger import Logger

logger = Logger(__name__)


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
        if not self.workflow_folder:
            self._setup_workflow_folder()
        
        # Generate a unique ID for the collection if it doesn't have one
        if "id" not in collection:
            import uuid
            collection["id"] = str(uuid.uuid4())
        
        # Generate a filename for the collection
        filename = f"collection_{collection['id']}.json"
        filepath = os.path.join(self.workflow_folder, filename)
        
        # Save the collection to a JSON file
        with open(filepath, 'w') as f:
            json.dump(collection, f, indent=4)
        
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
        Export a grid visualization as a PNG file.
        
        Args:
            grid_image: PIL Image object
            collection: Collection data
            
        Returns:
            tuple: (image_path, caption_path) paths to the exported files
        """
        if not self.workflow_folder:
            self._setup_workflow_folder()
        
        # Get sample ID from session info
        sample_id = "Unknown"
        if self.session_manager and self.session_manager.current_session:
            sample_id = self.session_manager.current_session.sample_id
        
        # Get session folder name (SEM1-###)
        session_folder_name = os.path.basename(self.session_manager.session_folder)
        
        # Determine the next available grid number
        grid_num = 1
        while True:
            # Check if any files with this number exist
            test_filename = f"{session_folder_name}_{sample_id}_MagGrid-{grid_num}.png"
            test_path = os.path.join(self.workflow_folder, test_filename)
            if not os.path.exists(test_path):
                break
            grid_num += 1
        
        # Generate filenames with the new format
        base_filename = f"{session_folder_name}_{sample_id}_MagGrid-{grid_num}"
        image_filename = f"{base_filename}.png"
        caption_filename = f"{base_filename}.txt"
        collection_filename = f"{base_filename}.json"
        
        # Create full paths
        image_path = os.path.join(self.workflow_folder, image_filename)
        caption_path = os.path.join(self.workflow_folder, caption_filename)
        collection_path = os.path.join(self.workflow_folder, collection_filename)
        
        # Save the grid image
        grid_image.save(image_path, format="PNG")
        
        # Create a caption file
        with open(caption_path, 'w') as f:
            f.write(self._generate_caption(collection))
        
        # Save the collection data
        with open(collection_path, 'w') as f:
            import json
            json.dump(collection, f, indent=4)
        
        logger.info(f"Exported grid: {image_path}")
        logger.info(f"Exported caption: {caption_path}")
        logger.info(f"Exported collection data: {collection_path}")
        
        return image_path, caption_path
    
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
