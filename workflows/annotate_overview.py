"""
AnnotateOverview workflow implementation for SEM Image Workflow Manager.
Creates annotated overview images with metadata data bar.
"""

import os
import datetime
import math
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from utils.logger import Logger
from workflows.workflow_base import WorkflowBase

logger = Logger(__name__)


class AnnotateOverviewWorkflow(WorkflowBase):
    """Implementation of the AnnotateOverview workflow."""
    
    def __init__(self, session_manager):
        """Initialize the workflow with session manager."""
        super().__init__(session_manager)
        
    def _get_font(self, size=12):
        """Get a font with robust fallback strategy.
        
        Args:
            size: Font size in points
            
        Returns:
            PIL.ImageFont: The loaded font or a default font
        """
        # Try standard fonts in order of preference
        font_names = [
            "arial.ttf",
            "Arial.ttf",
            "Helvetica.ttf", 
            "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf"
        ]
        
        # Try OS-specific font paths
        font_paths = []
        
        if sys.platform == "win32":
            font_paths = [
                "C:\\Windows\\Fonts",
                os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Fonts")
            ]
        elif sys.platform == "darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]
        else:  # Linux and others
            font_paths = [
                "/usr/share/fonts/truetype",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.local/share/fonts")
            ]
            
        # Try all combinations of paths and font names
        for path in font_paths:
            if os.path.exists(path):
                for font_name in font_names:
                    font_path = os.path.join(path, font_name)
                    try:
                        return ImageFont.truetype(font_path, size)
                    except IOError:
                        continue
        
        # Try direct font names (may work if fonts are in system path)
        for font_name in font_names:
            try:
                return ImageFont.truetype(font_name, size)
            except IOError:
                continue
                
        # Last resort: use default font
        logger.warning(f"Could not load any TrueType fonts, using default font")
        return ImageFont.load_default()
    
    def name(self):
        """Get workflow name."""
        return "AnnotateOverview"
    
    def description(self):
        """Get workflow description."""
        return "Create annotated overview images with metadata data bar"
    
    def discover_collections(self):
        """Discover and create collections."""
        self.collections = []
        
        if not self.session_manager or not self.session_manager.current_session:
            logger.warning("No session available for AnnotateOverview collection discovery")
            return self.collections
        
        # Get the session folder
        session_folder = self.session_manager.session_folder
        if not session_folder or not os.path.exists(session_folder):
            logger.warning(f"Session folder does not exist: {session_folder}")
            return self.collections
        
        # Find Stitch folders
        stitch_folders = []
        self._find_stitch_folders(session_folder, stitch_folders)
        
        # Find overview images
        overview_images = []
        for stitch_folder in stitch_folders:
            self._find_overview_images(stitch_folder, overview_images)
        
        # Create collection if we found overview images
        if overview_images:
            collection_images = []
            
            for img_data in overview_images:
                img_path = img_data["path"]
                metadata_dict = {}
                
                if self.session_manager.metadata and img_path in self.session_manager.metadata:
                    metadata = self.session_manager.metadata[img_path]
                    if metadata and metadata.is_valid():
                        metadata_dict = metadata.to_dict()
                else:
                    filename = os.path.basename(img_path)
                    logger.warning(f"No valid metadata found for {filename}, using fallback values")
                    metadata_dict = {
                        "image_path": img_path,
                        "filename": filename,
                        "acquisition_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                
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
        
        return self.collections
    
    def _find_stitch_folders(self, root_folder, stitch_folders):
        """Find folders containing 'Stitch' in name."""
        try:
            for item in os.listdir(root_folder):
                full_path = os.path.join(root_folder, item)
                if os.path.isdir(full_path):
                    if "stitch" in item.lower():
                        stitch_folders.append(full_path)
                    self._find_stitch_folders(full_path, stitch_folders)
        except Exception as e:
            logger.error(f"Error searching for stitch folders: {str(e)}")
    
    def _find_overview_images(self, stitch_folder, overview_images):
        """Find overview images in stitch folder."""
        try:
            for root, dirs, files in os.walk(stitch_folder):
                for file in files:
                    if "-Overview.tiff" in file:
                        img_path = os.path.join(root, file)
                        overview_images.append({
                            "path": img_path,
                            "is_overview": True
                        })
        except Exception as e:
            logger.error(f"Error searching for overview images: {str(e)}")
    
    def create_grid(self, collection, layout=None, options=None):
        """Create annotated overview image."""
        if not collection or "images" not in collection or not collection["images"]:
            return None
        
        # Check for multiple images and use the first one
        if len(collection["images"]) > 1:
            logger.warning(f"Multiple overview images found ({len(collection['images'])}), using only the first one")
            
        # Get image and metadata from the first image
        image_data = collection["images"][0]
        image_path = image_data["path"]
        metadata_dict = image_data["metadata_dict"]
        
        # Default options
        if options is None:
            options = {
                "annotations": [],
                "include_data_bar": True,
                "mark_session_images": True,
                "selected_locations": None,
                "rotation_direction": 1  # Default to CCW
            }
        
        try:
            # Load image
            img = Image.open(image_path).copy()
            
            # Mark session images
            if options.get("mark_session_images", True):
                img = self._mark_session_image_locations(img, image_path, options.get("selected_locations"), options)
            
            # Apply annotations
            if options.get("annotations"):
                img = self._apply_annotations(img, options["annotations"])
            
            # Add data bar
            if options.get("include_data_bar", True):
                img = self._add_data_bar(img, metadata_dict)
            
            return img
        except Exception as e:
            logger.error(f"Error creating annotated image: {str(e)}")
            return None
    
    def _apply_annotations(self, img, annotations):
        """Apply annotations to image."""
        draw = ImageDraw.Draw(img)
        
        # Try to load font with robust fallback
        font = self._get_font(14)
        
        # Apply each annotation
        for annotation in annotations:
            annotation_type = annotation.get("type")
            
            if annotation_type == "arrow":
                self._draw_arrow(draw, annotation, font)
            elif annotation_type == "text":
                self._draw_text(draw, annotation, font)
            elif annotation_type == "circle":
                self._draw_circle(draw, annotation)
            elif annotation_type == "rectangle":
                self._draw_rectangle(draw, annotation)
        
        return img
    
    def _draw_arrow(self, draw, annotation, font):
        """Draw arrow annotation."""
        start = annotation.get("start", (0, 0))
        end = annotation.get("end", (100, 100))
        color = annotation.get("color", (255, 0, 0))
        width = annotation.get("width", 2)
        
        # Draw line
        draw.line([start, end], fill=color, width=width)
        
        # Draw arrowhead
        arrow_head_size = width * 3
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = (dx**2 + dy**2)**0.5
        
        if length > 0:
            udx = dx / length
            udy = dy / length
            
            perp_x = -udy * arrow_head_size
            perp_y = udx * arrow_head_size
            
            point1 = (end[0] - udx * arrow_head_size + perp_x, 
                      end[1] - udy * arrow_head_size + perp_y)
            point2 = (end[0] - udx * arrow_head_size - perp_x, 
                      end[1] - udy * arrow_head_size - perp_y)
            
            draw.polygon([end, point1, point2], fill=color)
    
    def _draw_text(self, draw, annotation, font):
        """Draw text annotation."""
        position = annotation.get("position", (0, 0))
        text = annotation.get("text", "")
        color = annotation.get("color", (255, 0, 0))
        bg_color = annotation.get("background_color", None)
        
        if bg_color:
            text_bbox = draw.textbbox(position, text, font=font)
            draw.rectangle(text_bbox, fill=bg_color)
        
        draw.text(position, text, fill=color, font=font)
    
    def _draw_circle(self, draw, annotation):
        """Draw circle annotation."""
        center = annotation.get("center", (0, 0))
        radius = annotation.get("radius", 20)
        color = annotation.get("color", (255, 0, 0))
        width = annotation.get("width", 2)
        fill = annotation.get("fill", None)
        
        bbox = [
            center[0] - radius, center[1] - radius,
            center[0] + radius, center[1] + radius
        ]
        
        draw.ellipse(bbox, outline=color, width=width, fill=fill)
    
    def _draw_rectangle(self, draw, annotation):
        """Draw rectangle annotation."""
        top_left = annotation.get("top_left", (0, 0))
        bottom_right = annotation.get("bottom_right", (100, 100))
        color = annotation.get("color", (255, 0, 0))
        width = annotation.get("width", 2)
        fill = annotation.get("fill", None)
        
        draw.rectangle([top_left, bottom_right], outline=color, width=width, fill=fill)
    
    def _add_data_bar(self, img, metadata_dict):
        """Add data bar to image."""
        data_bar_height = 30
        margin = 10
        
        # Create new image
        new_img = Image.new('RGB', (img.width, img.height + data_bar_height), color='black')
        new_img.paste(img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        
        # Try to load font with robust fallback
        font = self._get_font(12)
        
        # Get metadata
        magnification = metadata_dict.get("magnification", "")
        working_distance = metadata_dict.get("working_distance_mm", "")
        high_voltage = metadata_dict.get("high_voltage_kV", "")
        detector = metadata_dict.get("detector", metadata_dict.get("mode", ""))
        acquisition_date = metadata_dict.get("acquisition_date", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        # Get scale
        fov_width = metadata_dict.get("field_of_view_width", 0)
        scale_text = ""
        if fov_width:
            if fov_width >= 1000:
                scale_text = f"{fov_width/1000:.1f} mm"
            else:
                scale_text = f"{fov_width:.0f} μm"
        
        # Get session/sample info
        session_id = "Unknown"
        sample_id = "Unknown"
        if self.session_manager and self.session_manager.current_session:
            session_id = os.path.basename(self.session_manager.session_folder)
            sample_id = self.session_manager.current_session.sample_id or "Unknown"
        
        # Data bar text
        info_text = f"Mag. (Pol) {magnification}× | FW {working_distance} mm | HV {high_voltage} kV | Int. Image | Det. {detector}"
        filename = os.path.basename(metadata_dict.get("image_path", ""))
        identifier = f"{session_id} {filename}"
        
        # Draw data bar
        info_x = img.width // 3
        timestamp_x = 2 * img.width // 3
        
        # Draw scale bar
        if fov_width:
            scale_bar_width = img.width // 5
            scale_bar_y = img.height + (data_bar_height // 2)
            scale_bar_x = margin
            
            draw.line([(scale_bar_x, scale_bar_y), (scale_bar_x + scale_bar_width, scale_bar_y)],
                     fill=(255, 255, 255), width=2)
            
            draw.text((scale_bar_x, scale_bar_y + 5), scale_text,
                     fill=(255, 255, 255), font=font, anchor="lt")
        
        # Draw metadata
        draw.text((info_x, img.height + (data_bar_height // 2)), info_text,
                 fill=(255, 255, 255), font=font, anchor="mm")
        
        # Draw timestamp
        draw.text((timestamp_x, img.height + (data_bar_height // 2)),
                 f"{acquisition_date} {identifier}", fill=(255, 255, 255),
                 font=font, anchor="mm")
        
        return new_img
    
    def export_grid(self, grid_image, collection):
        """Export annotated image."""
        try:
            # Get session info
            session_id = "Unknown"
            sample_id = "Unknown"
            client_id = ""
            
            if self.session_manager and self.session_manager.current_session:
                session_id = os.path.basename(self.session_manager.session_folder)
                sample_id = self.session_manager.current_session.sample_id or "Unknown"
                client_id = self.session_manager.current_session.client_sample_id or ""
            
            # Sanitize IDs
            for char in [':', '*', '?', '"', '<', '>', '|', '/', '\\']:
                session_id = session_id.replace(char, '_')
                sample_id = sample_id.replace(char, '_')
                client_id = client_id.replace(char, '_')
            
            # Filename
            filename = f"{session_id}_{sample_id}_{client_id}_AnnotatedOverview"
            
            # Find project folder
            if self.session_manager and self.session_manager.session_folder:
                project_folder = os.path.dirname(self.session_manager.session_folder)
            elif self.workflow_folder:
                project_folder = self.workflow_folder
            else:
                import tempfile
                project_folder = tempfile.gettempdir()
            
            # Create output folder
            annotated_folder = os.path.join(project_folder, "Annotated")
            if not os.path.exists(annotated_folder):
                os.makedirs(annotated_folder)
            
            # Save files
            image_path = os.path.join(annotated_folder, f"{filename}.tiff")
            caption_path = os.path.join(annotated_folder, f"{filename}.txt")
            
            grid_image.save(image_path, format="TIFF")
            
            with open(caption_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_caption(collection))
            
            return image_path, caption_path
            
        except Exception as e:
            logger.exception(f"Error exporting: {str(e)}")
            raise Exception(f"Failed to export: {str(e)}")
    
    def _generate_caption(self, collection):
        """Generate caption for the image."""
        if not collection or "images" not in collection:
            return "No image data available"
            
        # Get metadata from the first image (may be multiple)
        if len(collection["images"]) > 1:
            logger.info(f"Multiple overview images found ({len(collection['images'])}), using metadata from the first one for caption")
            
        metadata_dict = collection["images"][0]["metadata_dict"]
        
        # Get session info
        session_id = "Unknown"
        sample_id = "Unknown" 
        if self.session_manager and self.session_manager.current_session:
            session_id = os.path.basename(self.session_manager.session_folder)
            sample_id = self.session_manager.current_session.sample_id or "Unknown"
        
        # Generate caption
        caption = f"Annotated overview image for Sample: {sample_id}\n\n"
        caption += f"Session: {session_id}\n\n"
        
        # Add image details
        mag = metadata_dict.get("magnification", "Unknown")
        wd = metadata_dict.get("working_distance_mm", "Unknown")
        hv = metadata_dict.get("high_voltage_kV", "Unknown")
        det = metadata_dict.get("detector", metadata_dict.get("mode", "Unknown"))
        
        caption += f"Image Details:\n"
        caption += f"Magnification: {mag}x, Working Distance: {wd} mm, "
        caption += f"High Voltage: {hv} kV, Detector: {det}\n\n"
        
        # Add timestamp
        caption += f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}"
        
        return caption
        
    def _mark_session_image_locations(self, img, overview_path, selected_locations=None, options=None):
        """Mark session image locations on overview image using template matching."""
        if not self.session_manager or not self.session_manager.metadata:
            return img
            
        # Create copy and drawing context
        new_img = img.copy()
        draw = ImageDraw.Draw(new_img)
        
        # Load font with robust fallback
        font = self._get_font(16)
                
        # Get options
        rotation_direction = options.get("rotation_direction", 1)  # 1=CCW, -1=CW
        confidence_threshold = options.get("confidence_threshold", 0.0)  # Default to no threshold
        log_function = options.get("log_function", lambda msg: logger.info(msg))  # Default to logger.info
        
        # Store match results
        match_results = {}
        
        # Get overview parameters
        pixel_width_um = 1.0  # Default
        scan_rotation = 0.0    # Default
        
        # Check metadata
        if overview_path in self.session_manager.metadata:
            md = self.session_manager.metadata[overview_path]
            
            # Get rotation
            if hasattr(md, 'scan_rotation'):
                scan_rotation = md.scan_rotation
                logger.info(f"Using scan rotation: {scan_rotation} degrees")
                log_function(f"Overview scan rotation: {scan_rotation}° (applying {scan_rotation * rotation_direction}° rotation)")
                
            # Get pixel width
            if hasattr(md, 'pixel_width'):
                pixel_width = md.pixel_width
                if isinstance(pixel_width, str):
                    try:
                        parts = pixel_width.split()
                        if len(parts) >= 2:
                            value = float(parts[0])
                            unit = parts[1]
                            
                            if "nm" in unit:
                                pixel_width_um = value / 1000  # nm to μm
                            elif "μm" in unit or "um" in unit:
                                pixel_width_um = value
                            elif "mm" in unit:
                                pixel_width_um = value * 1000  # mm to μm
                    except Exception:
                        pass
        
        # Convert to OpenCV for template matching
        overview_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Apply rotation if needed
        if scan_rotation != 0:
            effective_angle = scan_rotation * rotation_direction
            logger.info(f"Using rotation angle: {scan_rotation}° (direction: {'CCW' if rotation_direction == 1 else 'CW'} = {effective_angle}°)")
            
            height, width = overview_cv.shape[:2]
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, -effective_angle, 1.0)
            overview_cv = cv2.warpAffine(
                overview_cv, 
                rotation_matrix, 
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255)
            )
            
        # Get session images
        session_images = []
        for img_path, metadata in self.session_manager.metadata.items():
            # Skip overview and invalid metadata
            if img_path == overview_path or not metadata or not metadata.is_valid():
                continue
                
            # Add to list if it has position info
            if hasattr(metadata, 'sample_position_x') and hasattr(metadata, 'sample_position_y'):
                session_images.append({
                    "path": img_path,
                    "metadata": metadata
                })
                
        # Filter by selected locations
        filtered_images = []
        if selected_locations:
            for idx in selected_locations:
                if 0 <= idx < len(session_images):
                    filtered_images.append(session_images[idx])
        else:
            filtered_images = session_images
            
        # Process images
        image_count = 0
        for img_data in filtered_images:
            session_path = img_data["path"]
            
            try:
                # Load session image
                session_cv = cv2.imread(session_path)
                if session_cv is None:
                    continue
                    
                # Crop to remove data bar (1920x1080)
                try:
                    h, w = session_cv.shape[:2]
                    if h > 1080 and w >= 1920:
                        logger.info(f"Cropping {os.path.basename(session_path)} from {w}x{h} to 1920x1080")
                        session_cv = session_cv[0:1080, 0:1920]
                    elif h > 0 and w > 0:
                        logger.debug(f"Image size {w}x{h} for {os.path.basename(session_path)}, no crop needed")
                    else:
                        logger.warning(f"Invalid image dimensions: {w}x{h} for {os.path.basename(session_path)}")
                        continue
                except Exception as e:
                    logger.error(f"Error cropping image {os.path.basename(session_path)}: {str(e)}")
                    continue
                    
                # Get session pixel width
                session_pixel_width_um = pixel_width_um  # Default
                if hasattr(img_data["metadata"], "pixel_dimension_nm"):
                    session_pixel_width_nm = img_data["metadata"].pixel_dimension_nm
                    session_pixel_width_um = session_pixel_width_nm / 1000  # nm to μm
                    
                # Calculate scale
                scale_factor = 1.0
                if session_pixel_width_um > 0 and pixel_width_um > 0:
                    scale_factor = session_pixel_width_um / pixel_width_um
                    logger.info(f"Using scale factor: {scale_factor:.2f} for {os.path.basename(session_path)}")
                else:
                    logger.warning(f"Invalid pixel dimensions for scaling: overview={pixel_width_um}μm, session={session_pixel_width_um}μm. Using default scale of 1.0.")
                    
                # Resize session image
                if scale_factor != 1.0:
                    try:
                        new_width = int(session_cv.shape[1] / scale_factor)
                        new_height = int(session_cv.shape[0] / scale_factor)
                        if new_width > 0 and new_height > 0:
                            logger.debug(f"Resizing {os.path.basename(session_path)} from {session_cv.shape[1]}x{session_cv.shape[0]} to {new_width}x{new_height}")
                            session_cv = cv2.resize(session_cv, (new_width, new_height), interpolation=cv2.INTER_AREA)
                        else:
                            logger.warning(f"Invalid resize dimensions: {new_width}x{new_height}, using original size")
                    except Exception as e:
                        logger.error(f"Error resizing image {os.path.basename(session_path)}: {str(e)}")
                        
                # Perform template matching
                match_result = cv2.matchTemplate(overview_cv, session_cv, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_result)

                # Calculate match position
                top_left = max_loc
                match_width = session_cv.shape[1]
                match_height = session_cv.shape[0]
                match_center_x = top_left[0] + match_width // 2
                match_center_y = top_left[1] + match_height // 2
                
                # Log match confidence
                confidence_msg = f"Match for {os.path.basename(session_path)}: confidence={max_val:.3f}"
                if max_val < 0.8:
                    confidence_msg += " (Low confidence)"
                    logger.warning(f"Low confidence match ({max_val:.3f}) for {os.path.basename(session_path)}")
                elif max_val >= 0.9:
                    confidence_msg += " (Excellent match)"
                    logger.info(f"Strong match ({max_val:.3f}) for {os.path.basename(session_path)}")
                else:
                    confidence_msg += " (Good match)"
                    logger.info(f"Good match ({max_val:.3f}) for {os.path.basename(session_path)}")
                    
                log_function(confidence_msg)
                
                # Store match result
                match_results[session_path] = {
                    "confidence": max_val,
                    "center_x": match_center_x,
                    "center_y": match_center_y,
                    "top_left": top_left,
                    "width": match_width,
                    "height": match_height
                }
                
                # Skip if below threshold (if threshold is provided)
                if confidence_threshold > 0 and max_val < confidence_threshold:
                    log_function(f"Skipping {os.path.basename(session_path)} - below threshold ({max_val:.3f} < {confidence_threshold})")
                    continue
                
                # Get color based on magnification
                crosshair_color = (255, 0, 0)  # Default red
                if hasattr(img_data["metadata"], "magnification"):
                    try:
                        mag_value = float(str(img_data["metadata"].magnification).replace('x', '').strip())
                        if mag_value < 100:
                            crosshair_color = (0, 128, 0)  # Green for low mag
                        elif mag_value < 500:
                            crosshair_color = (0, 0, 255)  # Blue for medium mag
                        elif mag_value < 1000:
                            crosshair_color = (255, 128, 0)  # Orange for high mag
                    except (ValueError, TypeError):
                        pass
                        
                # Draw crosshair
                crosshair_size = 25
                crosshair_width = 3
                
                # Horizontal line
                draw.line(
                    [(match_center_x - crosshair_size, match_center_y), 
                     (match_center_x + crosshair_size, match_center_y)],
                    fill=crosshair_color,
                    width=crosshair_width
                )
                
                # Vertical line
                draw.line(
                    [(match_center_x, match_center_y - crosshair_size), 
                     (match_center_x, match_center_y + crosshair_size)],
                    fill=crosshair_color,
                    width=crosshair_width
                )
                
                # Center circle
                circle_radius = 8
                draw.ellipse(
                    [(match_center_x - circle_radius, match_center_y - circle_radius),
                     (match_center_x + circle_radius, match_center_y + circle_radius)],
                    outline=crosshair_color,
                    width=crosshair_width
                )
                
                # Add label
                image_count += 1
                filename = os.path.basename(session_path)
                if len(filename) > 15:
                    filename = filename[:12] + "..."
                    
                label = f"{image_count}: {filename}"
                label_x = match_center_x + crosshair_size + 5
                label_y = match_center_y - crosshair_size - 5
                
                # Add background for label
                text_bbox = draw.textbbox((label_x, label_y), label, font=font)
                draw.rectangle(text_bbox, fill=(0, 0, 0, 128))
                
                # Draw label
                draw.text(
                    (label_x, label_y),
                    label,
                    fill=(255, 255, 0),  # Yellow
                    font=font
                )
                
                logger.info(f"Marked session image {image_count}: {filename} at ({match_center_x}, {match_center_y})")
                
            except Exception as e:
                logger.error(f"Error processing {os.path.basename(session_path)}: {str(e)}")
                
        # Store match results in options if provided
        if options and "match_results" in options:
            options["match_results"].update(match_results)
            
        # Calculate average confidence
        confidence_values = [result["confidence"] for result in match_results.values()]
        if confidence_values:
            avg_confidence = sum(confidence_values) / len(confidence_values)
            log_function(f"Average match confidence: {avg_confidence:.3f} (across {len(confidence_values)} images)")
        
        return new_img
