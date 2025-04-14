import os
import cv2
import math
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import argparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def template_match_session_images(overview_path, session_image_paths, rotation_direction=1, show_results=False):
    """
    Perform template matching to find session images within an overview image.
    
    Args:
        overview_path: Path to the overview image
        session_image_paths: List of paths to session images
        rotation_direction: Direction of rotation (1 for CCW, -1 for CW)
        show_results: Whether to display results visually
        
    Returns:
        List of match results with coordinates and confidence scores
    """
    # Load overview image
    overview_img = cv2.imread(overview_path)
    if overview_img is None:
        logger.error(f"Failed to load overview image: {overview_path}")
        return []
        
    # Store results
    match_results = []
    
    # Create a visualization image if needed
    if show_results:
        vis_img = overview_img.copy()
    
    # Process each session image
    for session_path in session_image_paths:
        logger.info(f"Processing session image: {os.path.basename(session_path)}")
        
        try:
            # Load session image
            session_img = cv2.imread(session_path)
            if session_img is None:
                logger.error(f"Failed to load session image: {session_path}")
                continue
                
            # Crop to remove data bar (assuming 1920x1080 resolution)
            h, w = session_img.shape[:2]
            if h > 1080 and w >= 1920:
                session_img = session_img[0:1080, 0:1920]
                logger.info(f"Cropped session image to 1920x1080")
            
            # Calculate appropriate scaling
            # In a real implementation, this would be derived from metadata
            # Here we're using a simple heuristic
            scale_factor = 0.25  # This would be derived from metadata in the real app
            
            # Resize session image to match expected scale in overview
            new_width = int(session_img.shape[1] * scale_factor)
            new_height = int(session_img.shape[0] * scale_factor)
            if new_width > 0 and new_height > 0:
                session_img = cv2.resize(session_img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.info(f"Resized session image to {new_width}x{new_height} (scale:{scale_factor})")
            
            # If rotation is needed (would be from metadata in real app)
            rotation_angle = 30  # Example angle, would be from metadata
            
            # Apply rotation direction
            effective_angle = rotation_angle * rotation_direction
            logger.info(f"Using rotation angle: {rotation_angle}° with direction: {'CCW' if rotation_direction == 1 else 'CW'} = {effective_angle}°")
            
            # Perform template matching
            match_result = cv2.matchTemplate(overview_img, session_img, cv2.TM_CCOEFF_NORMED)
            
            # Find best match
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_result)
            
            # Top-left corner of match
            top_left = max_loc
            match_confidence = max_val
            
            # Calculate center of matched region
            match_center_x = top_left[0] + session_img.shape[1] // 2
            match_center_y = top_left[1] + session_img.shape[0] // 2
            
            logger.info(f"Template match found at ({match_center_x}, {match_center_y}) with confidence {match_confidence:.3f}")
            
            # Store match result
            match_results.append({
                "path": session_path,
                "match_x": match_center_x,
                "match_y": match_center_y,
                "confidence": match_confidence,
                "top_left": top_left,
                "width": session_img.shape[1],
                "height": session_img.shape[0]
            })
            
            # Draw results if requested
            if show_results:
                # Draw bounding box
                bottom_right = (top_left[0] + session_img.shape[1], top_left[1] + session_img.shape[0])
                cv2.rectangle(vis_img, top_left, bottom_right, (0, 255, 0), 2)
                
                # Draw center point
                cv2.circle(vis_img, (match_center_x, match_center_y), 5, (0, 0, 255), -1)
                
                # Add confidence text
                cv2.putText(vis_img, f"{match_confidence:.3f}", 
                           (top_left[0], top_left[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        except Exception as e:
            logger.error(f"Error processing {os.path.basename(session_path)}: {str(e)}")
    
    # Show results if requested
    if show_results and match_results:
        plt.figure(figsize=(12, 10))
        plt.imshow(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB))
        plt.title(f"Template Matching Results - {len(match_results)} matches")
        plt.axis('off')
        plt.tight_layout()
        plt.show()
    
    return match_results

def validate_coordinates_with_metadata(match_results, metadata, overview_metadata, rotation_direction=1):
    """
    Validate template matching results against metadata coordinates.
    
    Args:
        match_results: List of template match results
        metadata: Dict of session image metadata keyed by path
        overview_metadata: Metadata for the overview image
        rotation_direction: Direction of rotation (1 for CCW, -1 for CW)
        
    Returns:
        List of validated match results with both matched and expected coordinates
    """
    validated_results = []
    
    # Get overview parameters from metadata
    overview_center_x = overview_metadata.get("sample_position_x", 0) * 1000000  # Convert to micrometers
    overview_center_y = overview_metadata.get("sample_position_y", 0) * 1000000  # Convert to micrometers
    
    # Get pixel dimensions from overview metadata
    um_per_pixel_x = overview_metadata.get("pixel_width_um", 1)
    um_per_pixel_y = um_per_pixel_x  # Assuming square pixels unless specified otherwise
    
    # Get overview dimensions
    overview_width = overview_metadata.get("width", 0)
    overview_height = overview_metadata.get("height", 0)
    
    # Get scan rotation
    scan_rotation = overview_metadata.get("scan_rotation", 0) 
    rotation_angle_rad = math.radians(scan_rotation * rotation_direction)
    
    logger.info(f"Overview center: ({overview_center_x}, {overview_center_y})μm")
    logger.info(f"Pixel size: {um_per_pixel_x}μm/pixel")
    logger.info(f"Scan rotation: {scan_rotation}° (direction: {'CCW' if rotation_direction == 1 else 'CW'}, {rotation_angle_rad} radians)")
    
    # Process each match result
    for match in match_results:
        # Get image path
        img_path = match["path"]
        
        # Skip if no metadata available
        if img_path not in metadata:
            logger.warning(f"No metadata available for {os.path.basename(img_path)}")
            continue
            
        img_metadata = metadata[img_path]
        
        # Get sample position from metadata (in micrometers)
        img_x = img_metadata.get("sample_position_x", 0) * 1000000  # Convert to micrometers 
        img_y = img_metadata.get("sample_position_y", 0) * 1000000  # Convert to micrometers
        
        # Calculate offset from overview center in micrometers
        dx_um = img_x - overview_center_x
        dy_um = img_y - overview_center_y
        
        # Apply rotation if needed
        if scan_rotation != 0:
            # Rotate the offset coordinates around (0,0) - with rotation direction
            rotated_dx = dx_um * math.cos(rotation_angle_rad) + dy_um * math.sin(rotation_angle_rad)
            rotated_dy = -dx_um * math.sin(rotation_angle_rad) + dy_um * math.cos(rotation_angle_rad)
            dx_um = rotated_dx
            dy_um = rotated_dy
            logger.info(f"Applied rotation ({scan_rotation}°), new offset: ({dx_um}, {dy_um})μm")
        
        # Convert to pixels
        dx_pixels = dx_um / um_per_pixel_x if um_per_pixel_x != 0 else 0
        dy_pixels = -dy_um / um_per_pixel_y if um_per_pixel_y != 0 else 0
        
        # Calculate expected canvas coordinates (from center of the image)
        expected_x = int(overview_width / 2 + dx_pixels)
        expected_y = int(overview_height / 2 + dy_pixels)
        
        # Calculate distance between expected and matched position
        matched_x = match["match_x"]
        matched_y = match["match_y"]
        
        # Calculate pixel distance
        distance_px = math.sqrt((expected_x - matched_x)**2 + (expected_y - matched_y)**2)
        
        # Calculate distance in micrometers
        distance_um = distance_px * um_per_pixel_x
        
        # Determine if match is valid
        is_valid = distance_px < 100  # Example threshold - 100 pixels
        
        # Add validation data to result
        validated_result = match.copy()
        validated_result.update({
            "expected_x": expected_x,
            "expected_y": expected_y,
            "distance_px": distance_px,
            "distance_um": distance_um,
            "is_valid": is_valid
        })
        
        validated_results.append(validated_result)
        
        logger.info(f"Image: {os.path.basename(img_path)}")
        logger.info(f"  Matched position: ({matched_x}, {matched_y})px")
        logger.info(f"  Expected position: ({expected_x}, {expected_y})px")
        logger.info(f"  Distance: {distance_px:.1f}px ({distance_um:.1f}μm)")
        logger.info(f"  Match is {'valid' if is_valid else 'invalid'}")
    
    return validated_results

def main():
    parser = argparse.ArgumentParser(description='Test template matching for session images in overview')
    parser.add_argument('--overview', required=True, help='Path to overview image')
    parser.add_argument('--sessions', required=True, nargs='+', help='Paths to session images')
    parser.add_argument('--rotation', type=int, default=1, choices=[-1, 1], 
                        help='Rotation direction (1=CCW, -1=CW)')
    parser.add_argument('--show', action='store_true', help='Show visual results')
    
    args = parser.parse_args()
    
    logger.info(f"Running template matching with rotation direction: {'CCW' if args.rotation == 1 else 'CW'}")
    
    # Run template matching
    match_results = template_match_session_images(
        args.overview, 
        args.sessions, 
        rotation_direction=args.rotation,
        show_results=args.show
    )
    
    # Print results
    logger.info(f"Found {len(match_results)} matches")
    for i, match in enumerate(match_results):
        logger.info(f"Match {i+1}: ({match['match_x']}, {match['match_y']}) - confidence: {match['confidence']:.3f}")

if __name__ == "__main__":
    main()
