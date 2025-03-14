"""
MagGrid workflow implementation for SEM Image Workflow Manager.
Creates hierarchical visualizations of the same scene at different magnifications.
"""

import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from utils.logger import Logger
from workflows.workflow_base import WorkflowBase

logger = Logger(__name__)


class MagGridWorkflow(WorkflowBase):
    """
    Implementation of the MagGrid workflow.
    Creates hierarchical visualizations of the same scene at different magnifications.
    """
    
    def __init__(self, session_manager):
        """
        Initialize MagGrid workflow.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__(session_manager)
        self.template_match_threshold = 0.5  # Threshold for template matching
    
    def name(self):
        """Get the user-friendly name of the workflow."""
        return "MagGrid"
    
    def description(self):
        """Get the description of the workflow."""
        return "Create hierarchical visualizations of the same scene at different magnifications"
    
    def discover_collections(self):
        """
        Discover and create collections based on MagGrid criteria.
        
        Returns:
            list: List of collections
        """
        self.collections = []
        
        if not self.session_manager or not self.session_manager.metadata:
            logger.warning("No metadata available for MagGrid collection discovery")
            return self.collections
        
        logger.info("Starting MagGrid collection discovery")
        
        # Group images by mode and high voltage
        groups = {}
        for img_path, metadata in self.session_manager.metadata.items():
            if not metadata.is_valid():
                continue
                
            key = f"{metadata.mode}_{metadata.high_voltage_kV}"
            if key not in groups:
                groups[key] = []
            groups[key].append(img_path)
        
        # For each group, find potential magnification pyramids
        for key, image_paths in groups.items():
            # Sort images by magnification, lowest first
            sorted_images = []
            for img_path in image_paths:
                metadata = self.session_manager.metadata[img_path]
                sorted_images.append((img_path, metadata))
            
            sorted_images.sort(key=lambda x: x[1].magnification)
            
            # Try to build magnification pyramids
            self._build_mag_pyramids(sorted_images)
        
        logger.info(f"Discovered {len(self.collections)} MagGrid collections")
        return self.collections
    
    def _build_mag_pyramids(self, sorted_images):
        """
        Build magnification pyramids from sorted images.
        
        Args:
            sorted_images: List of (image_path, metadata) tuples sorted by magnification
        """
        if len(sorted_images) < 2:
            return
        
        # Start with lowest magnification image
        for i in range(len(sorted_images) - 1):
            low_img_path, low_metadata = sorted_images[i]
            
            # Try to build a pyramid starting with this image
            pyramid = [{"path": low_img_path, "metadata_dict": low_metadata.to_dict()}]
            
            for j in range(i + 1, len(sorted_images)):
                high_img_path, high_metadata = sorted_images[j]
                
                # Check if higher magnification image is contained within the lower one
                if self._check_containment(low_metadata, high_metadata):
                    # Perform template matching to confirm
                    match_rect = self._template_match(low_img_path, high_img_path)
                    if match_rect:
                        # Add to pyramid with match information
                        pyramid.append({
                            "path": high_img_path, 
                            "metadata_dict": high_metadata.to_dict(),
                            "match_rect": match_rect
                        })
                        
                        # Update low image for next iteration
                        low_img_path, low_metadata = high_img_path, high_metadata
            
            # If we found a pyramid with at least 2 levels, add it as a collection
            if len(pyramid) >= 2:
                # Store only JSON-serializable data in the collection
                collection = {
                    "type": "MagGrid",
                    "images": pyramid,
                    "mode": pyramid[0]["metadata_dict"]["mode"],
                    "high_voltage": pyramid[0]["metadata_dict"]["high_voltage_kV"],
                    "magnifications": [img["metadata_dict"]["magnification"] for img in pyramid]
                }
                self.collections.append(collection)
                self.save_collection(collection)
                
                logger.info(f"Found MagGrid pyramid with {len(pyramid)} levels: " + 
                           f"Magnifications: {collection['magnifications']}")
    
    def _check_containment(self, low_metadata, high_metadata):
        """
        Check if higher magnification image could be contained within the lower one.
        
        Args:
            low_metadata: Metadata for lower magnification image
            high_metadata: Metadata for higher magnification image
            
        Returns:
            bool: True if higher magnification image could be contained within the lower one
        """
        # Check if they have the same mode and high voltage
        if low_metadata.mode != high_metadata.mode or \
           low_metadata.high_voltage_kV != high_metadata.high_voltage_kV:
            return False
        
        # Check if higher magnification is at least 2x higher
        if high_metadata.magnification < low_metadata.magnification * 1.5:
            return False
        
        # Check if the higher magnification field of view fits within the lower one
        low_x = low_metadata.sample_position_x
        low_y = low_metadata.sample_position_y
        low_width = low_metadata.field_of_view_width
        low_height = low_metadata.field_of_view_height
        
        high_x = high_metadata.sample_position_x
        high_y = high_metadata.sample_position_y
        high_width = high_metadata.field_of_view_width
        high_height = high_metadata.field_of_view_height
        
        # Calculate the boundaries of the low magnification image
        low_left = low_x - low_width / 2
        low_right = low_x + low_width / 2
        low_top = low_y - low_height / 2
        low_bottom = low_y + low_height / 2
        
        # Calculate the boundaries of the high magnification image
        high_left = high_x - high_width / 2
        high_right = high_x + high_width / 2
        high_top = high_y - high_height / 2
        high_bottom = high_y + high_height / 2
        
        # Check if high magnification image is contained within low magnification image
        return (high_left >= low_left and high_right <= low_right and
                high_top >= low_top and high_bottom <= low_bottom)
    
    def _template_match(self, low_img_path, high_img_path):
        """
        Perform template matching to find the location of the high magnification image
        within the low magnification image.
        
        Args:
            low_img_path: Path to low magnification image
            high_img_path: Path to high magnification image
            
        Returns:
            tuple: (x, y, width, height) of the match rectangle, or None if no match found
        """
        try:
            # Get metadata for both images
            low_metadata = self.session_manager.metadata.get(low_img_path)
            high_metadata = self.session_manager.metadata.get(high_img_path)
            
            if not low_metadata or not high_metadata:
                logger.error("Missing metadata for template matching")
                return None
                
            # Load images
            low_img = cv2.imread(low_img_path, cv2.IMREAD_GRAYSCALE)
            high_img = cv2.imread(high_img_path, cv2.IMREAD_GRAYSCALE)
            
            if low_img is None or high_img is None:
                logger.error(f"Failed to load images for template matching")
                return None
            
            # Calculate scale factor based on field of view
            # This represents how much smaller the high mag image needs to be to match the scale of the low mag image
            if low_metadata.field_of_view_width and high_metadata.field_of_view_width:
                scale_factor = high_metadata.field_of_view_width / low_metadata.field_of_view_width
            else:
                # Fallback to magnification ratio if FOV is not available
                scale_factor = low_metadata.magnification / high_metadata.magnification
                
            logger.debug(f"Template matching with scale factor: {scale_factor}")
            
            # Ensure scale factor is reasonable
            if scale_factor < 0.01 or scale_factor > 0.9:
                logger.warning(f"Unusual scale factor: {scale_factor}, using default 0.5")
                scale_factor = 0.5
            
            # Resize high mag image to match the scale of the low mag image
            template = cv2.resize(high_img, (0, 0), fx=scale_factor, fy=scale_factor)
            
            # Get template dimensions
            template_h, template_w = template.shape
            
            # Perform template matching
            result = cv2.matchTemplate(low_img, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val < self.template_match_threshold:
                logger.debug(f"Template matching failed: score {max_val} below threshold {self.template_match_threshold}")
                return None
            
            # top-left corner of match
            x, y = max_loc
            
            # Use the template dimensions directly since we've already scaled it
            w = template_w
            h = template_h
            
            logger.debug(f"Template match found: ({x}, {y}) to ({x+w}, {y+h}) with score {max_val}")
            return (x, y, w, h)
                
        except Exception as e:
            logger.error(f"Error in template matching: {str(e)}")
            return None
    
    def create_grid(self, collection, layout=None, options=None):
        """
        Create a grid visualization for the MagGrid collection.
        
        Args:
            collection: MagGrid collection to visualize
            layout (tuple, optional): Grid layout as (rows, columns)
            options (dict, optional): Annotation options
            
        Returns:
            PIL.Image: Grid visualization image
        """
        if not collection or "images" not in collection or len(collection["images"]) < 2:
            logger.error("Invalid collection for MagGrid visualization")
            return None
        
        # Default options if none provided
        if options is None:
            options = {
                "box_style": "solid",
                "label_style": "none"
            }
        
        # Determine layout based on number of images if not specified
        images = collection["images"]
        num_images = len(images)
        
        if not layout:
            if num_images == 2:
                layout = (2, 1)  # 2 rows, 1 column
            elif num_images <= 4:
                layout = (2, 2)  # 2 rows, 2 columns
            else:
                layout = (3, 2)  # 3 rows, 2 columns
        
        rows, cols = layout
        logger.info(f"Creating MagGrid with layout {rows}x{cols} for {num_images} images")
        
        # Load all images
        pil_images = []
        for img_data in images:
            try:
                img_path = img_data["path"]
                img = Image.open(img_path)
                pil_images.append(img)
            except Exception as e:
                logger.error(f"Error loading image {img_path}: {str(e)}")
                return None
        
        # Determine the size of grid cells (use the max width and height)
        cell_width = max(img.width for img in pil_images)
        cell_height = max(img.height for img in pil_images)
        
        # Create a blank grid image with spacing
        spacing = 10  # Increased spacing between images (was 4)
        grid_width = cols * cell_width + (cols - 1) * spacing
        grid_height = rows * cell_height + (rows - 1) * spacing
        grid_img = Image.new('RGB', (grid_width, grid_height), color='white')
        
        # Place images in the grid
        # For MagGrid, we place from lowest to highest magnification
        # left to right, top to bottom
        draw = ImageDraw.Draw(grid_img)
        
        try:
            # Try to load a font
            font = ImageFont.truetype("arial.ttf", 10)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Define colors for bounding boxes
        box_colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
        ]
        
        # Place images and draw bounding boxes
        for i, (img_data, img) in enumerate(zip(images, pil_images)):
            row = i // cols
            col = i % cols
            
            # Calculate position
            x = col * (cell_width + spacing)
            y = row * (cell_height + spacing)
            
            # Center the image in its cell
            x_offset = (cell_width - img.width) // 2
            y_offset = (cell_height - img.height) // 2
            
            # Paste the image
            grid_img.paste(img, (x + x_offset, y + y_offset))
            
            # Draw magnification label
            mag = img_data["metadata_dict"]["magnification"]
            label = f"{mag}x"
            draw.text((x + 5, y + 5), label, fill=(255, 255, 255), font=font, stroke_width=1, stroke_fill=(0, 0, 0))
            
            # Add filename label if requested
            if options.get("label_style") == "filename":
                try:
                    filename = os.path.basename(img_data["path"])
                    # Draw filename at the top left corner of the image
                    label_x = x + x_offset
                    label_y = y + y_offset - 15  # Position above the image
                    
                    # Add a background for better readability
                    text_bbox = draw.textbbox((label_x, label_y), filename, font=font)
                    draw.rectangle(text_bbox, fill="white")
                    
                    # Draw text
                    draw.text((label_x, label_y), filename, fill=(0, 0, 0), font=font)
                    logger.debug(f"Added filename label: {filename}")
                except Exception as e:
                    logger.error(f"Error adding filename label: {str(e)}")
            
            # If this is not the highest magnification and box style is not 'none', draw bounding box
            if i < len(images) - 1 and options["box_style"] != "none":
                next_img_data = images[i+1]
                
                # Check if match_rect exists in the next image data
                if "match_rect" in next_img_data:
                    match_rect = next_img_data["match_rect"]
                    
                    # Get color for this box
                    color = box_colors[i % len(box_colors)]
                    
                    # Draw bounding box based on style
                    mx, my, mw, mh = match_rect
                    
                    # Calculate absolute coordinates in the grid
                    box_x = x + x_offset + mx
                    box_y = y + y_offset + my
                    
                    # Calculate right and bottom edges
                    box_right = box_x + mw
                    box_bottom = box_y + mh
                    
                    # Log the box coordinates for debugging
                    logger.debug(f"Drawing box at ({box_x}, {box_y}) to ({box_right}, {box_bottom})")
                    
                    # Draw the box according to selected style
                    if options["box_style"] == "solid":
                        # Draw rectangle using the exact coordinates from template matching
                        draw.rectangle(
                            [box_x, box_y, box_right, box_bottom],
                            outline=color,
                            width=2
                        )
                    elif options["box_style"] == "dotted":
                        # Draw dotted rectangle by using short lines
                        dots = 20  # Number of dots per side
                        for d in range(dots):
                            # Top edge
                            tx1 = box_x + (mw * d / dots)
                            tx2 = box_x + (mw * (d + 0.5) / dots)
                            draw.line([(tx1, box_y), (tx2, box_y)], fill=color, width=2)
                            
                            # Bottom edge
                            bx1 = box_x + (mw * d / dots)
                            bx2 = box_x + (mw * (d + 0.5) / dots)
                            draw.line([(bx1, box_bottom), (bx2, box_bottom)], fill=color, width=2)
                            
                            # Left edge
                            ly1 = box_y + (mh * d / dots)
                            ly2 = box_y + (mh * (d + 0.5) / dots)
                            draw.line([(box_x, ly1), (box_x, ly2)], fill=color, width=2)
                            
                            # Right edge
                            ry1 = box_y + (mh * d / dots)
                            ry2 = box_y + (mh * (d + 0.5) / dots)
                            draw.line([(box_right, ry1), (box_right, ry2)], fill=color, width=2)
                    elif options["box_style"] == "corners":
                        # Draw just the corners (L shapes)
                        corner_length = min(20, mw/4, mh/4)  # Length of corner lines
                        
                        # Top-left corner
                        draw.line([(box_x, box_y), (box_x + corner_length, box_y)], fill=color, width=2)
                        draw.line([(box_x, box_y), (box_x, box_y + corner_length)], fill=color, width=2)
                        
                        # Top-right corner
                        draw.line([(box_right - corner_length, box_y), (box_right, box_y)], fill=color, width=2)
                        draw.line([(box_right, box_y), (box_right, box_y + corner_length)], fill=color, width=2)
                        
                        # Bottom-left corner
                        draw.line([(box_x, box_bottom - corner_length), (box_x, box_bottom)], fill=color, width=2)
                        draw.line([(box_x, box_bottom), (box_x + corner_length, box_bottom)], fill=color, width=2)
                        
                        # Bottom-right corner
                        draw.line([(box_right - corner_length, box_bottom), (box_right, box_bottom)], fill=color, width=2)
                        draw.line([(box_right, box_bottom - corner_length), (box_right, box_bottom)], fill=color, width=2)
                    
                    # Draw corresponding colored border on the next image
                    if i+1 < len(images):
                        next_row = (i+1) // cols
                        next_col = (i+1) % cols
                        next_x = next_col * (cell_width + spacing)
                        next_y = next_row * (cell_height + spacing)
                        next_img = pil_images[i+1]
                        
                        # Calculate offsets for centering
                        next_x_offset = (cell_width - next_img.width) // 2
                        next_y_offset = (cell_height - next_img.height) // 2
                        
                        # Draw colored border around the next image
                        border_width = 2
                        next_box_x = next_x + next_x_offset
                        next_box_y = next_y + next_y_offset
                        draw.rectangle(
                            [
                                next_box_x - border_width,
                                next_box_y - border_width,
                                next_box_x + next_img.width + border_width,
                                next_box_y + next_img.height + border_width
                            ],
                            outline=color,
                            width=border_width
                        )
        
        logger.info(f"Created MagGrid visualization with {num_images} images")
        return grid_img
    
    def _generate_caption(self, collection):
        """
        Generate a caption for the MagGrid visualization.
        
        Args:
            collection: MagGrid collection data
            
        Returns:
            str: Caption text
        """
        sample_id = "Unknown"
        if self.session_manager and self.session_manager.current_session:
            sample_id = self.session_manager.current_session.sample_id
        
        # Get information from collection
        mode = collection.get("mode", "Unknown")
        voltage = collection.get("high_voltage", "Unknown")
        mags = collection.get("magnifications", [])
        
        mag_str = ", ".join([f"{mag}x" for mag in mags])
        
        caption = f"Sample {sample_id} imaged with {mode} detector at {voltage} kV.\n"
        caption += f"Magnification series: {mag_str}."
        
        return caption
