"""
ModeGrid workflow implementation for SEM Image Workflow Manager.
Creates grid visualizations for comparing the same scene with different imaging modes or parameters.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from qtpy import QtWidgets
from utils.logger import Logger
from utils.config import config
from workflows.workflow_base import WorkflowBase

logger = Logger(__name__)


class ModeGridWorkflow(WorkflowBase):
    """
    Implementation of the ModeGrid workflow.
    Creates grid visualizations for comparing the same scene with different imaging modes or parameters.
    """
    
    def __init__(self, session_manager):
        """
        Initialize ModeGrid workflow.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__(session_manager)
        # Get scene matching tolerance from config (default 12%)
        self.scene_match_tolerance = float(config.get('mode_grid.scene_match_tolerance', 0.12))
        # Default order of modes for sorting
        self.preferred_modes_order = config.get('mode_grid.preferred_modes_order', 
                                                ["sed", "bsd", "topo", "edx"])
    
    def name(self):
        """Get the user-friendly name of the workflow."""
        return "ModeGrid"
    
    def description(self):
        """Get the description of the workflow."""
        return "Compare the same scene with different imaging modes or parameters"
    
    def discover_collections(self):
        """
        Discover and create collections based on ModeGrid criteria with enhanced diagnostics.
        
        Returns:
            list: List of collections
        """
        self.collections = []
        
        if not self.session_manager or not self.session_manager.metadata:
            logger.warning("No metadata available for ModeGrid collection discovery")
            return self.collections
        
        # Log basic info about available metadata
        total_images = len(self.session_manager.metadata)
        valid_images = sum(1 for m in self.session_manager.metadata.values() if m.is_valid())
        
        logger.info(f"Starting ModeGrid collection discovery with {valid_images}/{total_images} valid images")
        
        # First, check if manual Collection field exists in metadata
        has_collection_field = False
        collection_groups = {}
        
        # Look for Collection field
        for img_path, metadata in self.session_manager.metadata.items():
            if not metadata.is_valid():
                continue
            
            # Check for Collection field in additional_params
            if hasattr(metadata, 'additional_params') and isinstance(metadata.additional_params, dict):
                if 'Collection' in metadata.additional_params and metadata.additional_params['Collection']:
                    has_collection_field = True
                    collection_id = metadata.additional_params['Collection']
                    
                    if collection_id not in collection_groups:
                        collection_groups[collection_id] = []
                        
                    collection_groups[collection_id].append(img_path)
        
        # Log if Collection field was found
        if has_collection_field:
            logger.info(f"Found {len(collection_groups)} manual collections via Collection field")
        else:
            logger.info("No manual Collection field found in metadata")
        
        # Count all unique modes present in valid images
        all_modes = {}
        for img_path, metadata in self.session_manager.metadata.items():
            if metadata.is_valid():
                mode = self._get_mode_from_metadata(metadata)
                if mode not in all_modes:
                    all_modes[mode] = 0
                all_modes[mode] += 1
        
        # Log the summary of image modes
        logger.info(f"Found the following modes in metadata:")
        for mode, count in all_modes.items():
            logger.info(f"  - {mode}: {count} images")
        
        # If manual collections exist, use them
        manual_collections_created = 0
        
        if has_collection_field and collection_groups:
            for collection_id, images in collection_groups.items():
                # Skip collections with less than 2 images
                if len(images) < 2:
                    logger.info(f"Skipping manual collection {collection_id} - only {len(images)} images")
                    continue
                    
                # Create collection for these images
                collection = self._create_mode_collection_from_paths(collection_id, images)
                if collection and len(collection["images"]) >= 2:
                    # Check if we have different modes (don't create a collection with same mode)
                    modes = {img["mode"] for img in collection["images"]}
                    if len(modes) >= 2:
                        self.collections.append(collection)
                        self.save_collection(collection)
                        logger.info(f"Created ModeGrid collection from manual group: {collection_id} with {len(collection['images'])} images, {len(modes)} modes")
                        manual_collections_created += 1
                    else:
                        logger.info(f"Skipping manual collection {collection_id} - only has {len(modes)} unique modes")
                else:
                    logger.info(f"Failed to create collection from manual group: {collection_id}")
        
        # Log manual collection results
        if has_collection_field:
            logger.info(f"Created {manual_collections_created} collections from manual Collection field")
            
        # Now try position-based grouping with more diagnostic output
        logger.info("Starting position-based collection discovery")
        position_groups = self._group_by_position()
        
        # Count total position-based collections created
        position_collections_created = 0
        
        # For each position group, find images with different modes
        for position_key, images in position_groups.items():
            # Skip if there's only one image at this position
            if len(images) < 2:
                logger.info(f"Skipping position group {position_key} - only {len(images)} images")
                continue
            
            # Count different modes at this position
            modes = {}
            for img_path in images:
                metadata = self.session_manager.metadata[img_path]
                mode = self._get_mode_from_metadata(metadata)
                if mode not in modes:
                    modes[mode] = 0
                modes[mode] += 1
            
            # Log the modes found at this position
            logger.info(f"Position {position_key} has these modes: {', '.join([f'{m}({c})' for m, c in modes.items()])}")
            
            # If we have multiple modes, create a collection
            if len(modes) >= 2:
                collection = self._create_mode_collection(position_key, images)
                if collection and len(collection["images"]) >= 2:
                    self.collections.append(collection)
                    self.save_collection(collection)
                    logger.info(f"Created ModeGrid collection at position {position_key} with {len(collection['images'])} images")
                    position_collections_created += 1
                else:
                    logger.info(f"Failed to create collection at position {position_key}")
            else:
                logger.info(f"Skipping position {position_key} - only has {len(modes)} unique modes")
        
        # Log position-based collection results
        logger.info(f"Created {position_collections_created} collections from position-based grouping")
        
        # Total results
        logger.info(f"Total discovered ModeGrid collections: {len(self.collections)}")
        return self.collections
    
    def _group_by_position(self):
        """
        Group images by sample position with special handling for ChemSEM.
        
        Returns:
            dict: Dictionary mapping position key to list of image paths
        """
        position_groups = {}
        chemsem_matches = {}
        
        # First, gather all valid images and identify ChemSEM files
        valid_images = []
        chemsem_images = {}  # Filename (without _ChemiSEM) -> ChemSEM path
        normal_images = {}   # Filename -> path
        
        for img_path, metadata in self.session_manager.metadata.items():
            if (metadata.is_valid() and 
                metadata.sample_position_x is not None and 
                metadata.sample_position_y is not None and 
                metadata.field_of_view_width is not None and 
                metadata.field_of_view_height is not None):
                
                valid_images.append((img_path, metadata))
                
                # Identify ChemSEM images by filename
                if "ChemiSEM" in metadata.filename:
                    # Extract base name (remove _ChemiSEM from filename)
                    base_name = metadata.filename.replace("_ChemiSEM", "").replace(".tiff", "").replace(".tif", "")
                    chemsem_images[base_name] = img_path
                else:
                    # Normal image
                    base_name = metadata.filename.replace(".tiff", "").replace(".tif", "")
                    normal_images[base_name] = img_path
        
        # Log count of regular and ChemSEM images
        logger.info(f"Found {len(valid_images)} valid images: {len(normal_images)} regular, {len(chemsem_images)} ChemSEM")
        
        # Match ChemSEM images with their corresponding regular images
        for base_name, regular_path in normal_images.items():
            if base_name in chemsem_images:
                chemsem_path = chemsem_images[base_name]
                chemsem_matches[regular_path] = chemsem_path
                logger.info(f"Matched ChemSEM image to regular image: {base_name}")
        
        # Group by EXACT position values (no rounding or formatting)
        exact_position_groups = {}
        for img_path, metadata in valid_images:
            # Skip ChemSEM images for initial grouping (they'll be added to their matching regular image's group)
            if "ChemiSEM" in metadata.filename:
                continue
                
            # Use the exact numerical values as the key
            pos_key = f"{metadata.sample_position_x}_{metadata.sample_position_y}"
            if pos_key not in exact_position_groups:
                exact_position_groups[pos_key] = []
            exact_position_groups[pos_key].append(img_path)
        
        # Now process matched ChemSEM images
        for regular_path, chemsem_path in chemsem_matches.items():
            # Find which position group contains the regular image
            for pos_key, img_paths in exact_position_groups.items():
                if regular_path in img_paths:
                    # Add the ChemSEM image to the same group
                    img_paths.append(chemsem_path)
                    logger.info(f"Added ChemSEM image to position group {pos_key}")
                    break
        
        # Log the number of exact position groups
        logger.info(f"Created {len(exact_position_groups)} position groups for collection discovery")
        
        # Use the exact position groups directly
        position_groups = exact_position_groups
        
        # For each position group, log the number of images and modes found
        for pos_key, img_paths in position_groups.items():
            # Count unique modes in this group
            modes = set()
            for img_path in img_paths:
                metadata = self.session_manager.metadata[img_path]
                mode = self._get_mode_from_metadata(metadata)
                modes.add(mode)
            
            logger.info(f"Position group {pos_key}: {len(img_paths)} images, {len(modes)} unique modes")
        
        return position_groups
    
    def _are_positions_similar(self, metadata1, metadata2):
        """
        Check if two positions are similar within tolerance or exactly the same.
        
        Args:
            metadata1: First metadata object
            metadata2: Second metadata object
            
        Returns:
            bool: True if positions are similar
        """
        # First, do an exact match check - many consecutive images of same area have exact coordinates
        if (metadata1.sample_position_x == metadata2.sample_position_x and 
            metadata1.sample_position_y == metadata2.sample_position_y):
            return True
        
        # If not exact, do the tolerance-based comparison
        # Compare sample positions
        x1, y1 = metadata1.sample_position_x, metadata1.sample_position_y
        x2, y2 = metadata2.sample_position_x, metadata2.sample_position_y
        
        # Use field of view for tolerance calculation
        fov_width = max(metadata1.field_of_view_width, metadata2.field_of_view_width)
        fov_height = max(metadata1.field_of_view_height, metadata2.field_of_view_height)
        
        # If field of view is very small, use a minimum value to avoid division issues
        min_fov = 10  # 10 μm as a minimum FOV size for calculations
        if fov_width < min_fov:
            fov_width = min_fov
        if fov_height < min_fov:
            fov_height = min_fov
        
        # Calculate position difference as a fraction of field of view
        x_diff = abs(x1 - x2) / fov_width if fov_width > 0 else float('inf')
        y_diff = abs(y1 - y2) / fov_height if fov_height > 0 else float('inf')
        
        # Check if difference is within tolerance
        scene_match_tolerance = float(config.get('mode_grid.scene_match_tolerance', 0.2))
        position_match = (x_diff <= scene_match_tolerance and y_diff <= scene_match_tolerance)
        
        # Also check for similar magnification and pixel dimensions
        mag_tolerance = 0.1  # 10% tolerance for magnification
        mag_match = False
        
        if hasattr(metadata1, 'magnification') and hasattr(metadata2, 'magnification'):
            if metadata1.magnification and metadata2.magnification:
                mag_ratio = abs(metadata1.magnification - metadata2.magnification) / max(metadata1.magnification, metadata2.magnification)
                mag_match = mag_ratio <= mag_tolerance
        
        # Check for similar working distance
        wd_tolerance = 0.2  # 20% tolerance for working distance
        wd_match = False
        
        if hasattr(metadata1, 'working_distance_mm') and hasattr(metadata2, 'working_distance_mm'):
            if metadata1.working_distance_mm and metadata2.working_distance_mm:
                wd_ratio = abs(metadata1.working_distance_mm - metadata2.working_distance_mm) / max(metadata1.working_distance_mm, metadata2.working_distance_mm)
                wd_match = wd_ratio <= wd_tolerance
        
        # Special case for Collection field - if both have the same Collection value, that's an automatic match
        collection_match = False
        
        if hasattr(metadata1, 'additional_params') and hasattr(metadata2, 'additional_params'):
            if isinstance(metadata1.additional_params, dict) and isinstance(metadata2.additional_params, dict):
                if 'Collection' in metadata1.additional_params and 'Collection' in metadata2.additional_params:
                    if metadata1.additional_params['Collection'] and metadata2.additional_params['Collection']:
                        collection_match = metadata1.additional_params['Collection'] == metadata2.additional_params['Collection']
        
        # Consider images the same scene if:
        # 1. Positions match within tolerance AND working distance or magnification match
        # 2. OR they have the same Collection value
        return (position_match and (mag_match or wd_match)) or collection_match
    
    def _get_mode_from_metadata(self, metadata):
        """
        Extract the imaging mode from metadata with support for ChemSEM.
        
        Args:
            metadata: Metadata object
            
        Returns:
            str: Mode identifier (sed, bsd, topo-a, topo-b, chemsem, etc.)
                 Now includes high voltage in format: mode_NNkV
        """
        # Check for ChemSEM based on filename
        if hasattr(metadata, 'filename') and "ChemiSEM" in metadata.filename:
            # Include high voltage with ChemSEM if available
            if hasattr(metadata, 'high_voltage_kV') and metadata.high_voltage_kV is not None:
                return f"chemsem_{int(abs(metadata.high_voltage_kV))}kv"
            return "chemsem"
            
        # Basic mode from detector type
        basic_mode = metadata.mode.lower() if metadata.mode else "unknown"
        
        # First check the detector field
        detector_mode = None
        if hasattr(metadata, 'mode'):
            if metadata.mode.lower() == "sed":
                detector_mode = "sed"
            elif metadata.mode.lower() in ["bsd", "bsd-all"]:
                detector_mode = "bsd"
        
        # Next check for mix mode which indicates Topo
        # Topo uses different configurations of BSD segments
        if hasattr(metadata, 'mode') and metadata.mode.lower() == "mix":
            # Need to analyze the detector mix factors to determine topo direction
            # Extract mix factors from additional_params or direct attributes
            bsdA = bsdB = bsdC = bsdD = 0
            
            # Try to get from additional_params first
            if hasattr(metadata, 'additional_params') and 'detectorMixFactors' in metadata.additional_params:
                mix_factors = metadata.additional_params['detectorMixFactors']
                if isinstance(mix_factors, dict):
                    bsdA = float(mix_factors.get('bsdA', 0))
                    bsdB = float(mix_factors.get('bsdB', 0))
                    bsdC = float(mix_factors.get('bsdC', 0))
                    bsdD = float(mix_factors.get('bsdD', 0))
            
            # If not found in additional_params, try direct attributes
            elif hasattr(metadata, 'detectorMixFactors_bsdA'):
                bsdA = float(metadata.detectorMixFactors_bsdA) if metadata.detectorMixFactors_bsdA is not None else 0
                bsdB = float(metadata.detectorMixFactors_bsdB) if metadata.detectorMixFactors_bsdB is not None else 0
                bsdC = float(metadata.detectorMixFactors_bsdC) if metadata.detectorMixFactors_bsdC is not None else 0
                bsdD = float(metadata.detectorMixFactors_bsdD) if metadata.detectorMixFactors_bsdD is not None else 0
            
            # Try to determine topo direction from mix factors
            # This logic is based on the examples provided
            if abs(bsdB) > abs(bsdA) and abs(bsdC) > abs(bsdD):
                # Horizontal direction (approximately 136 degrees)
                detector_mode = "topo-h"
            elif abs(bsdA) > abs(bsdB) and abs(bsdD) > abs(bsdC):
                # Vertical direction (approximately 44 degrees)
                detector_mode = "topo-v"
            else:
                # Generic topo if we can't determine direction
                detector_mode = "topo"
        
        # If we haven't determined a mode yet, fall back to the basic mode
        if detector_mode is None:
            detector_mode = basic_mode
            
        # Incorporate high voltage into the mode identifier
        if hasattr(metadata, 'high_voltage_kV') and metadata.high_voltage_kV is not None:
            return f"{detector_mode}_{int(abs(metadata.high_voltage_kV))}kv"
        
        # Return just the detector mode if we don't have high voltage information
        return detector_mode


    def _get_mode_display_name(self, metadata):
        """
        Get a display name for the mode with parameters.
        
        Args:
            metadata: Metadata object
            
        Returns:
            str: Display name for the mode, including high voltage
        """
        mode = self._get_mode_from_metadata(metadata)
        
        # Extract base mode and high voltage parts
        base_mode = mode
        high_voltage = None
        
        # Check if mode includes high voltage suffix
        if "_" in mode:
            parts = mode.split("_")
            base_mode = parts[0]
            # Extract kV if present
            if len(parts) > 1 and "kv" in parts[1]:
                high_voltage = parts[1]
            
        # First determine the base mode display name
        display_name = ""
        if base_mode == "sed":
            display_name = "SED"
        elif base_mode == "bsd":
            display_name = "BSD"
        elif base_mode == "topo-h":
            display_name = "Topo 136°"
        elif base_mode == "topo-v":
            display_name = "Topo 44°"
        elif base_mode.startswith("topo"):
            display_name = "Topo"
        elif base_mode == "chemsem":
            display_name = "ChemSEM"
        elif base_mode == "edx":
            display_name = "EDX"
        else:
            display_name = base_mode.upper()
        
        # Add high voltage if available
        if high_voltage:
            # Clean up the format - e.g., "15kv" to "15 kV"
            hv_value = high_voltage.replace("kv", "")
            display_name += f" {hv_value} kV"
        
        return display_name
    
    def _create_mode_collection(self, position_key, images):
        """
        Create a ModeGrid collection for a group of images at the same position.
        
        Args:
            position_key: Position group key
            images: List of image paths at this position
            
        Returns:
            dict: ModeGrid collection
        """
        # Group images by mode
        mode_images = {}
        for img_path in images:
            metadata = self.session_manager.metadata[img_path]
            mode = self._get_mode_from_metadata(metadata)
            
            if mode not in mode_images:
                mode_images[mode] = []
            
            mode_images[mode].append((img_path, metadata))
        
        # Select the best image for each mode
        # For now, just take the first one, but in the future could implement quality metrics
        collection_images = []
        
        # Track which parameters vary across the collection
        all_hvs = set()
        all_currents = set()
        all_integrations = set()
        
        for mode, mode_imgs in mode_images.items():
            # Select first image as primary
            img_path, metadata = mode_imgs[0]
            
            # Track parameter values
            if metadata.high_voltage_kV is not None:
                all_hvs.add(metadata.high_voltage_kV)
            
            # Extract emission current if available
            emission_current = None
            if hasattr(metadata, 'additional_params') and 'emission_current_uA' in metadata.additional_params:
                emission_current = metadata.additional_params['emission_current_uA']
            elif hasattr(metadata, 'emission_current_uA'):
                emission_current = metadata.emission_current_uA
            
            if emission_current is not None:
                all_currents.add(emission_current)
            
            # Extract integrations if available
            integrations = None
            if hasattr(metadata, 'additional_params') and 'integrations' in metadata.additional_params:
                integrations = metadata.additional_params['integrations']
            elif hasattr(metadata, 'integrations'):
                integrations = metadata.integrations
            
            if integrations is not None:
                all_integrations.add(integrations)
            
            # Add alternatives (if any)
            alternatives = []
            if len(mode_imgs) > 1:
                alternatives = [alt_img[0] for alt_img in mode_imgs[1:]]
            
            # Add to collection images
            collection_images.append({
                "path": img_path,
                "metadata_dict": metadata.to_dict(),
                "mode": mode,
                "display_name": self._get_mode_display_name(metadata),
                "alternatives": alternatives
            })
        
        # Sort collection images by preferred mode order
        def get_mode_sort_key(img_data):
            mode = img_data["mode"]
            # Return the index in preferred_modes_order or a large number if not found
            for i, preferred_mode in enumerate(self.preferred_modes_order):
                if mode.startswith(preferred_mode):
                    return i
            return 999  # For modes not in the preferred list
        
        collection_images.sort(key=get_mode_sort_key)
        
        # Create collection
        reference_metadata = self.session_manager.metadata[images[0]]
        
        collection = {
            "type": "ModeGrid",
            "id": f"mode_grid_{position_key}",
            "images": collection_images,
            "sample_position_x": reference_metadata.sample_position_x,
            "sample_position_y": reference_metadata.sample_position_y,
            "field_of_view_width": reference_metadata.field_of_view_width,
            "field_of_view_height": reference_metadata.field_of_view_height,
            "varying_parameters": {
                "high_voltage": len(all_hvs) > 1,
                "emission_current": len(all_currents) > 1,
                "integrations": len(all_integrations) > 1
            },
            "description": f"Different modes at position {position_key:.6s}"
        }
        
        return collection
    
    def _create_mode_collection_from_paths(self, collection_id, images):
        """
        Create a ModeGrid collection from a list of image paths.
        
        Args:
            collection_id: Collection identifier
            images: List of image paths
            
        Returns:
            dict: ModeGrid collection
        """
        # Group images by mode
        mode_images = {}
        for img_path in images:
            metadata = self.session_manager.metadata[img_path]
            mode = self._get_mode_from_metadata(metadata)
            
            if mode not in mode_images:
                mode_images[mode] = []
            
            mode_images[mode].append((img_path, metadata))
        
        # Select the best image for each mode
        # For now, just take the first one, but in the future could implement quality metrics
        collection_images = []
        
        # Track which parameters vary across the collection
        all_hvs = set()
        all_currents = set()
        all_integrations = set()
        
        for mode, mode_imgs in mode_images.items():
            # Select first image as primary
            img_path, metadata = mode_imgs[0]
            
            # Track parameter values
            if metadata.high_voltage_kV is not None:
                all_hvs.add(metadata.high_voltage_kV)
            
            # Extract emission current if available
            emission_current = None
            if hasattr(metadata, 'additional_params') and 'emission_current_uA' in metadata.additional_params:
                emission_current = metadata.additional_params['emission_current_uA']
            elif hasattr(metadata, 'emission_current_uA'):
                emission_current = metadata.emission_current_uA
            
            if emission_current is not None:
                all_currents.add(emission_current)
            
            # Extract integrations if available
            integrations = None
            if hasattr(metadata, 'additional_params') and 'integrations' in metadata.additional_params:
                integrations = metadata.additional_params['integrations']
            elif hasattr(metadata, 'integrations'):
                integrations = metadata.integrations
            
            if integrations is not None:
                all_integrations.add(integrations)
            
            # Add alternatives (if any)
            alternatives = []
            if len(mode_imgs) > 1:
                alternatives = [alt_img[0] for alt_img in mode_imgs[1:]]
            
            # Add to collection images
            collection_images.append({
                "path": img_path,
                "metadata_dict": metadata.to_dict(),
                "mode": mode,
                "display_name": self._get_mode_display_name(metadata),
                "alternatives": alternatives
            })
        
        # Sort collection images by preferred mode order
        def get_mode_sort_key(img_data):
            mode = img_data["mode"]
            # Return the index in preferred_modes_order or a large number if not found
            for i, preferred_mode in enumerate(self.preferred_modes_order):
                if mode.startswith(preferred_mode):
                    return i
            return 999  # For modes not in the preferred list
        
        collection_images.sort(key=get_mode_sort_key)
        
        # Use the first image for reference data
        reference_metadata = self.session_manager.metadata[images[0]]
        
        collection = {
            "type": "ModeGrid",
            "id": f"mode_grid_{collection_id}",
            "images": collection_images,
            "sample_position_x": reference_metadata.sample_position_x,
            "sample_position_y": reference_metadata.sample_position_y,
            "field_of_view_width": reference_metadata.field_of_view_width,
            "field_of_view_height": reference_metadata.field_of_view_height,
            "varying_parameters": {
                "high_voltage": len(all_hvs) > 1,
                "emission_current": len(all_currents) > 1,
                "integrations": len(all_integrations) > 1
            },
            "description": f"Different modes in collection {collection_id}"
        }
        
        return collection
    
    def create_grid(self, collection, layout=None, options=None):
        """
        Create a grid visualization for the ModeGrid collection with support for ChemSEM.
        
        Args:
            collection: ModeGrid collection to visualize
            layout (tuple, optional): Grid layout as (rows, columns)
            options (dict, optional): Annotation options
            
        Returns:
            PIL.Image: Grid visualization image
        """
        # Add detailed logging to diagnose issues
        if not collection:
            logger.error("Invalid collection for ModeGrid visualization: collection is None")
            return None
            
        if "images" not in collection:
            logger.error("Invalid collection for ModeGrid visualization: 'images' field missing")
            logger.debug(f"Collection keys: {list(collection.keys())}")
            return None
            
        if len(collection["images"]) < 2:
            logger.error(f"Invalid collection for ModeGrid visualization: not enough images ({len(collection['images'])})")
            return None
        
        # Log the collection structure for debugging
        logger.debug(f"Creating grid for collection: {collection['id']}")
        logger.debug(f"Collection contains {len(collection['images'])} images")
        
        # Default options if none provided
        if options is None:
            options = {
                "label_mode": config.get('mode_grid.label_mode', True),
                "label_voltage": config.get('mode_grid.label_voltage', True),
                "label_current": config.get('mode_grid.label_current', True),
                "label_integrations": config.get('mode_grid.label_integrations', True),
                "label_font_size": config.get('mode_grid.label_font_size', 12)
            }
        
        # Determine layout based on number of images if not specified
        images = collection["images"]
        num_images = len(images)
        
        if not layout:
            if num_images == 2:
                layout = (1, 2)  # 1 row, 2 columns
            elif num_images <= 4:
                layout = (2, 2)  # 2 rows, 2 columns
            elif num_images <= 6:
                layout = (2, 3)  # 2 rows, 3 columns
            else:
                layout = (3, 3)  # 3 rows, 3 columns
        
        rows, cols = layout
        logger.info(f"Creating ModeGrid with layout {rows}x{cols} for {num_images} images")
        
        # Load all images
        pil_images = []
        for img_data in images:
            try:
                img_path = img_data["path"]
                logger.debug(f"Loading image: {img_path}")
                if not os.path.exists(img_path):
                    logger.error(f"Image file does not exist: {img_path}")
                    continue
                    
                img = Image.open(img_path)
                pil_images.append(img)
            except Exception as e:
                logger.error(f"Error loading image {img_path}: {str(e)}")
                return None
        
        # Check if we successfully loaded any images
        if len(pil_images) < 2:
            logger.error(f"Not enough images could be loaded: {len(pil_images)}")
            return None
        
        # Determine if we have any ChemSEM images
        has_chemsem = False
        for img_data in images:
            if img_data.get("mode") == "chemsem":
                has_chemsem = True
                break
        
        # Determine the size of grid cells - handle ChemSEM differently
        if has_chemsem:
            # Filter out ChemSEM images for size calculation (only use regular images)
            regular_images = [img for i, img in enumerate(pil_images) 
                            if i < len(images) and images[i].get("mode") != "chemsem"]
            
            # If we have regular images, use their size as reference
            if regular_images:
                cell_width = max(img.width for img in regular_images)
                cell_height = max(img.height for img in regular_images)
            else:
                # Fallback if somehow all images are ChemSEM
                cell_width = max(img.width for img in pil_images)
                cell_height = max(img.height for img in pil_images)
        else:
            # Standard case - use max dimensions
            cell_width = max(img.width for img in pil_images)
            cell_height = max(img.height for img in pil_images)
        
        # Create a blank grid image with spacing
        spacing = 10
        grid_width = cols * cell_width + (cols - 1) * spacing
        grid_height = rows * cell_height + (rows - 1) * spacing
        grid_img = Image.new('RGB', (grid_width, grid_height), color='white')
        
        # Place images in the grid
        draw = ImageDraw.Draw(grid_img)
        
        # Try to load a font with the configured size
        font_size = options.get("label_font_size", 12)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            try:
                # Try system font locations
                import sys
                if sys.platform == "win32":
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
                elif sys.platform == "darwin":  # macOS
                    font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size)
                else:  # Linux
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
                logger.warning(f"Could not load font with size {font_size}, using default font")
        
        # Place images and add labels
        for i, (img_data, img) in enumerate(zip(images, pil_images)):
            row = i // cols
            col = i % cols
            
            # Calculate position
            x = col * (cell_width + spacing)
            y = row * (cell_height + spacing)
            
            # Handle ChemSEM images - resize to fill the entire cell
            if img_data.get("mode") == "chemsem" or "chemsem" in img_data.get("mode", ""):
                # Resize the ChemSEM image to match the cell size exactly without maintaining aspect ratio
                resized_img = img.resize((cell_width, cell_height), Image.LANCZOS)
                
                # Paste directly into the grid at the cell position
                grid_img.paste(resized_img, (x, y))
                
                logger.info(f"Resized ChemSEM image to fill entire cell: {cell_width}x{cell_height}")
            else:
                # Standard image processing - center the image in its cell
                x_offset = (cell_width - img.width) // 2
                y_offset = (cell_height - img.height) // 2
                
                # Paste the image
                grid_img.paste(img, (x + x_offset, y + y_offset))
            
            # Add mode label if enabled
            if options.get("label_mode", True):
                mode_display = img_data.get("display_name", "Unknown")
                
                # We don't need to add voltage here since it's already included in the display_name
                # Just add other parameters if they vary and option is enabled
                metadata_dict = img_data.get("metadata_dict", {})
                varying_parameters = collection.get("varying_parameters", {})
