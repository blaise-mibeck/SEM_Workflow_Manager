"""
Test script for template matching functionality.
This demonstrates the OpenCV template matching to find session images within an overview.
"""

import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import argparse
from PIL import Image

def test_template_match(overview_path, template_path, rotation_direction=1, rotation_angle=0):
    """
    Test template matching to find a session image in an overview image.
    
    Args:
        overview_path: Path to the overview image
        template_path: Path to the session image (template)
        rotation_direction: 1 for CCW, -1 for CW
        rotation_angle: Rotation angle in degrees
        
    Returns:
        Tuple of (max_loc, max_val) - the location and score of the best match
    """
    # Load the images
    overview_img = cv2.imread(overview_path)
    template_img = cv2.imread(template_path)
    
    if overview_img is None:
        raise ValueError(f"Failed to load overview image: {overview_path}")
    if template_img is None:
        raise ValueError(f"Failed to load template image: {template_path}")
    
    # Apply rotation to overview if needed
    if rotation_angle != 0:
        # Get image dimensions
        height, width = overview_img.shape[:2]
        # Calculate the center of the image
        center = (width // 2, height // 2)
        
        # Apply rotation direction to angle
        effective_angle = rotation_angle * rotation_direction
        print(f"Applying {effective_angle}° rotation to overview image "
              f"({'CCW' if rotation_direction == 1 else 'CW'})")
        
        # Create rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, effective_angle, 1.0)
        # Perform the rotation
        overview_img = cv2.warpAffine(overview_img, rotation_matrix, (width, height), 
                                      flags=cv2.INTER_LINEAR, 
                                      borderMode=cv2.BORDER_CONSTANT,
                                      borderValue=(255, 255, 255))
    
    # Crop the template to remove data bar if it's a session image
    h, w = template_img.shape[:2]
    if h > 1080 and w >= 1920:
        template_img = template_img[0:1080, 0:1920]
        print(f"Cropped template image to 1920x1080")
    
    # Resize template to match expected scale in overview
    # This would be calculated from metadata in a real application
    scale_factor = 0.25  # Example scale factor
    
    if scale_factor != 1.0:
        new_width = int(template_img.shape[1] * scale_factor)
        new_height = int(template_img.shape[0] * scale_factor)
        if new_width > 0 and new_height > 0:
            template_img = cv2.resize(template_img, (new_width, new_height), 
                                      interpolation=cv2.INTER_AREA)
            print(f"Resized template to {new_width}x{new_height} (scale: {scale_factor})")
    
    # Perform template matching
    result = cv2.matchTemplate(overview_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    # Find the best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    # Calculate the center of the matched region
    top_left = max_loc
    bottom_right = (top_left[0] + template_img.shape[1], top_left[1] + template_img.shape[0])
    center = (top_left[0] + template_img.shape[1]//2, top_left[1] + template_img.shape[0]//2)
    
    print(f"Best match at {center} with confidence {max_val:.3f}")
    
    # Display the result
    result_img = overview_img.copy()
    
    # Draw a rectangle around the matched region
    cv2.rectangle(result_img, top_left, bottom_right, (0, 255, 0), 2)
    
    # Draw the center point
    cv2.circle(result_img, center, 5, (0, 0, 255), -1)
    
    # Add text with match score
    cv2.putText(result_img, f"Score: {max_val:.3f}", 
                (top_left[0], top_left[1]-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Convert to RGB for matplotlib
    result_img_rgb = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
    
    # Create a figure with subplots
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    
    # Show the overview image
    axs[0].imshow(cv2.cvtColor(overview_img, cv2.COLOR_BGR2RGB))
    axs[0].set_title('Overview Image')
    axs[0].axis('off')
    
    # Show the template image
    axs[1].imshow(cv2.cvtColor(template_img, cv2.COLOR_BGR2RGB))
    axs[1].set_title('Template Image')
    axs[1].axis('off')
    
    # Show the result
    axs[2].imshow(result_img_rgb)
    axs[2].set_title(f'Match Result (Score: {max_val:.3f})')
    axs[2].axis('off')
    
    plt.tight_layout()
    plt.show()
    
    # Also show the heat map of the match result
    plt.figure(figsize=(8, 6))
    plt.imshow(result, cmap='hot')
    plt.colorbar()
    plt.title('Template Matching Result (Heat Map)')
    plt.show()
    
    return max_loc, max_val

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test template matching')
    parser.add_argument('--overview', required=True, help='Path to overview image')
    parser.add_argument('--template', required=True, help='Path to template image')
    parser.add_argument('--rotation', type=float, default=0, help='Rotation angle in degrees')
    parser.add_argument('--direction', type=int, default=1, choices=[-1, 1], 
                        help='Rotation direction (1=CCW, -1=CW)')
    
    args = parser.parse_args()
    
    # Run template matching test
    test_template_match(args.overview, args.template, args.direction, args.rotation)
