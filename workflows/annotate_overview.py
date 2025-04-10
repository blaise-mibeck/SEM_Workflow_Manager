"""
AnnotateOverview workflow implementation for SEM Image Workflow Manager.
Creates annotated overview images with metadata data bar.
"""

import os
import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from utils.logger import Logger
from workflows.workflow_base import WorkflowBase

logger = Logger(__name__)


class AnnotateOverviewWorkflow(WorkflowBase):
    """
    Implementation of the AnnotateOverview workflow.
    Creates annotated overview images with metadata data bar.
    """
    
    def __init__(self, session_manager):
        """
        Initialize AnnotateOverview workflow.
        
        Args:
            session_manager: Session manager instance
        """
        super().__init__(session_manager)
    
    def name(self):
        """Get the user-friendly name of the workflow."""
        return "AnnotateOverview"
    
    def description(self):
        """Get the description of the workflow."""
        return "Create annotated overview images with metadata data bar"
    
    def discover_collections(self):
        """
        Discover and create collections based on AnnotateOverview criteria.
        Recursively searches for folders containing "Stitch" or "stitch",
        then recursively searches within those folders for images with "-Overview.tiff".
        
        Returns:
            list: List of collections
        """
        self.collections = []
        
        if not self.session_manager or not self.session_manager.current_session:
            logger.warning("No session available for AnnotateOverview collection discovery")
            return self.collections
        
        logger.info("Starting AnnotateOverview collection discovery")
        
        # Get the session folder
        session_folder = self.session_manager.session_folder
        if not session_folder or not os.path.exists(session_folder):
            logger.warning(f"Session folder does not exist: {session_folder}")
            return self.collections
        
        # Recursively find all Stitch folders
        stitch_folders = []
        self._find_stitch_folders(session_folder, stitch_folders)
        
        if not stitch_folders:
            logger.warning("No 'Stitch' folders found in the session")
        else:
            logger.info(f"Found {len(stitch_folders)} 'Stitch' folders: {stitch_folders}")
        
        # Find overview images in stitch folders
        overview_images = []
        for stitch_folder in stitch_folders:
            self._find_overview_images(stitch_folder, overview_images)
        
        if not overview_images:
            logger.warning("No '-Overview.tiff' images found in Stitch folders")
        else:
            logger.info(f"Found {len(overview_images)} overview images")
        
        # If we found overview images, add them to the collection
        if overview_images:
            # Create a collection with all the overview images
            collection_images = []
            
            for img_data in overview_images:
                img_path = img_data["path"]
                
                # Try to get metadata if available
                metadata = None
                metadata_dict = {}
                
                if self.session_manager.metadata and img_path in self.session_manager.metadata:
                    metadata = self.session_manager.metadata[img_path]
                    if metadata and metadata.is_valid():
                        metadata_dict = metadata.to_dict()
                        
                # If we don't have metadata, create minimal metadata
                if not metadata:
                    logger.warning(f"No metadata available for {img_path}, using minimal information")
                    # Extract what info we can from the filename and path
                    filename = os.path.basename(img_path)
                    metadata_dict = {
                        "image_path": img_path,
                        "filename": filename,
                        "acquisition_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                
                # Add to collection images
                collection_images.append({
                    "path": img_path,
                    "metadata_dict": metadata_dict,
                    "is_overview": True,
                    "magnification": metadata_dict.get("magnification", "Unknown")
                })
            
            # Create collection
            collection = {
                "type": "AnnotateOverview",
                "id": "annotate_overview_collection",
                "images": collection_images,
                "description": "Overview images from Stitch folders"
            }
            
            self.collections.append(collection)
            self.save_collection(collection)
            
            logger.info(f"Created AnnotateOverview collection with {len(collection_images)} images")
        
        return self.collections
    
    def _find_stitch_folders(self, root_folder, stitch_folders):
        """
        Recursively find all folders containing 'Stitch' or 'stitch' in the name.
        
        Args:
            root_folder: The root folder to start the search from
            stitch_folders: List to populate with found stitch folders
        """
        try:
            for item in os.listdir(root_folder):
                full_path = os.path.join(root_folder, item)
                
                # Check if it's a directory
                if os.path.isdir(full_path):
                    # Check if "stitch" is in the name (case insensitive)
                    if "stitch" in item.lower():
                        stitch_folders.append(full_path)
                        logger.info(f"Found stitch folder: {full_path}")
                    
                    # Recursively search in this directory
                    self._find_stitch_folders(full_path, stitch_folders)
        except Exception as e:
            logger.error(f"Error searching for stitch folders in {root_folder}: {str(e)}")
    
    def _find_overview_images(self, stitch_folder, overview_images):
        """
        Recursively find all images with '-Overview.tiff' in the name.
        
        Args:
            stitch_folder: The stitch folder to search in
            overview_images: List to populate with found overview images
        """
        try:
            for root, dirs, files in os.walk(stitch_folder):
                for file in files:
                    # Check if this is an overview image
                    if "-Overview.tiff" in file:
                        img_path = os.path.join(root, file)
                        logger.info(f"Found overview image: {img_path}")
                        
                        overview_images.append({
                            "path": img_path,
                            "is_overview": True
                        })
        except Exception as e:
            logger.error(f"Error searching for overview images in {stitch_folder}: {str(e)}")
    
    def create_grid(self, collection, layout=None, options=None):
        """
        Create annotated overview image with data bar.
        Also automatically marks locations of session images with crosshairs.
        
        Args:
            collection: AnnotateOverview collection
            layout (tuple, optional): Not used in this workflow
            options (dict, optional): Annotation options including:
                - annotations: List of annotation objects
                - include_data_bar: Boolean to include data bar
                - mark_session_images: Boolean to mark session images
                - selected_locations: List of indices of selected images to mark
            
        Returns:
            PIL.Image: Annotated image
        """
        if not collection or "images" not in collection or not collection["images"]:
            logger.error("Invalid collection for AnnotateOverview visualization")
            return None
        
        # Get the first image (assumed to be the best overview image)
        image_data = collection["images"][0]
        image_path = image_data["path"]
        metadata_dict = image_data["metadata_dict"]
        
        # Default options if none provided
        if options is None:
            options = {
                "annotations": [],  # List of annotation objects
                "include_data_bar": True,
                "mark_session_images": True,  # Default to marking session images
                "selected_locations": None  # No specific locations selected
            }
        
        try:
            # Load the image
            img = Image.open(image_path)
            
            # Make a copy to work with
            img = img.copy()
            
            # Mark session image locations if requested
            if options.get("mark_session_images", True):
                selected_locations = options.get("selected_locations")
                img = self._mark_session_image_locations(img, image_path, selected_locations)
            
            # Apply user annotations if any
            if options.get("annotations"):
                img = self._apply_annotations(img, options["annotations"])
            
            # Add data bar if requested
            if options.get("include_data_bar", True):
                img = self._add_data_bar(img, metadata_dict)
            
            return img
            
        except Exception as e:
            logger.error(f"Error creating annotated image: {str(e)}")
            return None
    
    def _apply_annotations(self, img, annotations):
        """
        Apply annotations to the image.
        
        Args:
            img: PIL Image
            annotations: List of annotation objects
            
        Returns:
            PIL.Image: Annotated image
        """
        # Create a drawing context
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except IOError:
            try:
                # Try system font locations
                import sys
                if sys.platform == "win32":
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 14)
                elif sys.platform == "darwin":  # macOS
                    font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 14)
                else:  # Linux
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
        
        # Apply each annotation
        for annotation in annotations:
            annotation_type = annotation.get("type")
            
            if annotation_type == "arrow":
                # Draw an arrow
                start = annotation.get("start", (0, 0))
                end = annotation.get("end", (100, 100))
                color = annotation.get("color", (255, 0, 0))
                width = annotation.get("width", 2)
                
                # Draw the arrow line
                draw.line([start, end], fill=color, width=width)
                
                # Draw the arrow head
                arrow_head_size = width * 3
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = (dx**2 + dy**2)**0.5
                
                if length > 0:
                    udx = dx / length
                    udy = dy / length
                    
                    # Calculate the arrow head points
                    perp_x = -udy * arrow_head_size
                    perp_y = udx * arrow_head_size
                    
                    point1 = (end[0] - udx * arrow_head_size + perp_x, 
                              end[1] - udy * arrow_head_size + perp_y)
                    point2 = (end[0] - udx * arrow_head_size - perp_x, 
                              end[1] - udy * arrow_head_size - perp_y)
                    
                    # Draw the arrow head
                    draw.polygon([end, point1, point2], fill=color)
            
            elif annotation_type == "text":
                # Draw text
                position = annotation.get("position", (0, 0))
                text = annotation.get("text", "")
                color = annotation.get("color", (255, 0, 0))
                bg_color = annotation.get("background_color", None)
                
                # Add background if specified
                if bg_color:
                    # Calculate text size
                    text_bbox = draw.textbbox(position, text, font=font)
                    # Draw background rectangle
                    draw.rectangle(text_bbox, fill=bg_color)
                
                # Draw text
                draw.text(position, text, fill=color, font=font)
            
            elif annotation_type == "circle":
                # Draw a circle
                center = annotation.get("center", (0, 0))
                radius = annotation.get("radius", 20)
                color = annotation.get("color", (255, 0, 0))
                width = annotation.get("width", 2)
                fill = annotation.get("fill", None)
                
                # Calculate bounding box for the circle
                bbox = [
                    center[0] - radius, center[1] - radius,
                    center[0] + radius, center[1] + radius
                ]
                
                # Draw the circle
                draw.ellipse(bbox, outline=color, width=width, fill=fill)
            
            elif annotation_type == "rectangle":
                # Draw a rectangle
                top_left = annotation.get("top_left", (0, 0))
                bottom_right = annotation.get("bottom_right", (100, 100))
                color = annotation.get("color", (255, 0, 0))
                width = annotation.get("width", 2)
                fill = annotation.get("fill", None)
                
                # Draw the rectangle
                draw.rectangle([top_left, bottom_right], outline=color, width=width, fill=fill)
        
        return img
    
    def _add_data_bar(self, img, metadata_dict):
        """
        Add a data bar to the image containing important metadata.
        
        Args:
            img: PIL Image
            metadata_dict: Dictionary of metadata
            
        Returns:
            PIL.Image: Image with data bar
        """
        # Define data bar dimensions
        data_bar_height = 30
        margin = 10
        
        # Create a new image with space for the data bar
        new_img = Image.new('RGB', (img.width, img.height + data_bar_height), color='black')
        
        # Paste the original image
        new_img.paste(img, (0, 0))
        
        # Create a drawing context
        draw = ImageDraw.Draw(new_img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except IOError:
            try:
                # Try system font locations
                import sys
                if sys.platform == "win32":
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 12)
                elif sys.platform == "darwin":  # macOS
                    font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 12)
                else:  # Linux
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
        
        # Extract key metadata
        magnification = metadata_dict.get("magnification", "")
        working_distance = metadata_dict.get("working_distance_mm", "")
        high_voltage = metadata_dict.get("high_voltage_kV", "")
        detector = metadata_dict.get("detector", metadata_dict.get("mode", ""))
        acquisition_date = metadata_dict.get("acquisition_date", "")
        
        # If acquisition_date is not available, use current date
        if not acquisition_date:
            acquisition_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Get scale information
        fov_width = metadata_dict.get("field_of_view_width", 0)
        
        # Format scale text
        scale_text = ""
        if fov_width:
            if fov_width >= 1000:
                scale_text = f"{fov_width/1000:.1f} mm"
            else:
                scale_text = f"{fov_width:.0f} μm"
        
        # Get session info
        session_id = "Unknown"
        if self.session_manager and self.session_manager.current_session:
            session_id = os.path.basename(self.session_manager.session_folder)
            
        # Get sample ID
        sample_id = "Unknown"
        if self.session_manager and self.session_manager.current_session:
            sample_id = self.session_manager.current_session.sample_id
        
        # Prepare data bar information
        info_text = f"Mag. (Pol) {magnification}× | FW {working_distance} mm | HV {high_voltage} kV | Int. Image | Det. {detector}"
        
        # Combine session ID and filename for identifier
        filename = os.path.basename(metadata_dict.get("image_path", ""))
        identifier = f"{session_id} {filename}"
        
        # Add timestamp
        timestamp = acquisition_date
        
        # Calculate positions
        info_x = img.width // 3
        timestamp_x = 2 * img.width // 3
        
        # Draw scale bar (if available)
        if fov_width:
            # Calculate scale bar length in pixels
            scale_bar_width = img.width // 5
            scale_bar_y = img.height + (data_bar_height // 2)
            scale_bar_x = margin
            
            # Draw scale bar
            draw.line(
                [(scale_bar_x, scale_bar_y), (scale_bar_x + scale_bar_width, scale_bar_y)],
                fill=(255, 255, 255),
                width=2
            )
            
            # Draw scale text
            draw.text(
                (scale_bar_x, scale_bar_y + 5),
                scale_text,
                fill=(255, 255, 255),
                font=font,
                anchor="lt"
            )
        
        # Draw metadata info
        draw.text(
            (info_x, img.height + (data_bar_height // 2)),
            info_text,
            fill=(255, 255, 255),
            font=font,
            anchor="mm"
        )
        
        # Draw timestamp and identifier
        draw.text(
            (timestamp_x, img.height + (data_bar_height // 2)),
            f"{timestamp} {identifier}",
            fill=(255, 255, 255),
            font=font,
            anchor="mm"
        )
        
        return new_img
    
    def export_grid(self, grid_image, collection):
        """
        Export annotated overview image with custom filename.
        
        Args:
            grid_image: PIL Image
            collection: Collection data
            
        Returns:
            tuple: (image_path, caption_path) paths to the exported files
        """
        try:
            # Get session information
            session_id = "Unknown"
            sample_id = "Unknown"
            client_id = ""
            
            if self.session_manager and self.session_manager.current_session:
                session_id = os.path.basename(self.session_manager.session_folder)
                sample_id = self.session_manager.current_session.sample_id or "Unknown"
                client_id = self.session_manager.current_session.client_sample_id or ""
            
            # Sanitize IDs for filename
            for char in [':', '*', '?', '"', '<', '>', '|', '/', '\\']:
                session_id = session_id.replace(char, '_')
                sample_id = sample_id.replace(char, '_')
                client_id = client_id.replace(char, '_')
            
            # Construct filename
            filename = f"{session_id}_{sample_id}_{client_id}_AnnotatedOverview"
            
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
            
            # Create an "Annotated" folder in the project folder
            annotated_folder = os.path.join(project_folder, "Annotated")
            if not os.path.exists(annotated_folder):
                try:
                    os.makedirs(annotated_folder)
                    logger.info(f"Created Annotated folder: {annotated_folder}")
                except Exception as e:
                    logger.error(f"Failed to create Annotated folder, using project folder: {str(e)}")
                    annotated_folder = project_folder
            
            # Create full paths
            image_path = os.path.join(annotated_folder, f"{filename}.tiff")
            caption_path = os.path.join(annotated_folder, f"{filename}.txt")
            
            # Save the image
            logger.info(f"Saving annotated image to: {image_path}")
            grid_image.save(image_path, format="TIFF")
            
            # Create a caption file
            logger.info(f"Saving caption to: {caption_path}")
            with open(caption_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_caption(collection))
            
            logger.info(f"Export completed successfully")
            
            return image_path, caption_path
            
        except Exception as e:
            logger.exception(f"Error during export: {str(e)}")
            raise Exception(f"Failed to export annotated image: {str(e)}")
    
    def _mark_session_image_locations(self, img, overview_path, selected_locations=None):
        """
        Mark session image locations on the overview image with crosshairs
        and add coordinate rulers along the edges.
        
        Args:
            img: PIL Image (overview image)
            overview_path: Path to the overview image
            selected_locations: List of indices of selected images to mark (if None, mark all)
            
        Returns:
            PIL.Image: Image with coordinate rulers and marked session image locations
        """
        if not self.session_manager or not self.session_manager.metadata:
            logger.warning("No session metadata available to mark image locations")
            return img
            
        # Create a larger image with space for rulers
        ruler_width = 60  # Increased width of the ruler in pixels for better visibility
        new_width = img.width + ruler_width
        new_height = img.height + ruler_width
        
        # Create a new white image
        new_img = Image.new('RGB', (new_width, new_height), color='white')
        
        # Paste the original image in the proper position (right and top of rulers)
        new_img.paste(img, (ruler_width, 0))
        
        # Create a drawing context for the new image with rulers
        draw = ImageDraw.Draw(new_img)
        
        # Try to load a font for labels with larger size for better visibility
        try:
            font = ImageFont.truetype("arial.ttf", 16)  # Increased font size
        except IOError:
            try:
                # Try system font locations
                import sys
                if sys.platform == "win32":
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 16)
                elif sys.platform == "darwin":  # macOS
                    font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 16)
                else:  # Linux
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
        
        # Try to get font for rulers - larger than before
        try:
            ruler_font = ImageFont.truetype("arial.ttf", 14)  # Increased font size
        except IOError:
            try:
                # Try system font locations
                import sys
                if sys.platform == "win32":
                    ruler_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 14)
                elif sys.platform == "darwin":  # macOS
                    ruler_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 14)
                else:  # Linux
                    ruler_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except:
                # Fallback to default font
                ruler_font = ImageFont.load_default()
        
        # Draw rulers
        # Get stitch coordinates from overview image metadata
        overview_stitch_x = 0  # Default stitch offset X
        overview_stitch_y = 0  # Default stitch offset Y
        
        # Field of view or scale factors
        magnification = 1000
        fov_width_um = img.width  # Default to pixels if no metadata
        fov_height_um = img.height
        
        # Initialize microscope coordinate variables
        overview_stage_x = 0
        overview_stage_y = 0
        
        # Check if overview path is in metadata
        if overview_path in self.session_manager.metadata:
            md = self.session_manager.metadata[overview_path]
            overview_stitch_x = md.stitch_offset_x if hasattr(md, 'stitch_offset_x') else 0
            overview_stitch_y = md.stitch_offset_y if hasattr(md, 'stitch_offset_y') else 0
            
            # Try to get field of view information
            if hasattr(md, 'field_of_view_width'):
                fov_width_um = md.field_of_view_width
                # Estimate height based on aspect ratio
                fov_height_um = fov_width_um * img.height / img.width
            
            # Get magnification if available
            if hasattr(md, 'magnification'):
                magnification = md.magnification
        
            # Try to get position in this order: sample_position, stage_position, stitch_offset
            # First try sample_position - these are in meters, convert to micrometers
            if hasattr(md, 'sample_position_x') and hasattr(md, 'sample_position_y'):
                sample_x = md.sample_position_x
                sample_y = md.sample_position_y
                
                # Check if values are very small (likely in meters)
                if abs(sample_x) < 1 and abs(sample_y) < 1:
                    # Convert from meters to micrometers (multiply by 1,000,000)
                    overview_stage_x = sample_x * 1000000
                    overview_stage_y = sample_y * 1000000
                    logger.info(f"Overview image center coordinates from sample_position: X={overview_stage_x}μm, Y={overview_stage_y}μm (converted from meters)")
                else:
                    overview_stage_x = sample_x
                    overview_stage_y = sample_y
                    logger.info(f"Overview image center coordinates from sample_position: X={overview_stage_x}μm, Y={overview_stage_y}μm")
            # Then try stage_position
            elif hasattr(md, 'stage_position_x') and hasattr(md, 'stage_position_y'):
                overview_stage_x = md.stage_position_x
                overview_stage_y = md.stage_position_y
                logger.info(f"Overview image center coordinates from stage_position: X={overview_stage_x}μm, Y={overview_stage_y}μm")
            # Finally try stitch_offset
            elif hasattr(md, 'stitch_offset_x') and hasattr(md, 'stitch_offset_y'):
                overview_stage_x = md.stitch_offset_x
                overview_stage_y = md.stitch_offset_y
                logger.info(f"Overview image center coordinates from stitch_offset: X={overview_stage_x}μm, Y={overview_stage_y}μm")
            
        # Calculate physical units per pixel
        um_per_pixel_x = fov_width_um / img.width
        um_per_pixel_y = fov_height_um / img.height
        
        # Determine if we should use mm or μm based on size
        use_mm_x = fov_width_um >= 1000
        use_mm_y = fov_height_um >= 1000
        
        # Draw axes lines with increased width for better visibility
        ruler_color = (50, 50, 50)  # Darker gray for better contrast
        tick_length = 8  # Increased tick length
        
        # Draw horizontal axis (top for physical, bottom for pixels)
        draw.line([(ruler_width, 0), (new_width, 0)], fill=ruler_color, width=2)  # Top axis
        draw.line([(ruler_width, img.height), (new_width, img.height)], fill=ruler_color, width=2)  # Bottom axis
        
        # Draw vertical axis (left for physical, right for pixels)
        draw.line([(ruler_width, 0), (ruler_width, img.height)], fill=ruler_color, width=2)  # Left axis
        draw.line([(new_width - 1, 0), (new_width - 1, img.height)], fill=ruler_color, width=2)  # Right axis
        
        # Draw tick marks and labels for horizontal physical units (top)
        tick_step_x = img.width // 10  # Divide into 10 segments
        for i in range(11):  # 0 to 10
            x = ruler_width + i * tick_step_x
            pos_um = i * tick_step_x * um_per_pixel_x  # Position in micrometers
            
            # Draw tick mark with increased width
            draw.line([(x, 0), (x, tick_length)], fill=ruler_color, width=2)
            
            # Format label based on units
            if use_mm_x:
                label = f"{pos_um/1000:.1f} mm"
            else:
                label = f"{pos_um:.0f} μm"
                
            # Draw label with larger font and better positioning
            text_bbox = draw.textbbox((x, tick_length + 4), label, font=ruler_font)
            draw.rectangle(text_bbox, fill=(255, 255, 255, 220))  # Background for better visibility
            draw.text((x, tick_length + 4), label, fill=ruler_color, font=ruler_font, anchor="mt")
        
        # Draw tick marks and labels for vertical physical units (left)
        tick_step_y = img.height // 10  # Divide into 10 segments
        for i in range(11):  # 0 to 10
            y = i * tick_step_y
            pos_um = i * tick_step_y * um_per_pixel_y  # Position in micrometers
            
            # Draw tick mark with increased width
            draw.line([(ruler_width - tick_length, y), (ruler_width, y)], fill=ruler_color, width=2)
            
            # Format label based on units
            if use_mm_y:
                label = f"{pos_um/1000:.1f} mm"
            else:
                label = f"{pos_um:.0f} μm"
                
            # Draw label with larger font and better positioning
            text_bbox = draw.textbbox((ruler_width - tick_length - 4, y), label, font=ruler_font)
            draw.rectangle(text_bbox, fill=(255, 255, 255, 220))  # Background for better visibility
            draw.text((ruler_width - tick_length - 4, y), label, fill=ruler_color, font=ruler_font, anchor="rm")
        
        # Draw tick marks and labels for horizontal pixel units (bottom)
        for i in range(11):  # 0 to 10
            x = ruler_width + i * tick_step_x
            pixel_pos = i * tick_step_x
            
            # Draw tick mark at bottom with increased width
            draw.line([(x, img.height - tick_length), (x, img.height)], fill=ruler_color, width=2)
            
            # Draw label with larger font and better positioning
            text_bbox = draw.textbbox((x, img.height - tick_length - 4), f"{pixel_pos}px", font=ruler_font)
            draw.rectangle(text_bbox, fill=(255, 255, 255, 220))  # Background for better visibility
            draw.text((x, img.height - tick_length - 4), f"{pixel_pos}px", fill=ruler_color, font=ruler_font, anchor="mb")
        
        # Draw tick marks and labels for vertical pixel units (right)
        for i in range(11):  # 0 to 10
            y = i * tick_step_y
            pixel_pos = i * tick_step_y
            
            # Draw tick mark with increased width
            draw.line([(new_width - 1, y), (new_width - 1 - tick_length, y)], fill=ruler_color, width=2)
            
            # Draw label with larger font and better positioning
            text_bbox = draw.textbbox((new_width - 1 - tick_length - 4, y), f"{pixel_pos}px", font=ruler_font)
            draw.rectangle(text_bbox, fill=(255, 255, 255, 220))  # Background for better visibility
            draw.text((new_width - 1 - tick_length - 4, y), f"{pixel_pos}px", fill=ruler_color, font=ruler_font, anchor="rm")
        
        # Get session images to mark
        session_images = []
        session_image_paths = []
        
        # Collect all valid session images with position data
        for img_path, metadata in self.session_manager.metadata.items():
            # Skip the overview image itself
            if img_path == overview_path:
                continue
            
            # Skip images that don't have valid metadata
            if not metadata or not metadata.is_valid():
                continue
            
            # Try to get the image position in multiple ways (in order of preference)
            # 1. sample_position (from metadata_extractor.py)
            # 2. stage_position
            # 3. stitch_offset
            
            img_x, img_y = None, None
            position_type = ""
            
            # First check for sample position (these are in meters, need to convert to micrometers)
            if hasattr(metadata, 'sample_position_x') and hasattr(metadata, 'sample_position_y'):
                img_x = metadata.sample_position_x
                img_y = metadata.sample_position_y
                
                # Check if values are very small (likely in meters)
                if abs(img_x) < 1 and abs(img_y) < 1:
                    # Convert from meters to micrometers (multiply by 1,000,000)
                    img_x = img_x * 1000000
                    img_y = img_y * 1000000
                    logger.info(f"Converted sample position from meters to micrometers: ({img_x}, {img_y})")
                
                position_type = "sample_position"
            
            # If no sample position, try stage position
            if (img_x is None or img_y is None) and hasattr(metadata, 'stage_position_x') and hasattr(metadata, 'stage_position_y'):
                img_x = metadata.stage_position_x
                img_y = metadata.stage_position_y
                position_type = "stage_position"
            
            # If no stage position, try stitch coordinates
            if (img_x is None or img_y is None) and hasattr(metadata, 'stitch_offset_x') and hasattr(metadata, 'stitch_offset_y'):
                img_x = metadata.stitch_offset_x
                img_y = metadata.stitch_offset_y
                position_type = "stitch_offset"
                
            # As a last resort, check different properties in the to_dict result
            if (img_x is None or img_y is None) and hasattr(metadata, 'to_dict'):
                md_dict = metadata.to_dict()
                for key in md_dict:
                    if img_x is None and ('position_x' in key.lower() or 'pos_x' in key.lower()):
                        img_x = md_dict[key]
                    if img_y is None and ('position_y' in key.lower() or 'pos_y' in key.lower()):
                        img_y = md_dict[key]
                if img_x is not None and img_y is not None:
                    position_type = "dictionary_search"
            
            # Skip if don't have any coordinates
            if img_x is None or img_y is None:
                logger.warning(f"No position data found for image: {os.path.basename(img_path)}")
                continue
                
            logger.info(f"Found {position_type} coordinates for {os.path.basename(img_path)}: ({img_x}, {img_y})")
            
            # Create image data object with position information
            session_images.append({
                "path": img_path,
                "metadata": metadata,
                "pos_x": img_x,  # Store exact coordinates
                "pos_y": img_y,
                "position_type": position_type  # Store what type of position information we found
            })
            session_image_paths.append(img_path)
        
        # Initialize a counter for labeling images
        image_count = 0
        
        # Process the selected locations if provided
        filtered_images = []
        if selected_locations is not None and len(selected_locations) > 0:
            for idx in selected_locations:
                if 0 <= idx < len(session_images):
                    filtered_images.append(session_images[idx])
        else:
            # If no specific locations selected, use all images
            filtered_images = session_images
        
        # Draw crosshairs for the filtered session images
        for img_data in filtered_images:
            # Extract position data
            img_x = img_data["pos_x"]
            img_y = img_data["pos_y"]
            
            # We need to convert microscope coordinates to canvas coordinates
            # Microscope coordinates (img_x, img_y) are in microns from a reference point
            # For SEM, coordinates increase upward and leftward
            
            # First calculate the offset from the overview center
            # For microscope coordinates: X increases going LEFT, Y increases going UP
            dx_um = img_x - overview_stage_x  # Positive when image is to the left of center (img_x greater)
            dy_um = img_y - overview_stage_y  # Positive when image is above center (img_y greater)
            
            # Convert to pixels (microscope coordinates increase in opposite direction to pixel coordinates)
            # Negative sign because pixel X increases RIGHT but microscope X increases LEFT
            # Negative sign because pixel Y increases DOWN but microscope Y increases UP
            dx_pixels = -dx_um / um_per_pixel_x if um_per_pixel_x != 0 else 0
            dy_pixels = -dy_um / um_per_pixel_y if um_per_pixel_y != 0 else 0
            
            logger.debug(f"Coordinate conversion: Microscope({img_x}, {img_y})μm -> Offset({dx_um}, {dy_um})μm -> Pixels({dx_pixels}, {dy_pixels})px")
            
            # Calculate canvas coordinates
            x = int(ruler_width + img.width / 2 + dx_pixels)  # Adjust for ruler offset
            y = int(img.height / 2 + dy_pixels)
            
            logger.debug(f"Image {os.path.basename(img_data['path'])}: Pos({img_x}, {img_y})μm -> Canvas({x}, {y})px")
            
            # Skip if outside the image bounds
            if x < ruler_width or x >= new_width or y < 0 or y >= img.height:
                continue
            
            # Determine color based on magnification if available
            mag = "Unknown"
            crosshair_color = (255, 0, 0)  # Default red
            
            if "metadata" in img_data and hasattr(img_data["metadata"], "magnification"):
                mag = img_data["metadata"].magnification
            elif "metadata_dict" in img_data:
                mag = img_data.get("metadata_dict", {}).get("magnification", "Unknown")
            
            # Use different colors for different magnification ranges
            try:
                mag_value = float(str(mag).replace('x', '').strip())
                if mag_value < 100:
                    crosshair_color = (0, 128, 0)  # Green for very low mag
                elif mag_value < 500:
                    crosshair_color = (0, 0, 255)  # Blue for low mag
                elif mag_value < 1000:
                    crosshair_color = (255, 128, 0)  # Orange for medium mag
                else:
                    crosshair_color = (255, 0, 0)  # Red for high mag
            except (ValueError, TypeError):
                # Keep default color if can't determine mag
                pass
            
            # Draw a more visible crosshair
            crosshair_size = 25  # Increased size
            crosshair_width = 3  # Increased width
            
            # Add center coordinates annotation on the image
            if x == int(ruler_width + img.width / 2) and y == int(img.height / 2):
                # This is the center point - add microscope coordinates
                center_label = f"Center: ({overview_stage_x}, {overview_stage_y})μm"
                center_label_x = x + crosshair_size + 10
                center_label_y = y + crosshair_size + 10
                
                # Add background for the center coordinates label
                center_text_bbox = draw.textbbox((center_label_x, center_label_y), center_label, font=font)
                draw.rectangle(center_text_bbox, fill=(0, 0, 0, 128))
                
                # Draw the center coordinates label
                draw.text(
                    (center_label_x, center_label_y),
                    center_label,
                    fill=(0, 255, 255),  # Cyan for visibility
                    font=font
                )
            
            # Draw a crosshair (horizontal and vertical lines)
            draw.line(
                [(x - crosshair_size, y), (x + crosshair_size, y)],
                fill=crosshair_color,
                width=crosshair_width
            )
            draw.line(
                [(x, y - crosshair_size), (x, y + crosshair_size)],
                fill=crosshair_color,
                width=crosshair_width
            )
            
            # Draw a circle at the center
            circle_radius = 8  # Increased radius
            draw.ellipse(
                [(x - circle_radius, y - circle_radius), (x + circle_radius, y + circle_radius)],
                outline=crosshair_color,
                width=crosshair_width
            )
            
            # Add a label with image number and filename
            image_count += 1
            filename = os.path.basename(img_data["path"])
            # Truncate filename if too long
            if len(filename) > 15:
                filename = filename[:12] + "..."
            
            # Create label with number and filename
            label = f"{image_count}: {filename}"
            
            # Calculate label position to avoid overlapping with crosshair
            label_x = x + crosshair_size + 5
            label_y = y - crosshair_size - 5
            
            # Add background for the label to make it more visible
            text_bbox = draw.textbbox((label_x, label_y), label, font=font)
            draw.rectangle(text_bbox, fill=(0, 0, 0, 128))
            
            # Draw the label
            draw.text(
                (label_x, label_y),
                label,
                fill=(255, 255, 0),  # Yellow for visibility
                font=font
            )
            
            logger.debug(f"Marked session image {image_count}: {os.path.basename(img_data['path'])}")
        
        if image_count > 0:
            logger.info(f"Marked {image_count} session image locations on the overview")
        else:
            logger.warning("No session image locations could be marked on the overview")
        
        return new_img
    
    def _generate_caption(self, collection):
        """
        Generate a caption for the annotated overview image.
        
        Args:
            collection: Collection data
            
        Returns:
            str: Caption text
        """
        # Get session information
        session_id = "Unknown"
        sample_id = "Unknown"
        client_id = ""
        tcl_id = ""
        operator = ""
        
        if self.session_manager and self.session_manager.current_session:
            session_id = os.path.basename(self.session_manager.session_folder)
            sample_id = self.session_manager.current_session.sample_id or "Unknown"
            client_id = self.session_manager.current_session.client_sample_id or ""
            tcl_id = self.session_manager.current_session.tcl_sample_id or ""
            operator = self.session_manager.current_session.operator_name or ""
        
        # Get image information
        image_info = "No image data available"
        if collection and "images" in collection and collection["images"]:
            img_data = collection["images"][0]
            metadata_dict = img_data["metadata_dict"]
            
            magnification = metadata_dict.get("magnification", "Unknown")
            working_distance = metadata_dict.get("working_distance_mm", "Unknown")
            high_voltage = metadata_dict.get("high_voltage_kV", "Unknown")
            detector = metadata_dict.get("detector", metadata_dict.get("mode", "Unknown"))
            
            image_info = f"Magnification: {magnification}x, Working Distance: {working_distance} mm, "
            image_info += f"High Voltage: {high_voltage} kV, Detector: {detector}"
        
        # Build caption
        caption = f"Annotated overview image for Sample: {sample_id}\n\n"
        
        if client_id:
            caption += f"Client ID: {client_id}\n"
        
        if tcl_id:
            caption += f"TCL ID: {tcl_id}\n"
        
        caption += f"Session: {session_id}\n"
        
        if operator:
            caption += f"Operator: {operator}\n"
        
        caption += f"\nImage Details:\n{image_info}\n\n"
        
        # Add timestamp
        caption += f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}"
        
        return caption
