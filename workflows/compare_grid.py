"""
CompareGrid workflow implementation for SEM Image Workflow Manager.
Creates grid visualizations for comparing samples across different sessions.
"""

import os
import json
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from qtpy import QtWidgets
from utils.logger import Logger
from workflows.workflow_base import WorkflowBase, convert_to_serializable

logger = Logger(__name__)


class CompareGridWorkflow(WorkflowBase):
    """
    Implementation of the CompareGrid workflow.
    Creates grid visualizations for comparing samples across different sessions.
    """
    
    def __init__(self, session_manager):
        """
        Initialize CompareGrid workflow.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__(session_manager)
        self.sessions = {}  # Dictionary of session_folder -> session_info
        self.all_metadata = {}  # Dictionary of image_path -> metadata
        self.consolidated_metadata = None  # DataFrame with all metadata
        self.main_session_folder = None
        
        # Store the main session if available
        if session_manager and session_manager.session_folder:
            self.main_session_folder = session_manager.session_folder
            if session_manager.current_session:
                self.sessions[session_manager.session_folder] = session_manager.current_session
                self.all_metadata.update(session_manager.metadata)
                
        # Call _setup_workflow_folder explicitly to ensure it has the correct path
        self._setup_workflow_folder()
    
    def _setup_workflow_folder(self):
        """
        Override the workflow folder setup to handle the multi-session nature of CompareGrid.
        """
        if not self.session_manager or not self.session_manager.session_folder:
            return
        
        # Use the main session folder for the workflow folder
        workflow_name = self.__class__.__name__
        self.workflow_folder = os.path.join(
            self.session_manager.session_folder,
            workflow_name
        )
        
        if not os.path.exists(self.workflow_folder):
            try:
                os.makedirs(self.workflow_folder)
                logger.info(f"Created CompareGrid workflow folder: {self.workflow_folder}")
            except Exception as e:
                logger.error(f"Failed to create workflow folder: {str(e)}")
    
    def name(self):
        """Get the user-friendly name of the workflow."""
        return "CompareGrid"
    
    def description(self):
        """Get the description of the workflow."""
        return "Create grid visualizations for comparing samples across different sessions"
    
    def add_session(self, session_folder):
        """
        Add a session to the comparison.
        
        Args:
            session_folder: Path to the session folder
            
        Returns:
            bool: True if successful, False otherwise
        """
        if session_folder in self.sessions:
            logger.info(f"Session already added: {session_folder}")
            return True
        
        try:
            # Create a temporary session manager to load the session
            from models.session import SessionManager
            temp_manager = SessionManager()
            
            if temp_manager.open_session(session_folder):
                # Store session info
                self.sessions[session_folder] = temp_manager.current_session
                
                # Copy metadata
                self.all_metadata.update(temp_manager.metadata)
                
                # Reset consolidated metadata so it will be rebuilt
                self.consolidated_metadata = None
                
                logger.info(f"Added session: {session_folder}")
                return True
            else:
                logger.error(f"Failed to open session: {session_folder}")
                return False
        except Exception as e:
            logger.error(f"Error adding session: {str(e)}")
            return False
    
    def remove_session(self, session_folder):
        """
        Remove a session from the comparison.
        
        Args:
            session_folder: Path to the session folder
            
        Returns:
            bool: True if successful, False otherwise
        """
        if session_folder not in self.sessions:
            logger.warning(f"Session not found: {session_folder}")
            return False
        
        try:
            # Remove session info
            self.sessions.pop(session_folder)
            
            # Remove metadata for images in this session
            to_remove = []
            for img_path in self.all_metadata:
                if img_path.startswith(session_folder):
                    to_remove.append(img_path)
            
            for img_path in to_remove:
                self.all_metadata.pop(img_path)
            
            # Reset consolidated metadata so it will be rebuilt
            self.consolidated_metadata = None
            
            logger.info(f"Removed session: {session_folder}")
            return True
        except Exception as e:
            logger.error(f"Error removing session: {str(e)}")
            return False
    
    def get_session_info(self, session_folder):
        """
        Get session info for a session.
        
        Args:
            session_folder: Path to the session folder
            
        Returns:
            SessionInfo: Session info object or None
        """
        return self.sessions.get(session_folder)
    
    def get_sessions(self):
        """
        Get all sessions.
        
        Returns:
            dict: Dictionary of session_folder -> session_info
        """
        return self.sessions
    
    def _consolidate_metadata(self):
        """
        Consolidate metadata from all sessions into a single DataFrame.
        
        Returns:
            pandas.DataFrame: Consolidated metadata
        """
        if self.consolidated_metadata is not None:
            return self.consolidated_metadata
        
        # Convert metadata to DataFrames
        session_dfs = []
        
        for session_folder, session_info in self.sessions.items():
            # Try to load from CSV first (more efficient)
            session_id = os.path.basename(session_folder)
            csv_path = os.path.join(session_folder, f"{session_id}_metadata.csv")
            
            if not os.path.exists(csv_path):
                # Try legacy path
                csv_path = os.path.join(session_folder, "metadata.csv")
            
            if os.path.exists(csv_path):
                try:
                    # Load the CSV
                    df = pd.read_csv(csv_path)
                    
                    # Add session_id if not present
                    if 'session_id' not in df.columns:
                        df['session_id'] = session_id
                    
                    # Add session_folder
                    df['session_folder'] = session_folder
                    
                    # Add sample_id and sample_name if available
                    if session_info:
                        if not 'sample_id' in df.columns:
                            df['sample_id'] = session_info.sample_id
                        if hasattr(session_info, 'sample_name') and not 'sample_name' in df.columns:
                            df['sample_name'] = session_info.sample_name
                    
                    session_dfs.append(df)
                    logger.info(f"Loaded metadata from CSV for session: {session_id}")
                    continue
                except Exception as e:
                    logger.warning(f"Error loading CSV for session {session_id}: {str(e)}")
                    # Fall back to metadata from memory
            
            # If CSV loading failed, use metadata from memory
            session_metadata = [m for p, m in self.all_metadata.items() if p.startswith(session_folder)]
            
            if session_metadata:
                # Convert to dicts
                metadata_dicts = [m.to_dict() for m in session_metadata]
                
                # Create DataFrame
                df = pd.DataFrame(metadata_dicts)
                
                # Add session_id
                df['session_id'] = session_id
                
                # Add session_folder
                df['session_folder'] = session_folder
                
                # Add sample_id and sample_name if available
                if session_info:
                    if not 'sample_id' in df.columns:
                        df['sample_id'] = session_info.sample_id
                    if hasattr(session_info, 'sample_name') and not 'sample_name' in df.columns:
                        df['sample_name'] = session_info.sample_name
                
                session_dfs.append(df)
                logger.info(f"Created metadata DataFrame for session: {session_id}")
        
        if not session_dfs:
            logger.warning("No metadata available for consolidation")
            return pd.DataFrame()
        
        # Combine all DataFrames
        try:
            self.consolidated_metadata = pd.concat(session_dfs, ignore_index=True)
            logger.info(f"Consolidated metadata with {len(self.consolidated_metadata)} entries")
            return self.consolidated_metadata
        except Exception as e:
            logger.error(f"Error consolidating metadata: {str(e)}")
            return pd.DataFrame()
    
    def discover_collections(self):
        """
        Discover and create collections based on CompareGrid criteria.
        
        Returns:
            list: List of collections
        """
        self.collections = []
        
        # Verify we have at least two sessions
        if len(self.sessions) < 2:
            QtWidgets.QMessageBox.warning(
                None,
                "Insufficient Sessions",
                "At least two sessions are required for comparison. Please add more sessions."
            )
            return self.collections
        
        # Check if each session has metadata
        sessions_without_metadata = []
        for session_folder, session_info in self.sessions.items():
            # Check if metadata exists
            session_id = os.path.basename(session_folder)
            metadata_file = os.path.join(session_folder, f"{session_id}_metadata.csv")
            
            # Also check legacy name
            legacy_metadata_file = os.path.join(session_folder, "metadata.csv")
            
            if not os.path.exists(metadata_file) and not os.path.exists(legacy_metadata_file):
                sessions_without_metadata.append(session_id)
        
        # Alert if metadata is missing
        if sessions_without_metadata:
            missing_sessions = "\n".join(sessions_without_metadata)
            response = QtWidgets.QMessageBox.question(
                None,
                "Missing Metadata",
                f"The following sessions are missing metadata:\n{missing_sessions}\n\n"
                "Would you like to extract metadata for these sessions now?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            
            if response == QtWidgets.QMessageBox.Yes:
                # Extract metadata for each session
                for session_folder in sessions_without_metadata:
                    # TODO: Implement extracting metadata for these sessions
                    # For now, just show a message
                    QtWidgets.QMessageBox.information(
                        None,
                        "Metadata Extraction",
                        f"Please open session {session_folder} in the Standard tab and use "
                        "Tools → Extract Metadata to process this session."
                    )
                return self.collections
        
        logger.info("Starting CompareGrid collection discovery")
        
        # Consolidate metadata from all sessions
        df = self._consolidate_metadata()
        
        if df.empty:
            QtWidgets.QMessageBox.warning(
                None,
                "No Metadata",
                "No metadata available for collection discovery."
            )
            return self.collections
        
        # Group by mode and high voltage (exact match)
        mode_voltage_groups = []
        
        # Get unique mode/voltage combinations
        mode_voltage_combinations = df.groupby(['mode', 'high_voltage_kV']).size().reset_index().rename(columns={0: 'count'})
        
        # For each combination, check if it exists in multiple sessions
        for _, row in mode_voltage_combinations.iterrows():
            mode = row['mode']
            voltage = row['high_voltage_kV']
            
            # Filter by this mode and voltage
            filtered_df = df[(df['mode'] == mode) & (df['high_voltage_kV'] == voltage)]
            
            # Check if this appears in at least 2 sessions
            session_count = filtered_df['session_id'].nunique()
            if session_count >= 2:
                mode_voltage_groups.append({
                    'mode': mode,
                    'voltage': voltage,
                    'data': filtered_df
                })
        
        # Process each mode/voltage group
        for group in mode_voltage_groups:
            mode = group['mode']
            voltage = group['voltage']
            filtered_df = group['data']
            
            # Get all magnifications
            magnifications = filtered_df['magnification'].dropna().unique().tolist()
            magnifications.sort()
            
            # Group magnifications with 12% tolerance
            mag_groups = []
            for mag in magnifications:
                # Check if this mag fits in an existing group
                found_group = False
                for group in mag_groups:
                    # Check if within 12% of the first mag in group
                    base_mag = group[0]
                    if abs(mag - base_mag) / base_mag <= 0.12:  # 12% tolerance
                        group.append(mag)
                        found_group = True
                        break
                
                # If not found a group, create a new one
                if not found_group:
                    mag_groups.append([mag])
            
            # Create collections for each magnification group
            for mag_group in mag_groups:
                # Use the median magnification as the representative
                if len(mag_group) % 2 == 0:  # even number
                    representative_mag = (mag_group[len(mag_group)//2-1] + mag_group[len(mag_group)//2]) / 2
                else:  # odd number
                    representative_mag = mag_group[len(mag_group)//2]
                
                # Find images within tolerance of the representative magnification
                mag_min = representative_mag * 0.88  # -12%
                mag_max = representative_mag * 1.12  # +12%
                
                mag_df = filtered_df[(filtered_df['magnification'] >= mag_min) & 
                                     (filtered_df['magnification'] <= mag_max)]
                
                # Group by session
                session_groups = mag_df.groupby('session_id')
                
                # Check if we have images from at least 2 sessions
                if len(session_groups) < 2:
                    continue
                
                # Find best matching image for each session
                collection_images = []
                
                for session_id, group_df in session_groups:
                    # Get session folder
                    session_folder = group_df['session_folder'].iloc[0]
                    
                    # Get sample info
                    sample_id = group_df['sample_id'].iloc[0] if 'sample_id' in group_df else "Unknown"
                    sample_name = group_df['sample_name'].iloc[0] if 'sample_name' in group_df else ""
                    
                    # Sort by how close the magnification is to the representative
                    group_df['mag_diff'] = abs(group_df['magnification'] - representative_mag)
                    group_df = group_df.sort_values('mag_diff')
                    
                    # Get the best matching image
                    best_image = group_df.iloc[0]
                    
                    # Extract alternative images (up to 4)
                    alternatives = []
                    for _, alt_row in group_df.iloc[1:5].iterrows():
                        if 'image_path' in alt_row and pd.notna(alt_row['image_path']):
                            alternatives.append(alt_row['image_path'])
                    
                    # Add to collection images
                    metadata_dict = {col: best_image[col] for col in best_image.index 
                                    if col not in ['session_id', 'session_folder', 'mag_diff']}
                    
                    collection_images.append({
                        "path": best_image['image_path'],
                        "metadata_dict": metadata_dict,
                        "session_folder": session_folder,
                        "sample_id": sample_id,
                        "sample_name": sample_name,
                        "alternatives": alternatives
                    })
                
                # Create collection
                collection = {
                    "type": "CompareGrid",
                    "id": f"compare_{mode}_{int(representative_mag)}_{voltage}",
                    "images": collection_images,
                    "mode": mode,
                    "high_voltage": voltage,
                    "magnification": int(representative_mag),
                    "description": f"{mode} mode at {int(representative_mag)}x, {voltage} kV"
                }
                
                # Ensure collection has complete metadata
                self._ensure_full_metadata(collection)
                
                self.collections.append(collection)
                self.save_collection(collection)
                
                logger.info(f"Found CompareGrid collection with {len(collection_images)} samples: {collection['description']}")
        
        if not self.collections:
            QtWidgets.QMessageBox.information(
                None,
                "No Collections Found",
                "No comparable collections were found across the selected sessions.\n\n"
                "Comparable collections require images with:\n"
                "- Same detector mode\n"
                "- Same high voltage\n"
                "- Similar magnification (within 12%)\n\n"
                "Make sure metadata has been extracted for all sessions."
            )
        
        logger.info(f"Discovered {len(self.collections)} CompareGrid collections")
        return self.collections
    
    def create_grid(self, collection, layout=None, options=None):
        """
        Create a grid visualization for the CompareGrid collection.
        
        Args:
            collection: CompareGrid collection to visualize
            layout (tuple, optional): Grid layout as (rows, columns)
            options (dict, optional): Annotation options
            
        Returns:
            PIL.Image: Grid visualization image
        """
        if not collection or "images" not in collection or len(collection["images"]) < 2:
            logger.error("Invalid collection for CompareGrid visualization")
            return None
        
        # Default options if none provided
        if options is None:
            options = {
                "label_style": "both"  # Default to showing both sample ID and name
            }
        
        # Determine layout based on number of images if not specified
        images_data = collection["images"]
        num_images = len(images_data)
        
        if not layout:
            # For comparison grids, we typically want a single row for easy comparison
            if num_images <= 4:
                layout = (1, num_images)  # 1 row, n columns
            else:
                # For more images, use 2 rows
                layout = (2, (num_images + 1) // 2)  # 2 rows, ceil(n/2) columns
        
        rows, cols = layout
        logger.info(f"Creating CompareGrid with layout {rows}x{cols} for {num_images} samples")
        
        # Load all images with improved error handling
        pil_images = []
        missing_images = []
        
        for img_data in images_data:
            try:
                img_path = img_data.get("path", "")
                
                if not img_path:
                    logger.error("Image path is missing in collection data")
                    missing_images.append("Unknown path")
                    continue
                
                # Verify the file exists
                if not os.path.exists(img_path):
                    logger.error(f"Image file does not exist: {img_path}")
                    missing_images.append(os.path.basename(img_path))
                    continue
                
                # Try to open the image
                img = Image.open(img_path)
                pil_images.append(img)
                logger.info(f"Successfully loaded image: {img_path}")
            except Exception as e:
                logger.error(f"Error loading image {img_data.get('path', 'Unknown')}: {str(e)}")
                if 'path' in img_data:
                    missing_images.append(os.path.basename(img_data["path"]))
                else:
                    missing_images.append("Unknown path")
        
        # If no images could be loaded, show detailed error and return
        if not pil_images:
            error_msg = "Failed to load any images. Please check that all image files exist."
            if missing_images:
                error_msg += f"\nMissing images: {', '.join(missing_images)}"
            logger.error(error_msg)
            QtWidgets.QMessageBox.critical(None, "Image Loading Error", error_msg)
            return None
            
        # If some images are missing, warn but continue with available ones
        if missing_images and len(pil_images) < len(images_data):
            warn_msg = f"Some images could not be loaded ({len(missing_images)} missing).\nThe grid will be created with available images only."
            logger.warning(warn_msg)
            QtWidgets.QMessageBox.warning(None, "Partial Image Loading", warn_msg)
        
        # Determine the size of grid cells (use the max width and height)
        cell_width = max(img.width for img in pil_images)
        cell_height = max(img.height for img in pil_images)
        
        # Create a blank grid image with spacing
        spacing = 30  # Increased spacing between images to accommodate larger labels
        
        # Additional space for labels at the top of each image
        label_height = 30  # Increased label height for larger text
        
        grid_width = cols * cell_width + (cols - 1) * spacing
        grid_height = rows * (cell_height + label_height) + (rows - 1) * spacing
        grid_img = Image.new('RGB', (grid_width, grid_height), color='white')
        
        # Place images in the grid
        draw = ImageDraw.Draw(grid_img)
        
        try:
            # Get custom font size from options or use default
            base_font_size = options.get("font_size", 16)
            # Scale based on grid width (approximate for 6.5 inch document)
            target_doc_width_inches = 6.5
            pixels_per_inch = 300  # Typical print resolution
            target_width_pixels = target_doc_width_inches * pixels_per_inch
            font_scale = grid_width / target_width_pixels
            adjusted_font_size = max(int(base_font_size / font_scale), 8)  # Allow smaller minimum size
            logger.info(f"Using user-specified font size: {base_font_size}, adjusted to: {adjusted_font_size}")
            
            # Try to load the font
            try:
                font = ImageFont.truetype("arial.ttf", adjusted_font_size)
            except IOError:
                try:
                    # Try system font locations
                    import sys
                    if sys.platform == "win32":
                        font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", adjusted_font_size)
                    elif sys.platform == "darwin":  # macOS
                        font = ImageFont.truetype("/Library/Fonts/Arial.ttf", adjusted_font_size)
                    else:  # Linux
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", adjusted_font_size)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                    logger.warning(f"Could not load Arial font, using default font")
        except Exception as e:
            # Fallback to default font if any error
            font = ImageFont.load_default()
            logger.warning(f"Error setting up font: {str(e)}")
        
        logger.info(f"Using font size: {adjusted_font_size}")
        
        # Place images and add labels
        for i, (img_data, img) in enumerate(zip(images_data, pil_images)):
            row = i // cols
            col = i % cols
            
            # Calculate position (including space for label)
            x = col * (cell_width + spacing)
            y = row * (cell_height + label_height + spacing) + label_height
            
            # Center the image in its cell
            x_offset = (cell_width - img.width) // 2
            y_offset = (cell_height - img.height) // 2
            
            # Paste the image
            grid_img.paste(img, (x + x_offset, y + y_offset))
            
            # Add sample ID/name label
            sample_id = img_data.get("sample_id", "Unknown")
            sample_name = img_data.get("sample_name", "")
            
            label_text = ""
            if options["label_style"] == "id" or options["label_style"] == "both":
                label_text = sample_id
            
            if options["label_style"] == "name" and sample_name:
                label_text = sample_name
            elif options["label_style"] == "both" and sample_name:
                label_text = f"{sample_id}: {sample_name}"
            
            # Center the label both horizontally and vertically in the white space above the image
            label_x = x + (cell_width // 2)
            
            # Calculate text dimensions to center vertically
            text_width = draw.textlength(label_text, font=font)
            
            # Use textbbox to get text dimensions (compatible with newer Pillow)
            text_bbox = draw.textbbox((0, 0), label_text, font=font)
            text_height = text_bbox[3] - text_bbox[1]
            
            # Position in the middle of the label area
            label_y = y - label_height + ((label_height - text_height) // 2)
            
            # Draw the label text with center alignment
            draw.text(
                (label_x - (text_width // 2), label_y),
                label_text,
                fill=(0, 0, 0),
                font=font
            )
            
            # Add magnification label at the bottom left corner of each image
            mag = img_data["metadata_dict"]["magnification"]
            mag_label = f"{mag}x"
            
            # Draw magnification with improved visibility
            mag_x = x + x_offset + 10
            mag_y = y + y_offset + img.height - 25  # Increased spacing
            
            # Draw shadow/outline for better visibility
            for offset in [(1,1), (-1,-1), (1,-1), (-1,1)]:
                draw.text(
                    (mag_x + offset[0], mag_y + offset[1]),
                    mag_label,
                    fill=(0, 0, 0),
                    font=font
                )
            
            # Draw the main text
            draw.text(
                (mag_x, mag_y),
                mag_label,
                fill=(255, 255, 255),
                font=font
            )
            
            # If this image has alternatives, add a small indicator
            if img_data.get("alternatives"):
                alt_indicator = "▼"  # Down triangle indicator for alternatives
                draw.text(
                    (x + cell_width - 25, y - label_height + 5),
                    alt_indicator,
                    fill=(0, 120, 215),  # Blue color
                    font=font
                )
        
        logger.info(f"Created CompareGrid visualization with {num_images} samples")
        return grid_img
    
    def _ensure_full_metadata(self, collection):
        """
        Make sure all images in the collection have complete metadata stored.
        This helps make the collection independent from session data.
        Also normalizes paths to ensure consistent handling across sessions.
        
        Args:
            collection: Collection to enhance with metadata
        """
        if not collection or "images" not in collection:
            return
            
        # Find common parent directory for all sessions
        session_folders = set()
        for img_data in collection["images"]:
            if "session_folder" in img_data:
                session_folders.add(img_data["session_folder"])
        
        # Find the common parent if there are multiple session folders
        common_parent = None
        if len(session_folders) > 1:
            # Convert to list and sort for consistent processing
            folders = sorted(list(session_folders))
            
            # Try to find common parent by comparing path components
            parts_list = [os.path.normpath(folder).split(os.sep) for folder in folders]
            min_parts = min(len(parts) for parts in parts_list)
            
            # Find common prefix parts
            common_parts = []
            for i in range(min_parts):
                if all(parts[i] == parts_list[0][i] for parts in parts_list):
                    common_parts.append(parts_list[0][i])
                else:
                    break
            
            # If we found common parts, join them to form the common parent path
            if common_parts:
                common_parent = os.sep.join(common_parts)
                if common_parent.endswith(os.sep):
                    common_parent = common_parent[:-1]
                logger.info(f"Found common parent directory: {common_parent}")
        
        # Check each image entry
        for img_data in collection["images"]:
            # Make sure all necessary fields are present
            if "path" not in img_data:
                logger.warning("Image entry missing path field")
                continue
                
            # Extract and normalize path
            img_path = img_data["path"]
            session_folder = img_data.get("session_folder", "")
            filename = os.path.basename(img_path)
            
            # Ensure the path is absolute
            if not os.path.isabs(img_path) and session_folder:
                # Reconstruct absolute path
                img_path = os.path.join(session_folder, img_path)
                img_data["path"] = img_path
            
            # Check if file exists and try to fix if not
            if not os.path.exists(img_path):
                # Try to locate the file in the session folder
                if session_folder and os.path.exists(session_folder):
                    potential_path = os.path.join(session_folder, filename)
                    if os.path.exists(potential_path):
                        logger.info(f"Fixed path for {filename}: {potential_path}")
                        img_path = potential_path
                        img_data["path"] = img_path
                
                # If common parent is found, try to reconstruct path relative to it
                if common_parent and not os.path.exists(img_path):
                    # Get session name from session folder path
                    session_name = os.path.basename(session_folder)
                    
                    # Try to reconstruct path based on common parent and session name
                    potential_path = os.path.join(common_parent, session_name, filename)
                    if os.path.exists(potential_path):
                        logger.info(f"Fixed path for {filename} using common parent: {potential_path}")
                        img_path = potential_path
                        img_data["path"] = img_path
                        
                        # Update session folder to be consistent
                        new_session_folder = os.path.join(common_parent, session_name)
                        img_data["session_folder"] = new_session_folder
            
            # Store the file existence status and path information
            img_data["file_exists"] = os.path.exists(img_path)
            img_data["filename"] = filename
            img_data["parent_dir"] = os.path.dirname(img_path)
            
            # Store path information for debugging
            img_data["normalized_path"] = os.path.normpath(img_path)
    
    def switch_image_alternative(self, collection, image_index, alternative_path):
        """
        Switch to an alternative image in the collection.
        
        Args:
            collection: CompareGrid collection
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
            
            # Swap the current image with the alternative
            from models.metadata_extractor import MetadataExtractor
            extractor = MetadataExtractor()
            
            # Extract metadata for the alternative image
            alt_metadata = extractor.extract_metadata(alternative_path)
            
            if not alt_metadata:
                logger.error(f"Failed to extract metadata for alternative image: {alternative_path}")
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
    

    def export_grid(self, grid_image, collection):
        """
        Override to export grid visualization to CompareGrids folder in the parent directory.
        
        Args:
            grid_image: PIL Image object
            collection: Collection data
            
        Returns:
            tuple: (image_path, caption_path) paths to the exported files
        """
        # Add necessary imports
        import datetime
        
        try:
            # Find the common parent directory of all session folders
            session_folders = []
            common_parent = None
            
            # Collect all session folders
            for img_data in collection.get("images", []):
                if "session_folder" in img_data and img_data["session_folder"]:
                    session_folders.append(img_data["session_folder"])
            
            if not session_folders and self.session_manager and self.session_manager.session_folder:
                session_folders.append(self.session_manager.session_folder)
            
            if session_folders:
                # For a single session, use its parent directory
                if len(session_folders) == 1:
                    common_parent = os.path.dirname(session_folders[0])
                    logger.info(f"Using parent directory of single session: {common_parent}")
                else:
                    # For multiple sessions, find common parent
                    # Convert to list and sort for consistent processing
                    folders = sorted(list(set(session_folders)))
                    
                    # Try to find common parent by comparing path components
                    parts_list = [os.path.normpath(folder).split(os.sep) for folder in folders]
                    min_parts = min(len(parts) for parts in parts_list)
                    
                    # Find common prefix parts
                    common_parts = []
                    for i in range(min_parts):
                        if all(parts[i] == parts_list[0][i] for parts in parts_list):
                            common_parts.append(parts_list[0][i])
                        else:
                            break
                    
                    # If we found common parts, join them to form the common parent path
                    if common_parts:
                        common_parent = os.sep.join(common_parts)
                        if common_parent.endswith(os.sep):
                            common_parent = common_parent[:-1]
                        logger.info(f"Found common parent directory for export: {common_parent}")
            
            # If we couldn't determine a common parent, fall back to the workflow folder
            if not common_parent:
                if self.workflow_folder:
                    common_parent = os.path.dirname(self.workflow_folder)
                elif self.session_manager and self.session_manager.session_folder:
                    common_parent = os.path.dirname(self.session_manager.session_folder)
                else:
                    # Last resort fallback to temp directory
                    import tempfile
                    common_parent = tempfile.gettempdir()
                    logger.warning(f"Using temporary folder as fallback: {common_parent}")
            
            # Create "CompareGrids" folder in the common parent directory
            grids_folder = os.path.join(common_parent, "CompareGrids")
            if not os.path.exists(grids_folder):
                try:
                    os.makedirs(grids_folder)
                    logger.info(f"Created CompareGrids folder: {grids_folder}")
                except Exception as e:
                    logger.error(f"Failed to create CompareGrids folder, using parent folder: {str(e)}")
                    grids_folder = common_parent
            
            # Get session information or use defaults
            session_id = "CompareGrid"
            
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
                sample_id = "Unknown"
            
            # Add magnification and mode to the filename for better identification
            mag = collection.get("magnification", "")
            mode = collection.get("mode", "")
            
            # Create a descriptive base filename using just Mode and Magnification
            base_filename = f"CompareGrid_{mode}_{mag}x"
            
            # Clean up any characters that might be problematic in filenames
            for char in [':', '*', '?', '"', '<', '>', '|', '/', '\\']:
                base_filename = base_filename.replace(char, '_')
            
            # Use simple filenames without counters as requested
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
            with open(caption_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_caption(collection))
            
            # Convert to serializable format and save the collection data
            logger.info(f"Saving collection data to: {collection_path}")
            serializable_collection = convert_to_serializable(collection)
            with open(collection_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_collection, f, indent=4)
            
            logger.info(f"Export completed successfully to: {grids_folder}")
            
            return image_path, caption_path
            
        except Exception as e:
            logger.exception(f"Error during export: {str(e)}")
            raise Exception(f"Failed to export grid: {str(e)}")
    
    def _generate_caption(self, collection):
        """
        Generate a more comprehensive caption for the CompareGrid visualization.
        
        Args:
            collection: CompareGrid collection data
            
        Returns:
            str: Caption text
        """
        # Add necessary import
        import datetime
        import os
        
        mode = collection.get("mode", "Unknown")
        voltage = collection.get("high_voltage", "Unknown")
        mag = collection.get("magnification", "Unknown")
        
        caption = f"Comparison of samples imaged with {mode} detector at {mag}x magnification, {voltage} kV.\n\n"
        caption += "Samples included:\n"
        
        # Add information about each sample with more details
        for i, img in enumerate(collection.get("images", [])):
            sample_id = img.get("sample_id", "Unknown")
            sample_name = img.get("sample_name", "")
            session_folder = img.get("session_folder", "")
            session_name = os.path.basename(session_folder) if session_folder else "Unknown Session"
            image_file = os.path.basename(img.get("path", ""))
            
            # Get additional metadata if available
            metadata_dict = img.get("metadata_dict", {})
            exact_mag = metadata_dict.get("magnification", mag)
            working_distance = metadata_dict.get("working_distance_mm", "")
            spot_size = metadata_dict.get("spot_size", "")
            
            # Format sample information
            sample_text = f"{i+1}. {sample_id}"
            if sample_name:
                sample_text += f" ({sample_name})"
            
            sample_text += f"\n   Session: {session_name}"
            sample_text += f"\n   File: {image_file}"
            
            # Add detailed metadata if available
            if exact_mag:
                sample_text += f"\n   Exact magnification: {exact_mag}x"
            if working_distance:
                sample_text += f"\n   Working distance: {working_distance} mm"
            if spot_size:
                sample_text += f"\n   Spot size: {spot_size}"
            
            caption += sample_text + "\n\n"
        
        caption += f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}"
        
        return caption