"""
ModeGrid workflow implementation for SEM Image Workflow Manager.
Creates grid visualizations for comparing the same scene with different imaging modes or parameters.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from qtpy import QtWidgets
from utils.logger import Logger
from utils.config import config
from workflows.workflow_base import WorkflowBase

logger = Logger(__name__)


class ModeGridWorkflow(WorkflowBase):
    """
    Implementation of the ModeGrid workflow.
    Creates grid visualizations for comparing the same scene with different imaging modes or parameters.
    """
    
    def __init__(self, session_manager):
        """
        Initialize ModeGrid workflow.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__(session_manager)
        # Get scene matching tolerance from config (default 12%)
        self.scene_match_tolerance = float(config.get('mode_grid.scene_match_tolerance', 0.12))
        # Default order of modes for sorting
        self.preferred_modes_order = config.get('mode_grid.preferred_modes_order', 
                                                ["sed", "bsd", "topo", "edx"])
    
    def name(self):
        """Get the user-friendly name of the workflow."""
        return "ModeGrid"
    
    def description(self):
        """Get the description of the workflow."""
        return "Compare the same scene with different imaging modes or parameters"
    
    def discover_collections(self):
        """
        Discover and create collections based on ModeGrid criteria with enhanced diagnostics.
        
        Returns:
            list: List of collections
        """
        self.collections = []
        
        if not self.session_manager or not self.session_manager.metadata:
            logger.warning("No metadata available for ModeGrid collection discovery")
            return self.collections
        
        # Log basic info about available metadata
        total_images = len(self.session_manager.metadata)
        valid_images = sum(1 for m in self.session_manager.metadata.values() if m.is_valid())
        
        logger.info(f"Starting ModeGrid collection discovery with {valid_images}/{total_images} valid images")
        
        # First, check if manual Collection field exists in metadata
        has_collection_field = False
        collection_groups = {}
        
        # Look for Collection field
        for img_path, metadata in self.session_manager.metadata.items():
            if not metadata.is_valid():
                continue
            
            # Check for Collection field in additional_params
            if hasattr(metadata, 'additional_params') and isinstance(metadata.additional_params, dict):
                if 'Collection' in metadata.additional_params and metadata.additional_params['Collection']:
                    has_collection_field = True
                    collection_id = metadata.additional_params['Collection']
                    
                    if collection_id not in collection_groups:
                        collection_groups[collection_id] = []
                        
                    collection_groups[collection_id].append(img_path)
        
        # Log if Collection field was found
        if has_collection_field:
            logger.info(f"Found {len(collection_groups)} manual collections via Collection field")
        else:
            logger.info("No manual Collection field found in metadata")
        
        # Count all unique modes present in valid images
        all_modes = {}
        for img_path, metadata in self.session_manager.metadata.items():
            if metadata.is_valid():
                mode = self._get_mode_from_metadata(metadata)
                if mode not in all_modes:
                    all_modes[mode] = 0
                all_modes[mode] += 1
        
        # Log the summary of image modes
        logger.info(f"Found the following modes in metadata:")
        for mode, count in all_modes.items():
            logger.info(f"  - {mode}: {count} images")
        
        # If manual collections exist, use them
        manual_collections_created = 0
        
        if has_collection_field and collection_groups:
            for collection_id, images in collection_groups.items():
                # Skip collections with less than 2 images
                if len(images) < 2:
                    logger.info(f"Skipping manual collection {collection_id} - only {len(images)} images")
                    continue
                    
                # Create collection for these images
                collection = self._create_mode_collection_from_paths(collection_id, images)
                if collection and len(collection["images"]) >= 2:
                    # Check if we have different modes (don't create a collection with same mode)
                    modes = {img["mode"] for img in collection["images"]}
                    if len(modes) >= 2:
                        self.collections.append(collection)
                        self.save_collection(collection)
                        logger.info(f"Created ModeGrid collection from manual group: {collection_id} with {len(collection['images'])} images, {len(modes)} modes")
                        manual_collections_created += 1
                    else:
                        logger.info(f"Skipping manual collection {collection_id} - only has {len(modes)} unique modes")
                else:
                    logger.info(f"Failed to create collection from manual group: {collection_id}")
        
        # Log manual collection results
        if has_collection_field:
            logger.info(f"Created {manual_collections_created} collections from manual Collection field")
            
        # Now try position-based grouping with more diagnostic output
        logger.info("Starting position-based collection discovery")
        position_groups = self._group_by_position()
        
        # Count total position-based collections created
        position_collections_created = 0
        
        # For each position group, find images with different modes
        for position_key, images in position_groups.items():
            # Skip if there's only one image at this position
            if len(images) < 2:
                logger.info(f"Skipping position group {position_key} - only {len(images)} images")
                continue
            
            # Count different modes at this position
            modes = {}
            for img_path in images:
                metadata = self.session_manager.metadata[img_path]
                mode = self._get_mode_from_metadata(metadata)
                if mode not in modes:
                    modes[mode] = 0
                modes[mode] += 1
            
            # Log the modes found at this position
            logger.info(f"Position {position_key} has these modes: {', '.join([f'{m}({c})' for m, c in modes.items()])}")
            
            # If we have multiple modes, create a collection
            if len(modes) >= 2:
                collection = self._create_mode_collection(position_key, images)
                if collection and len(collection["images"]) >= 2:
                    self.collections.append(collection)
                    self.save_collection(collection)
                    logger.info(f"Created ModeGrid collection at position {position_key} with {len(collection['images'])} images")
                    position_collections_created += 1
                else:
                    logger.info(f"Failed to create collection at position {position_key}")
            else:
                logger.info(f"Skipping position {position_key} - only has {len(modes)} unique modes")
        
        # Log position-based collection results
        logger.info(f"Created {position_collections_created} collections from position-based grouping")
        
        # Total results
        logger.info(f"Total discovered ModeGrid collections: {len(self.collections)}")
        return self.collections
    
    def _group_by_position(self):
        """
        Group images by sample position with special handling for ChemSEM.
        
        Returns:
            dict: Dictionary mapping position key to list of image paths
        """
        position_groups = {}
        chemsem_matches = {}
        
        # First, gather all valid images and identify ChemSEM files
        valid_images = []
        chemsem_images = {}  # Filename (without _ChemiSEM) -> ChemSEM path
        normal_images = {}   # Filename -> path
        
        for img_path, metadata in self.session_manager.metadata.items():
            if (metadata.is_valid() and 
                metadata.sample_position_x is not None and 
                metadata.sample_position_y is not None and 
                metadata.field_of_view_width is not None and 
                metadata.field_of_view_height is not None):
                
                valid_images.append((img_path, metadata))
                
                # Identify ChemSEM images by filename
                if "ChemiSEM" in metadata.filename:
                    # Extract base name (remove _ChemiSEM from filename)
                    base_name = metadata.filename.replace("_ChemiSEM", "").replace(".tiff", "").replace(".tif", "")
                    chemsem_images[base_name] = img_path
                else:
                    # Normal image
                    base_name = metadata.filename.replace(".tiff", "").replace(".tif", "")
                    normal_images[base_name] = img_path
        
        # Log count of regular and ChemSEM images
        logger.info(f"Found {len(valid_images)} valid images: {len(normal_images)} regular, {len(chemsem_images)} ChemSEM")
        
        # Match ChemSEM images with their corresponding regular images
        for base_name, regular_path in normal_images.items():
            if base_name in chemsem_images:
                chemsem_path = chemsem_images[base_name]
                chemsem_matches[regular_path] = chemsem_path
                logger.info(f"Matched ChemSEM image to regular image: {base_name}")
        
        # Group by EXACT position values (no rounding or formatting)
        exact_position_groups = {}
        for img_path, metadata in valid_images:
            # Skip ChemSEM images for initial grouping (they'll be added to their matching regular image's group)
            if "ChemiSEM" in metadata.filename:
                continue
                
            # Use the exact numerical values as the key
            pos_key = f"{metadata.sample_position_x}_{metadata.sample_position_y}"
            if pos_key not in exact_position_groups:
                exact_position_groups[pos_key] = []
            exact_position_groups[pos_key].append(img_path)
        
        # Now process matched ChemSEM images
        for regular_path, chemsem_path in chemsem_matches.items():
            # Find which position group contains the regular image
            for pos_key, img_paths in exact_position_groups.items():
                if regular_path in img_paths:
                    # Add the ChemSEM image to the same group
                    img_paths.append(chemsem_path)
                    logger.info(f"Added ChemSEM image to position group {pos_key}")
                    break
        
        # Log the number of exact position groups
        logger.info(f"Created {len(exact_position_groups)} position groups for collection discovery")
        
        # Use the exact position groups directly
        position_groups = exact_position_groups
        
        # For each position group, log the number of images and modes found
        for pos_key, img_paths in position_groups.items():
            # Count unique modes in this group
            modes = set()
            for img_path in img_paths:
                metadata = self.session_manager.metadata[img_path]
                mode = self._get_mode_from_metadata(metadata)
                modes.add(mode)
            
            logger.info(f"Position group {pos_key}: {len(img_paths)} images, {len(modes)} unique modes")
        
        return position_groups
    
    def _are_positions_similar(self, metadata1, metadata2):
        """
        Check if two positions are similar within tolerance or exactly the same.
        
        Args:
            metadata1: First metadata object
            metadata2: Second metadata object
            
        Returns:
            bool: True if positions are similar
        """
        # First, do an exact match check - many consecutive images of same area have exact coordinates
        if (metadata1.sample_position_x == metadata2.sample_position_x and 
            metadata1.sample_position_y == metadata2.sample_position_y):
            return True
        
        # If not exact, do the tolerance-based comparison
        # Compare sample positions
        x1, y1 = metadata1.sample_position_x, metadata1.sample_position_y
        x2, y2 = metadata2.sample_position_x, metadata2.sample_position_y
        
        # Use field of view for tolerance calculation
        fov_width = max(metadata1.field_of_view_width, metadata2.field_of_view_width)
        fov_height = max(metadata1.field_of_view_height, metadata2.field_of_view_height)
        
        # If field of view is very small, use a minimum value to avoid division issues
        min_fov = 10  # 10 μm as a minimum FOV size for calculations
        if fov_width < min_fov:
            fov_width = min_fov
        if fov_height < min_fov:
            fov_height = min_fov
        
        # Calculate position difference as a fraction of field of view
        x_diff = abs(x1 - x2) / fov_width if fov_width > 0 else float('inf')
        y_diff = abs(y1 - y2) / fov_height if fov_height > 0 else float('inf')
        
        # Check if difference is within tolerance
        scene_match_tolerance = float(config.get('mode_grid.scene_match_tolerance', 0.2))
        position_match = (x_diff <= scene_match_tolerance and y_diff <= scene_match_tolerance)
        
        # Also check for similar magnification and pixel dimensions
        mag_tolerance = 0.1  # 10% tolerance for magnification
        mag_match = False
        
        if hasattr(metadata1, 'magnification') and hasattr(metadata2, 'magnification'):
            if metadata1.magnification and metadata2.magnification:
                mag_ratio = abs(metadata1.magnification - metadata2.magnification) / max(metadata1.magnification, metadata2.magnification)
                mag_match = mag_ratio <= mag_tolerance
        
        # Check for similar working distance
        wd_tolerance = 0.2  # 20% tolerance for working distance
        wd_match = False
        
        if hasattr(metadata1, 'working_distance_mm') and hasattr(metadata2, 'working_distance_mm'):
            if metadata1.working_distance_mm and metadata2.working_distance_mm:
                wd_ratio = abs(metadata1.working_distance_mm - metadata2.working_distance_mm) / max(metadata1.working_distance_mm, metadata2.working_distance_mm)
                wd_match = wd_ratio <= wd_tolerance
        
        # Special case for Collection field - if both have the same Collection value, that's an automatic match
        collection_match = False
        
        if hasattr(metadata1, 'additional_params') and hasattr(metadata2, 'additional_params'):
            if isinstance(metadata1.additional_params, dict) and isinstance(metadata2.additional_params, dict):
                if 'Collection' in metadata1.additional_params and 'Collection' in metadata2.additional_params:
                    if metadata1.additional_params['Collection'] and metadata2.additional_params['Collection']:
                        collection_match = metadata1.additional_params['Collection'] == metadata2.additional_params['Collection']
        
        # Consider images the same scene if:
        # 1. Positions match within tolerance AND working distance or magnification match
        # 2. OR they have the same Collection value
        return (position_match and (mag_match or wd_match)) or collection_match
    
    def _get_mode_from_metadata(self, metadata):
        """
        Extract the imaging mode from metadata with support for ChemSEM.
        
        Args:
            metadata: Metadata object
            
        Returns:
            str: Mode identifier (sed, bsd, topo-a, topo-b, chemsem, etc.)
                 Now includes high voltage in format: mode_NNkV
        """
        # Check for ChemSEM based on filename
        if hasattr(metadata, 'filename') and "ChemiSEM" in metadata.filename:
            # Include high voltage with ChemSEM if available
            if hasattr(metadata, 'high_voltage_kV') and metadata.high_voltage_kV is not None:
                return f"chemsem_{int(abs(metadata.high_voltage_kV))}kv"
            return "chemsem"
            
        # Basic mode from detector type
        basic_mode = metadata.mode.lower() if metadata.mode else "unknown"
        
        # First check the detector field
        detector_mode = None
        if hasattr(metadata, 'mode'):
            if metadata.mode.lower() == "sed":
                detector_mode = "sed"
            elif metadata.mode.lower() in ["bsd", "bsd-all"]:
                detector_mode = "bsd"
        
        # Next check for mix mode which indicates Topo
        # Topo uses different configurations of BSD segments
        if hasattr(metadata, 'mode') and metadata.mode.lower() == "mix":
            # Need to analyze the detector mix factors to determine topo direction
            # Extract mix factors from additional_params or direct attributes
            bsdA = bsdB = bsdC = bsdD = 0
            
            # Try to get from additional_params first
            if hasattr(metadata, 'additional_params') and 'detectorMixFactors' in metadata.additional_params:
                mix_factors = metadata.additional_params['detectorMixFactors']
                if isinstance(mix_factors, dict):
                    bsdA = float(mix_factors.get('bsdA', 0))
                    bsdB = float(mix_factors.get('bsdB', 0))
                    bsdC = float(mix_factors.get('bsdC', 0))
                    bsdD = float(mix_factors.get('bsdD', 0))
            
            # If not found in additional_params, try direct attributes
            elif hasattr(metadata, 'detectorMixFactors_bsdA'):
                bsdA = float(metadata.detectorMixFactors_bsdA) if metadata.detectorMixFactors_bsdA is not None else 0
                bsdB = float(metadata.detectorMixFactors_bsdB) if metadata.detectorMixFactors_bsdB is not None else 0
                bsdC = float(metadata.detectorMixFactors_bsdC) if metadata.detectorMixFactors_bsdC is not None else 0
                bsdD = float(metadata.detectorMixFactors_bsdD) if metadata.detectorMixFactors_bsdD is not None else 0
            
            # Try to determine topo direction from mix factors
            # This logic is based on the examples provided
            if abs(bsdB) > abs(bsdA) and abs(bsdC) > abs(bsdD):
                # Horizontal direction (approximately 136 degrees)
                detector_mode = "topo-h"
            elif abs(bsdA) > abs(bsdB) and abs(bsdD) > abs(bsdC):
                # Vertical direction (approximately 44 degrees)
                detector_mode = "topo-v"
            else:
                # Generic topo if we can't determine direction
                detector_mode = "topo"
        
        # If we haven't determined a mode yet, fall back to the basic mode
        if detector_mode is None:
            detector_mode = basic_mode
            
        # Incorporate high voltage into the mode identifier
        if hasattr(metadata, 'high_voltage_kV') and metadata.high_voltage_kV is not None:
            return f"{detector_mode}_{int(abs(metadata.high_voltage_kV))}kv"
        
        # Return just the detector mode if we don't have high voltage information
        return detector_mode


    def _get_mode_display_name(self, metadata):
        """
        Get a display name for the mode with parameters.
        
        Args:
            metadata: Metadata object
            
        Returns:
            str: Display name for the mode, including high voltage
        """
        mode = self._get_mode_from_metadata(metadata)
        
        # Extract base mode and high voltage parts
        base_mode = mode
        high_voltage = None
        
        # Check if mode includes high voltage suffix
        if "_" in mode:
            parts = mode.split("_")
            base_mode = parts[0]
            # Extract kV if present
            if len(parts) > 1 and "kv" in parts[1]:
                high_voltage = parts[1]
            
        # First determine the base mode display name
        display_name = ""
        if base_mode == "sed":
            display_name = "SED"
        elif base_mode == "bsd":
            display_name = "BSD"
        elif base_mode == "topo-h":
            display_name = "Topo 136°"
        elif base_mode == "topo-v":
            display_name = "Topo 44°"
        elif base_mode.startswith("topo"):
            display_name = "Topo"
        elif base_mode == "chemsem":
            display_name = "ChemSEM"
        elif base_mode == "edx":
            display_name = "EDX"
        else:
            display_name = base_mode.upper()
        
        # Add high voltage if available
        if high_voltage:
            # Clean up the format - e.g., "15kv" to "15 kV"
            hv_value = high_voltage.replace("kv", "")
            display_name += f" {hv_value} kV"
        
        return display_name
    
    def _create_mode_collection(self, position_key, images):
        """
        Create a ModeGrid collection for a group of images at the same position.
        
        Args:
            position_key: Position group key
            images: List of image paths at this position
            
        Returns:
            dict: ModeGrid collection
        """
        # Group images by mode
        mode_images = {}
        for img_path in images:
            metadata = self.session_manager.metadata[img_path]
            mode = self._get_mode_from_metadata(metadata)
            
            if mode not in mode_images:
                mode_images[mode] = []
            
            mode_images[mode].append((img_path, metadata))
        
        # Select the best image for each mode
        # For now, just take the first one, but in the future could implement quality metrics
        collection_images = []
        
        # Track which parameters vary across the collection
        all_hvs = set()
        all_currents = set()
        all_integrations = set()
        
        for mode, mode_imgs in mode_images.items():
            # Select first image as primary
            img_path, metadata = mode_imgs[0]
            
            # Track parameter values
            if metadata.high_voltage_kV is not None:
                all_hvs.add(metadata.high_voltage_kV)
            
            # Extract emission current if available
            emission_current = None
            if hasattr(metadata, 'additional_params') and 'emission_current_uA' in metadata.additional_params:
                emission_current = metadata.additional_params['emission_current_uA']
            elif hasattr(metadata, 'emission_current_uA'):
                emission_current = metadata.emission_current_uA
            
            if emission_current is not None:
                all_currents.add(emission_current)
            
            # Extract integrations if available
            integrations = None
            if hasattr(metadata, 'additional_params') and 'integrations' in metadata.additional_params:
                integrations = metadata.additional_params['integrations']
            elif hasattr(metadata, 'integrations'):
                integrations = metadata.integrations
            
            if integrations is not None:
                all_integrations.add(integrations)
            
            # Add alternatives (if any)
            alternatives = []
            if len(mode_imgs) > 1:
                alternatives = [alt_img[0] for alt_img in mode_imgs[1:]]
            
            # Add to collection images
            collection_images.append({
                "path": img_path,
                "metadata_dict": metadata.to_dict(),
                "mode": mode,
                "display_name": self._get_mode_display_name(metadata),
                "alternatives": alternatives
            })
        
        # Sort collection images by preferred mode order
        def get_mode_sort_key(img_data):
            mode = img_data["mode"]
            # Return the index in preferred_modes_order or a large number if not found
            for i, preferred_mode in enumerate(self.preferred_modes_order):
                if mode.startswith(preferred_mode):
                    return i
            return 999  # For modes not in the preferred list
        
        collection_images.sort(key=get_mode_sort_key)
        
        # Create collection
        reference_metadata = self.session_manager.metadata[images[0]]
        
        collection = {
            "type": "ModeGrid",
            "id": f"mode_grid_{position_key}",
            "images": collection_images,
            "sample_position_x": reference_metadata.sample_position_x,
            "sample_position_y": reference_metadata.sample_position_y,
            "field_of_view_width": reference_metadata.field_of_view_width,
            "field_of_view_height": reference_metadata.field_of_view_height,
            "varying_parameters": {
                "high_voltage": len(all_hvs) > 1,
                "emission_current": len(all_currents) > 1,
                "integrations": len(all_integrations) > 1
            },
            "description": f"Different modes at position {position_key:.6s}"
        }
        
        return collection
    
    def _create_mode_collection_from_paths(self, collection_id, images):
        """
        Create a ModeGrid collection from a list of image paths.
        
        Args:
            collection_id: Collection identifier
            images: List of image paths
            
        Returns:
            dict: ModeGrid collection
        """
        # Group images by mode
        mode_images = {}
        for img_path in images:
            metadata = self.session_manager.metadata[img_path]
            mode = self._get_mode_from_metadata(metadata)
            
            if mode not in mode_images:
                mode_images[mode] = []
            
            mode_images[mode].append((img_path, metadata))
        
        # Select the best image for each mode
        # For now, just take the first one, but in the future could implement quality metrics
        collection_images = []
        
        # Track which parameters vary across the collection
        all_hvs = set()
        all_currents = set()
        all_integrations = set()
        
        for mode, mode_imgs in mode_images.items():
            # Select first image as primary
            img_path, metadata = mode_imgs[0]
            
            # Track parameter values
            if metadata.high_voltage_kV is not None:
                all_hvs.add(metadata.high_voltage_kV)
            
            # Extract emission current if available
            emission_current = None
            if hasattr(metadata, 'additional_params') and 'emission_current_uA' in metadata.additional_params:
                emission_current = metadata.additional_params['emission_current_uA']
            elif hasattr(metadata, 'emission_current_uA'):
                emission_current = metadata.emission_current_uA
            
            if emission_current is not None:
                all_currents.add(emission_current)
            
            # Extract integrations if available
            integrations = None
            if hasattr(metadata, 'additional_params') and 'integrations' in metadata.additional_params:
                integrations = metadata.additional_params['integrations']
            elif hasattr(metadata, 'integrations'):
                integrations = metadata.integrations
            
            if integrations is not None:
                all_integrations.add(integrations)
            
            # Add alternatives (if any)
            alternatives = []
            if len(mode_imgs) > 1:
                alternatives = [alt_img[0] for alt_img in mode_imgs[1:]]
            
            # Add to collection images
            collection_images.append({
                "path": img_path,
                "metadata_dict": metadata.to_dict(),
                "mode": mode,
                "display_name": self._get_mode_display_name(metadata),
                "alternatives": alternatives
            })
        
        # Sort collection images by preferred mode order
        def get_mode_sort_key(img_data):
            mode = img_data["mode"]
            # Return the index in preferred_modes_order or a large number if not found
            for i, preferred_mode in enumerate(self.preferred_modes_order):
                if mode.startswith(preferred_mode):
                    return i
            return 999  # For modes not in the preferred list
        
        collection_images.sort(key=get_mode_sort_key)
        
        # Use the first image for reference data
        reference_metadata = self.session_manager.metadata[images[0]]
        
        collection = {
            "type": "ModeGrid",
            "id": f"mode_grid_{collection_id}",
            "images": collection_images,
            "sample_position_x": reference_metadata.sample_position_x,
            "sample_position_y": reference_metadata.sample_position_y,
            "field_of_view_width": reference_metadata.field_of_view_width,
            "field_of_view_height": reference_metadata.field_of_view_height,
            "varying_parameters": {
                "high_voltage": len(all_hvs) > 1,
                "emission_current": len(all_currents) > 1,
                "integrations": len(all_integrations) > 1
            },
            "description": f"Different modes in collection {collection_id}"
        }
        
        return collection
    
    def create_grid(self, collection, layout=None, options=None):
        """
        Create a grid visualization for the ModeGrid collection with support for ChemSEM.
        
        Args:
            collection: ModeGrid collection to visualize
            layout (tuple, optional): Grid layout as (rows, columns)
            options (dict, optional): Annotation options
            
        Returns:
            PIL.Image: Grid visualization image
        """
        # Add detailed logging to diagnose issues
        if not collection:
            logger.error("Invalid collection for ModeGrid visualization: collection is None")
            return None
            
        if "images" not in collection:
            logger.error("Invalid collection for ModeGrid visualization: 'images' field missing")
            logger.debug(f"Collection keys: {list(collection.keys())}")
            return None
            
        if len(collection["images"]) < 2:
            logger.error(f"Invalid collection for ModeGrid visualization: not enough images ({len(collection['images'])})")
            return None
        
        # Log the collection structure for debugging
        logger.debug(f"Creating grid for collection: {collection['id']}")
        logger.debug(f"Collection contains {len(collection['images'])} images")
        
        # Default options if none provided
        if options is None:
            options = {
                "label_mode": config.get('mode_grid.label_mode', True),
                "label_voltage": config.get('mode_grid.label_voltage', True),
                "label_current": config.get('mode_grid.label_current', True),
                "label_integrations": config.get('mode_grid.label_integrations', True),
                "label_font_size": config.get('mode_grid.label_font_size', 12)
            }
        
        # Determine layout based on number of images if not specified
        images = collection["images"]
        num_images = len(images)
        
        if not layout:
            if num_images == 2:
                layout = (1, 2)  # 1 row, 2 columns
            elif num_images <= 4:
                layout = (2, 2)  # 2 rows, 2 columns
            elif num_images <= 6:
                layout = (2, 3)  # 2 rows, 3 columns
            else:
                layout = (3, 3)  # 3 rows, 3 columns
        
        rows, cols = layout
        logger.info(f"Creating ModeGrid with layout {rows}x{cols} for {num_images} images")
        
        # Load all images
        pil_images = []
        for img_data in images:
            try:
                img_path = img_data["path"]
                logger.debug(f"Loading image: {img_path}")
                if not os.path.exists(img_path):
                    logger.error(f"Image file does not exist: {img_path}")
                    continue
                    
                img = Image.open(img_path)
                pil_images.append(img)
            except Exception as e:
                logger.error(f"Error loading image {img_path}: {str(e)}")
                return None
        
        # Check if we successfully loaded any images
        if len(pil_images) < 2:
            logger.error(f"Not enough images could be loaded: {len(pil_images)}")
            return None
        
        # Determine if we have any ChemSEM images
        has_chemsem = False
        for img_data in images:
            if img_data.get("mode") == "chemsem":
                has_chemsem = True
                break
        
        # Determine the size of grid cells - handle ChemSEM differently
        if has_chemsem:
            # Filter out ChemSEM images for size calculation (only use regular images)
            regular_images = [img for i, img in enumerate(pil_images) 
                            if i < len(images) and images[i].get("mode") != "chemsem"]
            
            # If we have regular images, use their size as reference
            if regular_images:
                cell_width = max(img.width for img in regular_images)
                cell_height = max(img.height for img in regular_images)
            else:
                # Fallback if somehow all images are ChemSEM
                cell_width = max(img.width for img in pil_images)
                cell_height = max(img.height for img in pil_images)
        else:
            # Standard case - use max dimensions
            cell_width = max(img.width for img in pil_images)
            cell_height = max(img.height for img in pil_images)
        
        # Create a blank grid image with spacing
        spacing = 10
        grid_width = cols * cell_width + (cols - 1) * spacing
        grid_height = rows * cell_height + (rows - 1) * spacing
        grid_img = Image.new('RGB', (grid_width, grid_height), color='white')
        
        # Place images in the grid
        draw = ImageDraw.Draw(grid_img)
        
        # Try to load a font with the configured size
        font_size = options.get("label_font_size", 12)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            try:
                # Try system font locations
                import sys
                if sys.platform == "win32":
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
                elif sys.platform == "darwin":  # macOS
                    font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size)
                else:  # Linux
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
                logger.warning(f"Could not load font with size {font_size}, using default font")
        
        # Place images and add labels
        for i, (img_data, img) in enumerate(zip(images, pil_images)):
            row = i // cols
            col = i % cols
            
            # Calculate position
            x = col * (cell_width + spacing)
            y = row * (cell_height + spacing)
            
            # Handle ChemSEM images - resize to fill the entire cell
            if img_data.get("mode") == "chemsem" or "chemsem" in img_data.get("mode", ""):
                # Resize the ChemSEM image to match the cell size exactly without maintaining aspect ratio
                resized_img = img.resize((cell_width, cell_height), Image.LANCZOS)
                
                # Paste directly into the grid at the cell position
                grid_img.paste(resized_img, (x, y))
                
                logger.info(f"Resized ChemSEM image to fill entire cell: {cell_width}x{cell_height}")
            else:
                # Standard image processing - center the image in its cell
                x_offset = (cell_width - img.width) // 2
                y_offset = (cell_height - img.height) // 2
                
                # Paste the image
                grid_img.paste(img, (x + x_offset, y + y_offset))
            
            # Add mode label if enabled
            if options.get("label_mode", True):
                mode_display = img_data.get("display_name", "Unknown")
                
"""
ModeGrid workflow implementation for SEM Image Workflow Manager.
Creates grid visualizations for comparing the same scene with different imaging modes or parameters.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from qtpy import QtWidgets
from utils.logger import Logger
from utils.config import config
from workflows.workflow_base import WorkflowBase

logger = Logger(__name__)


class ModeGridWorkflow(WorkflowBase):
    """
    Implementation of the ModeGrid workflow.
    Creates grid visualizations for comparing the same scene with different imaging modes or parameters.
    """
    
    def __init__(self, session_manager):
        """
        Initialize ModeGrid workflow.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__(session_manager)
        # Get scene matching tolerance from config (default 12%)
        self.scene_match_tolerance = float(config.get('mode_grid.scene_match_tolerance', 0.12))
        # Default order of modes for sorting
        self.preferred_modes_order = config.get('mode_grid.preferred_modes_order', 
                                                ["sed", "bsd", "topo", "edx"])
    
    def name(self):
        """Get the user-friendly name of the workflow."""
        return "ModeGrid"
    
    def description(self):
        """Get the description of the workflow."""
        return "Compare the same scene with different imaging modes or parameters"
    
    def discover_collections(self):
        """
        Discover and create collections based on ModeGrid criteria with enhanced diagnostics.
        
        Returns:
            list: List of collections
        """
        self.collections = []
        
        if not self.session_manager or not self.session_manager.metadata:
            logger.warning("No metadata available for ModeGrid collection discovery")
            return self.collections
        
        # Log basic info about available metadata
        total_images = len(self.session_manager.metadata)
        valid_images = sum(1 for m in self.session_manager.metadata.values() if m.is_valid())
        
        logger.info(f"Starting ModeGrid collection discovery with {valid_images}/{total_images} valid images")
        
        # First, check if manual Collection field exists in metadata
        has_collection_field = False
        collection_groups = {}
        
        # Look for Collection field
        for img_path, metadata in self.session_manager.metadata.items():
            if not metadata.is_valid():
                continue
            
            # Check for Collection field in additional_params
            if hasattr(metadata, 'additional_params') and isinstance(metadata.additional_params, dict):
                if 'Collection' in metadata.additional_params and metadata.additional_params['Collection']:
                    has_collection_field = True
                    collection_id = metadata.additional_params['Collection']
                    
                    if collection_id not in collection_groups:
                        collection_groups[collection_id] = []
                        
                    collection_groups[collection_id].append(img_path)
        
        # Log if Collection field was found
        if has_collection_field:
            logger.info(f"Found {len(collection_groups)} manual collections via Collection field")
        else:
            logger.info("No manual Collection field found in metadata")
        
        # Count all unique modes present in valid images
        all_modes = {}
        for img_path, metadata in self.session_manager.metadata.items():
            if metadata.is_valid():
                mode = self._get_mode_from_metadata(metadata)
                if mode not in all_modes:
                    all_modes[mode] = 0
                all_modes[mode] += 1
        
        # Log the summary of image modes
        logger.info(f"Found the following modes in metadata:")
        for mode, count in all_modes.items():
            logger.info(f"  - {mode}: {count} images")
        
        # If manual collections exist, use them
        manual_collections_created = 0
        
        if has_collection_field and collection_groups:
            for collection_id, images in collection_groups.items():
                # Skip collections with less than 2 images
                if len(images) < 2:
                    logger.info(f"Skipping manual collection {collection_id} - only {len(images)} images")
                    continue
                    
                # Create collection for these images
                collection = self._create_mode_collection_from_paths(collection_id, images)
                if collection and len(collection["images"]) >= 2:
                    # Check if we have different modes (don't create a collection with same mode)
                    modes = {img["mode"] for img in collection["images"]}
                    if len(modes) >= 2:
                        self.collections.append(collection)
                        self.save_collection(collection)
                        logger.info(f"Created ModeGrid collection from manual group: {collection_id} with {len(collection['images'])} images, {len(modes)} modes")
                        manual_collections_created += 1
                    else:
                        logger.info(f"Skipping manual collection {collection_id} - only has {len(modes)} unique modes")
                else:
                    logger.info(f"Failed to create collection from manual group: {collection_id}")
        
        # Log manual collection results
        if has_collection_field:
            logger.info(f"Created {manual_collections_created} collections from manual Collection field")
            
        # Now try position-based grouping with more diagnostic output
        logger.info("Starting position-based collection discovery")
        position_groups = self._group_by_position()
        
        # Count total position-based collections created
        position_collections_created = 0
        
        # For each position group, find images with different modes
        for position_key, images in position_groups.items():
            # Skip if there's only one image at this position
            if len(images) < 2:
                logger.info(f"Skipping position group {position_key} - only {len(images)} images")
                continue
            
            # Count different modes at this position
            modes = {}
            for img_path in images:
                metadata = self.session_manager.metadata[img_path]
                mode = self._get_mode_from_metadata(metadata)
                if mode not in modes:
                    modes[mode] = 0
                modes[mode] += 1
            
            # Log the modes found at this position
            logger.info(f"Position {position_key} has these modes: {', '.join([f'{m}({c})' for m, c in modes.items()])}")
            
            # If we have multiple modes, create a collection
            if len(modes) >= 2:
                collection = self._create_mode_collection(position_key, images)
                if collection and len(collection["images"]) >= 2:
                    self.collections.append(collection)
                    self.save_collection(collection)
                    logger.info(f"Created ModeGrid collection at position {position_key} with {len(collection['images'])} images")
                    position_collections_created += 1
                else:
                    logger.info(f"Failed to create collection at position {position_key}")
            else:
                logger.info(f"Skipping position {position_key} - only has {len(modes)} unique modes")
        
        # Log position-based collection results
        logger.info(f"Created {position_collections_created} collections from position-based grouping")
        
        # Total results
        logger.info(f"Total discovered ModeGrid collections: {len(self.collections)}")
        return self.collections
    
    def _group_by_position(self):
        """
        Group images by sample position with special handling for ChemSEM.
        
        Returns:
            dict: Dictionary mapping position key to list of image paths
        """
        position_groups = {}
        chemsem_matches = {}
        
        # First, gather all valid images and identify ChemSEM files
        valid_images = []
        chemsem_images = {}  # Filename (without _ChemiSEM) -> ChemSEM path
        normal_images = {}   # Filename -> path
        
        for img_path, metadata in self.session_manager.metadata.items():
            if (metadata.is_valid() and 
                metadata.sample_position_x is not None and 
                metadata.sample_position_y is not None and 
                metadata.field_of_view_width is not None and 
                metadata.field_of_view_height is not None):
                
                valid_images.append((img_path, metadata))
                
                # Identify ChemSEM images by filename
                if "ChemiSEM" in metadata.filename:
                    # Extract base name (remove _ChemiSEM from filename)
                    base_name = metadata.filename.replace("_ChemiSEM", "").replace(".tiff", "").replace(".tif", "")
                    chemsem_images[base_name] = img_path
                else:
                    # Normal image
                    base_name = metadata.filename.replace(".tiff", "").replace(".tif", "")
                    normal_images[base_name] = img_path
        
        # Log count of regular and ChemSEM images
        logger.info(f"Found {len(valid_images)} valid images: {len(normal_images)} regular, {len(chemsem_images)} ChemSEM")
        
        # Match ChemSEM images with their corresponding regular images
        for base_name, regular_path in normal_images.items():
            if base_name in chemsem_images:
                chemsem_path = chemsem_images[base_name]
                chemsem_matches[regular_path] = chemsem_path
                logger.info(f"Matched ChemSEM image to regular image: {base_name}")
        
        # Group by EXACT position values (no rounding or formatting)
        exact_position_groups = {}
        for img_path, metadata in valid_images:
            # Skip ChemSEM images for initial grouping (they'll be added to their matching regular image's group)
            if "ChemiSEM" in metadata.filename:
                continue
                
            # Use the exact numerical values as the key
            pos_key = f"{metadata.sample_position_x}_{metadata.sample_position_y}"
            if pos_key not in exact_position_groups:
                exact_position_groups[pos_key] = []
            exact_position_groups[pos_key].append(img_path)
        
        # Now process matched ChemSEM images
        for regular_path, chemsem_path in chemsem_matches.items():
            # Find which position group contains the regular image
            for pos_key, img_paths in exact_position_groups.items():
                if regular_path in img_paths:
                    # Add the ChemSEM image to the same group
                    img_paths.append(chemsem_path)
                    logger.info(f"Added ChemSEM image to position group {pos_key}")
                    break
        
        # Log the number of exact position groups
        logger.info(f"Created {len(exact_position_groups)} position groups for collection discovery")
        
        # Use the exact position groups directly
        position_groups = exact_position_groups
        
        # For each position group, log the number of images and modes found
        for pos_key, img_paths in position_groups.items():
            # Count unique modes in this group
            modes = set()
            for img_path in img_paths:
                metadata = self.session_manager.metadata[img_path]
                mode = self._get_mode_from_metadata(metadata)
                modes.add(mode)
            
            logger.info(f"Position group {pos_key}: {len(img_paths)} images, {len(modes)} unique modes")
        
        return position_groups
    
    def _are_positions_similar(self, metadata1, metadata2):
        """
        Check if two positions are similar within tolerance or exactly the same.
        
        Args:
            metadata1: First metadata object
            metadata2: Second metadata object
            
        Returns:
            bool: True if positions are similar
        """
        # First, do an exact match check - many consecutive images of same area have exact coordinates
        if (metadata1.sample_position_x == metadata2.sample_position_x and 
            metadata1.sample_position_y == metadata2.sample_position_y):
            return True
        
        # If not exact, do the tolerance-based comparison
        # Compare sample positions
        x1, y1 = metadata1.sample_position_x, metadata1.sample_position_y
        x2, y2 = metadata2.sample_position_x, metadata2.sample_position_y
        
        # Use field of view for tolerance calculation
        fov_width = max(metadata1.field_of_view_width, metadata2.field_of_view_width)
        fov_height = max(metadata1.field_of_view_height, metadata2.field_of_view_height)
        
        # If field of view is very small, use a minimum value to avoid division issues
        min_fov = 10  # 10 μm as a minimum FOV size for calculations
        if fov_width < min_fov:
            fov_width = min_fov
        if fov_height < min_fov:
            fov_height = min_fov
        
        # Calculate position difference as a fraction of field of view
        x_diff = abs(x1 - x2) / fov_width if fov_width > 0 else float('inf')
        y_diff = abs(y1 - y2) / fov_height if fov_height > 0 else float('inf')
        
        # Check if difference is within tolerance
        scene_match_tolerance = float(config.get('mode_grid.scene_match_tolerance', 0.2))
        position_match = (x_diff <= scene_match_tolerance and y_diff <= scene_match_tolerance)
        
        # Also check for similar magnification and pixel dimensions
        mag_tolerance = 0.1  # 10% tolerance for magnification
        mag_match = False
        
        if hasattr(metadata1, 'magnification') and hasattr(metadata2, 'magnification'):
            if metadata1.magnification and metadata2.magnification:
                mag_ratio = abs(metadata1.magnification - metadata2.magnification) / max(metadata1.magnification, metadata2.magnification)
                mag_match = mag_ratio <= mag_tolerance
        
        # Check for similar working distance
        wd_tolerance = 0.2  # 20% tolerance for working distance
        wd_match = False
        
        if hasattr(metadata1, 'working_distance_mm') and hasattr(metadata2, 'working_distance_mm'):
            if metadata1.working_distance_mm and metadata2.working_distance_mm:
                wd_ratio = abs(metadata1.working_distance_mm - metadata2.working_distance_mm) / max(metadata1.working_distance_mm, metadata2.working_distance_mm)
                wd_match = wd_ratio <= wd_tolerance
        
        # Special case for Collection field - if both have the same Collection value, that's an automatic match
        collection_match = False
        
        if hasattr(metadata1, 'additional_params') and hasattr(metadata2, 'additional_params'):
            if isinstance(metadata1.additional_params, dict) and isinstance(metadata2.additional_params, dict):
                if 'Collection' in metadata1.additional_params and 'Collection' in metadata2.additional_params:
                    if metadata1.additional_params['Collection'] and metadata2.additional_params['Collection']:
                        collection_match = metadata1.additional_params['Collection'] == metadata2.additional_params['Collection']
        
        # Consider images the same scene if:
        # 1. Positions match within tolerance AND working distance or magnification match
        # 2. OR they have the same Collection value
        return (position_match and (mag_match or wd_match)) or collection_match
    
    def _get_mode_from_metadata(self, metadata):
        """
        Extract the imaging mode from metadata with support for ChemSEM.
        
        Args:
            metadata: Metadata object
            
        Returns:
            str: Mode identifier (sed, bsd, topo-a, topo-b, chemsem, etc.)
                 Now includes high voltage in format: mode_NNkV
        """
        # Check for ChemSEM based on filename
        if hasattr(metadata, 'filename') and "ChemiSEM" in metadata.filename:
            # Include high voltage with ChemSEM if available
            if hasattr(metadata, 'high_voltage_kV') and metadata.high_voltage_kV is not None:
                return f"chemsem_{int(abs(metadata.high_voltage_kV))}kv"
            return "chemsem"
            
        # Basic mode from detector type
        basic_mode = metadata.mode.lower() if metadata.mode else "unknown"
        
        # First check the detector field
        detector_mode = None
        if hasattr(metadata, 'mode'):
            if metadata.mode.lower() == "sed":
                detector_mode = "sed"
            elif metadata.mode.lower() in ["bsd", "bsd-all"]:
                detector_mode = "bsd"
        
        # Next check for mix mode which indicates Topo
        # Topo uses different configurations of BSD segments
        if hasattr(metadata, 'mode') and metadata.mode.lower() == "mix":
            # Need to analyze the detector mix factors to determine topo direction
            # Extract mix factors from additional_params or direct attributes
            bsdA = bsdB = bsdC = bsdD = 0
            
            # Try to get from additional_params first
            if hasattr(metadata, 'additional_params') and 'detectorMixFactors' in metadata.additional_params:
                mix_factors = metadata.additional_params['detectorMixFactors']
                if isinstance(mix_factors, dict):
                    bsdA = float(mix_factors.get('bsdA', 0))
                    bsdB = float(mix_factors.get('bsdB', 0))
                    bsdC = float(mix_factors.get('bsdC', 0))
                    bsdD = float(mix_factors.get('bsdD', 0))
            
            # If not found in additional_params, try direct attributes
            elif hasattr(metadata, 'detectorMixFactors_bsdA'):
                bsdA = float(metadata.detectorMixFactors_bsdA) if metadata.detectorMixFactors_bsdA is not None else 0
                bsdB = float(metadata.detectorMixFactors_bsdB) if metadata.detectorMixFactors_bsdB is not None else 0
                bsdC = float(metadata.detectorMixFactors_bsdC) if metadata.detectorMixFactors_bsdC is not None else 0
                bsdD = float(metadata.detectorMixFactors_bsdD) if metadata.detectorMixFactors_bsdD is not None else 0
            
            # Try to determine topo direction from mix factors
            # This logic is based on the examples provided
            if abs(bsdB) > abs(bsdA) and abs(bsdC) > abs(bsdD):
                # Horizontal direction (approximately 136 degrees)
                detector_mode = "topo-h"
            elif abs(bsdA) > abs(bsdB) and abs(bsdD) > abs(bsdC):
                # Vertical direction (approximately 44 degrees)
                detector_mode = "topo-v"
            else:
                # Generic topo if we can't determine direction
                detector_mode = "topo"
        
        # If we haven't determined a mode yet, fall back to the basic mode
        if detector_mode is None:
            detector_mode = basic_mode
            
        # Incorporate high voltage into the mode identifier
        if hasattr(metadata, 'high_voltage_kV') and metadata.high_voltage_kV is not None:
            return f"{detector_mode}_{int(abs(metadata.high_voltage_kV))}kv"
        
        # Return just the detector mode if we don't have high voltage information
        return detector_mode


    def _get_mode_display_name(self, metadata):
        """
        Get a display name for the mode with parameters.
        
        Args:
            metadata: Metadata object
            
        Returns:
            str: Display name for the mode, including high voltage
        """
        mode = self._get_mode_from_metadata(metadata)
        
        # Extract base mode and high voltage parts
        base_mode = mode
        high_voltage = None
        
        # Check if mode includes high voltage suffix
        if "_" in mode:
            parts = mode.split("_")
            base_mode = parts[0]
            # Extract kV if present
            if len(parts) > 1 and "kv" in parts[1]:
                high_voltage = parts[1]
            
        # First determine the base mode display name
        display_name = ""
        if base_mode == "sed":
            display_name = "SED"
        elif base_mode == "bsd":
            display_name = "BSD"
        elif base_mode == "topo-h":
            display_name = "Topo 136°"
        elif base_mode == "topo-v":
            display_name = "Topo 44°"
        elif base_mode.startswith("topo"):
            display_name = "Topo"
        elif base_mode == "chemsem":
            display_name = "ChemSEM"
        elif base_mode == "edx":
            display_name = "EDX"
        else:
            display_name = base_mode.upper()
        
        # Add high voltage if available
        if high_voltage:
            # Clean up the format - e.g., "15kv" to "15 kV"
            hv_value = high_voltage.replace("kv", "")
            display_name += f" {hv_value} kV"
        
        return display_name
    
    def _create_mode_collection(self, position_key, images):
        """
        Create a ModeGrid collection for a group of images at the same position.
        
        Args:
            position_key: Position group key
            images: List of image paths at this position
            
        Returns:
            dict: ModeGrid collection
        """
        # Group images by mode
        mode_images = {}
        for img_path in images:
            metadata = self.session_manager.metadata[img_path]
            mode = self._get_mode_from_metadata(metadata)
            
            if mode not in mode_images:
                mode_images[mode] = []
            
            mode_images[mode].append((img_path, metadata))
        
        # Select the best image for each mode
        # For now, just take the first one, but in the future could implement quality metrics
        collection_images = []
        
        # Track which parameters vary across the collection
        all_hvs = set()
        all_currents = set()
        all_integrations = set()
        
        for mode, mode_imgs in mode_images.items():
            # Select first image as primary
            img_path, metadata = mode_imgs[0]
            
            # Track parameter values
            if metadata.high_voltage_kV is not None:
                all_hvs.add(metadata.high_voltage_kV)
            
            # Extract emission current if available
            emission_current = None
            if hasattr(metadata, 'additional_params') and 'emission_current_uA' in metadata.additional_params:
                emission_current = metadata.additional_params['emission_current_uA']
            elif hasattr(metadata, 'emission_current_uA'):
                emission_current = metadata.emission_current_uA
            
            if emission_current is not None:
                all_currents.add(emission_current)
            
            # Extract integrations if available
            integrations = None
            if hasattr(metadata, 'additional_params') and 'integrations' in metadata.additional_params:
                integrations = metadata.additional_params['integrations']
            elif hasattr(metadata, 'integrations'):
                integrations = metadata.integrations
            
            if integrations is not None:
                all_integrations.add(integrations)
            
            # Add alternatives (if any)
            alternatives = []
            if len(mode_imgs) > 1:
                alternatives = [alt_img[0] for alt_img in mode_imgs[1:]]
            
            # Add to collection images
            collection_images.append({
                "path": img_path,
                "metadata_dict": metadata.to_dict(),
                "mode": mode,
                "display_name": self._get_mode_display_name(metadata),
                "alternatives": alternatives
            })
        
        # Sort collection images by preferred mode order
        def get_mode_sort_key(img_data):
            mode = img_data["mode"]
            # Return the index in preferred_modes_order or a large number if not found
            for i, preferred_mode in enumerate(self.preferred_modes_order):
                if mode.startswith(preferred_mode):
                    return i
            return 999  # For modes not in the preferred list
        
        collection_images.sort(key=get_mode_sort_key)
        
        # Create collection
        reference_metadata = self.session_manager.metadata[images[0]]
        
        collection = {
            "type": "ModeGrid",
            "id": f"mode_grid_{position_key}",
            "images": collection_images,
            "sample_position_x": reference_metadata.sample_position_x,
            "sample_position_y": reference_metadata.sample_position_y,
            "field_of_view_width": reference_metadata.field_of_view_width,
            "field_of_view_height": reference_metadata.field_of_view_height,
            "varying_parameters": {
                "high_voltage": len(all_hvs) > 1,
                "emission_current": len(all_currents) > 1,
                "integrations": len(all_integrations) > 1
            },
            "description": f"Different modes at position {position_key:.6s}"
        }
        
        return collection
    
    def _create_mode_collection_from_paths(self, collection_id, images):
        """
        Create a ModeGrid collection from a list of image paths.
        
        Args:
            collection_id: Collection identifier
            images: List of image paths
            
        Returns:
            dict: ModeGrid collection
        """
        # Group images by mode
        mode_images = {}
        for img_path in images:
            metadata = self.session_manager.metadata[img_path]
            mode = self._get_mode_from_metadata(metadata)
            
            if mode not in mode_images:
                mode_images[mode] = []
            
            mode_images[mode].append((img_path, metadata))
        
        # Select the best image for each mode
        # For now, just take the first one, but in the future could implement quality metrics
        collection_images = []
        
        # Track which parameters vary across the collection
        all_hvs = set()
        all_currents = set()
        all_integrations = set()
        
        for mode, mode_imgs in mode_images.items():
            # Select first image as primary
            img_path, metadata = mode_imgs[0]
            
            # Track parameter values
            if metadata.high_voltage_kV is not None:
                all_hvs.add(metadata.high_voltage_kV)
            
            # Extract emission current if available
            emission_current = None
            if hasattr(metadata, 'additional_params') and 'emission_current_uA' in metadata.additional_params:
                emission_current = metadata.additional_params['emission_current_uA']
            elif hasattr(metadata, 'emission_current_uA'):
                emission_current = metadata.emission_current_uA
            
            if emission_current is not None:
                all_currents.add(emission_current)
            
            # Extract integrations if available
            integrations = None
            if hasattr(metadata, 'additional_params') and 'integrations' in metadata.additional_params:
                integrations = metadata.additional_params['integrations']
            elif hasattr(metadata, 'integrations'):
                integrations = metadata.integrations
            
            if integrations is not None:
                all_integrations.add(integrations)
            
            # Add alternatives (if any)
            alternatives = []
            if len(mode_imgs) > 1:
                alternatives = [alt_img[0] for alt_img in mode_imgs[1:]]
            
            # Add to collection images
            collection_images.append({
                "path": img_path,
                "metadata_dict": metadata.to_dict(),
                "mode": mode,
                "display_name": self._get_mode_display_name(metadata),
                "alternatives": alternatives
            })
        
        # Sort collection images by preferred mode order
        def get_mode_sort_key(img_data):
            mode = img_data["mode"]
            # Return the index in preferred_modes_order or a large number if not found
            for i, preferred_mode in enumerate(self.preferred_modes_order):
                if mode.startswith(preferred_mode):
                    return i
            return 999  # For modes not in the preferred list
        
        collection_images.sort(key=get_mode_sort_key)
        
        # Use the first image for reference data
        reference_metadata = self.session_manager.metadata[images[0]]
        
        collection = {
            "type": "ModeGrid",
            "id": f"mode_grid_{collection_id}",
            "images": collection_images,
            "sample_position_x": reference_metadata.sample_position_x,
            "sample_position_y": reference_metadata.sample_position_y,
            "field_of_view_width": reference_metadata.field_of_view_width,
            "field_of_view_height": reference_metadata.field_of_view_height,
            "varying_parameters": {
                "high_voltage": len(all_hvs) > 1,
                "emission_current": len(all_currents) > 1,
                "integrations": len(all_integrations) > 1
            },
            "description": f"Different modes in collection {collection_id}"
        }
        
        return collection
    
    def create_grid(self, collection, layout=None, options=None):
        """
        Create a grid visualization for the ModeGrid collection with support for ChemSEM.
        
        Args:
            collection: ModeGrid collection to visualize
            layout (tuple, optional): Grid layout as (rows, columns)
            options (dict, optional): Annotation options
            
        Returns:
            PIL.Image: Grid visualization image
        """
        # Add detailed logging to diagnose issues
        if not collection:
            logger.error("Invalid collection for ModeGrid visualization: collection is None")
            return None
            
        if "images" not in collection:
            logger.error("Invalid collection for ModeGrid visualization: 'images' field missing")
            logger.debug(f"Collection keys: {list(collection.keys())}")
            return None
            
        if len(collection["images"]) < 2:
            logger.error(f"Invalid collection for ModeGrid visualization: not enough images ({len(collection['images'])})")
            return None
        
        # Log the collection structure for debugging
        logger.debug(f"Creating grid for collection: {collection['id']}")
        logger.debug(f"Collection contains {len(collection['images'])} images")
        
        # Default options if none provided
        if options is None:
            options = {
                "label_mode": config.get('mode_grid.label_mode', True),
                "label_voltage": config.get('mode_grid.label_voltage', True),
                "label_current": config.get('mode_grid.label_current', True),
                "label_integrations": config.get('mode_grid.label_integrations', True),
                "label_font_size": config.get('mode_grid.label_font_size', 12)
            }
        
        # Determine layout based on number of images if not specified
        images = collection["images"]
        num_images = len(images)
        
        if not layout:
            if num_images == 2:
                layout = (1, 2)  # 1 row, 2 columns
            elif num_images <= 4:
                layout = (2, 2)  # 2 rows, 2 columns
            elif num_images <= 6:
                layout = (2, 3)  # 2 rows, 3 columns
            else:
                layout = (3, 3)  # 3 rows, 3 columns
        
        rows, cols = layout
        logger.info(f"Creating ModeGrid with layout {rows}x{cols} for {num_images} images")
        
        # Load all images
        pil_images = []
        for img_data in images:
            try:
                img_path = img_data["path"]
                logger.debug(f"Loading image: {img_path}")
                if not os.path.exists(img_path):
                    logger.error(f"Image file does not exist: {img_path}")
                    continue
                    
                img = Image.open(img_path)
                pil_images.append(img)
            except Exception as e:
                logger.error(f"Error loading image {img_path}: {str(e)}")
                return None
        
        # Check if we successfully loaded any images
        if len(pil_images) < 2:
            logger.error(f"Not enough images could be loaded: {len(pil_images)}")
            return None
        
        # Determine if we have any ChemSEM images
        has_chemsem = False
        for img_data in images:
            if img_data.get("mode") == "chemsem":
                has_chemsem = True
                break
        
        # Determine the size of grid cells - handle ChemSEM differently
        if has_chemsem:
            # Filter out ChemSEM images for size calculation (only use regular images)
            regular_images = [img for i, img in enumerate(pil_images) 
                            if i < len(images) and images[i].get("mode") != "chemsem"]
            
            # If we have regular images, use their size as reference
            if regular_images:
                cell_width = max(img.width for img in regular_images)
                cell_height = max(img.height for img in regular_images)
            else:
                # Fallback if somehow all images are ChemSEM
                cell_width = max(img.width for img in pil_images)
                cell_height = max(img.height for img in pil_images)
        else:
            # Standard case - use max dimensions
            cell_width = max(img.width for img in pil_images)
            cell_height = max(img.height for img in pil_images)
        
        # Create a blank grid image with spacing
        spacing = 10
        grid_width = cols * cell_width + (cols - 1) * spacing
        grid_height = rows * cell_height + (rows - 1) * spacing
        grid_img = Image.new('RGB', (grid_width, grid_height), color='white')
        
        # Place images in the grid
        draw = ImageDraw.Draw(grid_img)
        
        # Try to load a font with the configured size
        font_size = options.get("label_font_size", 12)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            try:
                # Try system font locations
                import sys
                if sys.platform == "win32":
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
                elif sys.platform == "darwin":  # macOS
                    font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size)
                else:  # Linux
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
                logger.warning(f"Could not load font with size {font_size}, using default font")
        
        # Place images and add labels
        for i, (img_data, img) in enumerate(zip(images, pil_images)):
            row = i // cols
            col = i % cols
            
            # Calculate position
            x = col * (cell_width + spacing)
            y = row * (cell_height + spacing)
            
            # Handle ChemSEM images - resize to fill the entire cell
            if img_data.get("mode") == "chemsem" or "chemsem" in img_data.get("mode", ""):
                # Resize the ChemSEM image to match the cell size exactly without maintaining aspect ratio
                resized_img = img.resize((cell_width, cell_height), Image.LANCZOS)
                
                # Paste directly into the grid at the cell position
                grid_img.paste(resized_img, (x, y))
                
                logger.info(f"Resized ChemSEM image to fill entire cell: {cell_width}x{cell_height}")
            else:
                # Standard image processing - center the image in its cell
                x_offset = (cell_width - img.width) // 2
                y_offset = (cell_height - img.height) // 2
                
                # Paste the image
                grid_img.paste(img, (x + x_offset, y + y_offset))
            
            # Add mode label if enabled
            if options.get("label_mode", True):
                mode_display = img_data.get("display_name", "Unknown")
                
                # No need to add voltage as it's already in the display_name
                # Just add other parameters if they vary and options are enabled
                metadata_dict = img_data.get("metadata_dict", {})
                varying_parameters = collection.get("varying_parameters", {})
                
                # Add emission current if it varies and option enabled
                if varying_parameters.get("emission_current", False) and options.get("label_current", True):
                    emission_current = metadata_dict.get("emission_current_uA")
                    if emission_current is not None:
                        mode_display += f" {emission_current}μA"
                
                # Add integrations if they vary and option enabled
                if varying_parameters.get("integrations", False) and options.get("label_integrations", True):
                    integrations = metadata_dict.get("integrations")
                    if integrations is not None:
                        mode_display += f" {integrations}int"
                
                # Draw the mode label
                label_x = x + cell_width // 2
                label_y = y + 10  # Position at top
                
                # Draw label with shadow for better visibility
                text_width, text_height = draw.textsize(mode_display, font=font) if hasattr(draw, 'textsize') else (
                    draw.textlength(mode_display, font=font), font_size * 1.5)
                
                text_x = label_x - text_width // 2
                
                # Draw light background for text
                draw.rectangle(
                    [text_x - 5, label_y - 3, text_x + text_width + 5, label_y + text_height + 3],
                    fill=(255, 255, 255, 180)
                )
                
                # Draw text
                draw.text(
                    (text_x, label_y),
                    mode_display,
                    fill=(0, 0, 0),
                    font=font
                )
                
                # Add indicator if image has alternatives
                if img_data.get("alternatives"):
                    alt_indicator = "▼"  # Down triangle indicator for alternatives
                    alt_x = text_x + text_width + 8
                    
                    draw.text(
                        (alt_x, label_y),
                        alt_indicator,
                        fill=(0, 120, 215),  # Blue color
                        font=font
                    )
        
        logger.info(f"Created ModeGrid visualization with {num_images} images")
        return grid_img
    
    def switch_image_alternative(self, collection, image_index, alternative_path):
        """
        Switch to an alternative image in the collection.
        
        Args:
            collection: ModeGrid collection
            image_index: Index of the image to replace
            alternative_path: Path to the alternative image
            
        Returns:
            dict: Updated collection
        """
        if not collection or "images" not in collection:
            return collection
        
        if image_index < 0 or image_index >= len(collection["images"]):
            logger.error(f"Invalid image index: {image_index}")
            return collection
        
        try:
            # Get the current image data
            current_image = collection["images"][image_index]
            
            # Check if alternative is in the alternatives list
            if alternative_path not in current_image.get("alternatives", []):
                logger.warning(f"Alternative path not found in alternatives list: {alternative_path}")
                return collection
            
            # Get metadata for the alternative image
            alt_metadata = self.session_manager.metadata.get(alternative_path)
            
            if not alt_metadata:
                logger.error(f"Failed to get metadata for alternative image: {alternative_path}")
                return collection
            
            # Update alternatives list
            alternatives = current_image.get("alternatives", [])
            alternatives.append(current_image["path"])
            alternatives.remove(alternative_path)
            
            # Update current image
            current_image["path"] = alternative_path
            current_image["metadata_dict"] = alt_metadata.to_dict()
            current_image["alternatives"] = alternatives
            
            # Update collection
            collection["images"][image_index] = current_image
            
            # Save collection
            self.save_collection(collection)
            
            logger.info(f"Switched to alternative image: {alternative_path}")
            return collection
            
        except Exception as e:
            logger.error(f"Error switching alternative image: {str(e)}")
            return collection
    
    def _generate_caption(self, collection):
        """
        Generate a caption for the ModeGrid visualization.
        
        Args:
            collection: ModeGrid collection data
            
        Returns:
            str: Caption text
        """
        sample_id = "Unknown"
        if self.session_manager and self.session_manager.current_session:
            sample_id = self.session_manager.current_session.sample_id
        
        # Get field of view info
        fov_width = collection.get("field_of_view_width", 0)
        fov_height = collection.get("field_of_view_height", 0)
        
        # Get mode information
        modes = []
        for img in collection.get("images", []):
            mode_display = img.get("display_name", "Unknown")
            modes.append(mode_display)
        
        mode_str = ", ".join(modes)
        
        caption = f"Sample {sample_id} comparison of imaging modes.\n"
        caption += f"Field of view: {fov_width:.1f} x {fov_height:.1f} μm.\n"
        caption += f"Modes shown: {mode_str}."
        
        return caption
