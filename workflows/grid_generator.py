"""
Grid visualization generator for SEM Image Workflow Manager.
Handles image layout and processing for grid visualizations.
"""

from PIL import Image, ImageDraw, ImageFont
from utils.logger import Logger

logger = Logger(__name__)


class GridGenerator:
    """
    Utility class for creating grid visualizations of SEM images.
    """
    
    def __init__(self, spacing=4, background_color='white'):
        """
        Initialize grid generator.
        
        Args:
            spacing (int): Pixel spacing between grid cells
            background_color (str): Background color of the grid
        """
        self.spacing = spacing
        self.background_color = background_color
    
    def create_grid(self, images, layout=None, cell_size=None):
        """
        Create a grid visualization of images.
        
        Args:
            images (list): List of PIL.Image objects
            layout (tuple, optional): Grid layout as (rows, columns)
            cell_size (tuple, optional): Size of each grid cell as (width, height)
            
        Returns:
            PIL.Image: Grid visualization image
        """
        if not images:
            logger.error("No images provided for grid visualization")
            return None
        
        num_images = len(images)
        
        # Determine layout if not specified
        if not layout:
            if num_images <= 2:
                layout = (1, 2)  # 1 row, 2 columns
            elif num_images <= 4:
                layout = (2, 2)  # 2 rows, 2 columns
            else:
                layout = (3, 2)  # 3 rows, 2 columns
        
        rows, cols = layout
        
        # If there are more grid cells than images, adjust the layout
        if rows * cols > num_images:
            if cols > 1:
                cols = min(cols, num_images)
            rows = (num_images + cols - 1) // cols
        
        logger.info(f"Creating grid with layout {rows}x{cols} for {num_images} images")
        
        # Determine cell size if not specified
        if not cell_size:
            max_width = max(img.width for img in images)
            max_height = max(img.height for img in images)
            cell_size = (max_width, max_height)
        
        cell_width, cell_height = cell_size
        
        # Create a blank grid image with spacing
        grid_width = cols * cell_width + (cols - 1) * self.spacing
        grid_height = rows * cell_height + (rows - 1) * self.spacing
        grid_img = Image.new('RGB', (grid_width, grid_height), color=self.background_color)
        
        # Place images in the grid
        for i, img in enumerate(images):
            if i >= rows * cols:
                break  # Skip if we've filled all cells
                
            row = i // cols
            col = i % cols
            
            # Calculate position
            x = col * (cell_width + self.spacing)
            y = row * (cell_height + self.spacing)
            
            # Center the image in its cell
            x_offset = (cell_width - img.width) // 2
            y_offset = (cell_height - img.height) // 2
            
            # Paste the image
            grid_img.paste(img, (x + x_offset, y + y_offset))
        
        return grid_img
    
    def add_labels(self, grid_img, labels, layout, cell_size, position='top'):
        """
        Add text labels to a grid visualization.
        
        Args:
            grid_img (PIL.Image): Grid image to modify
            labels (list): List of label strings
            layout (tuple): Grid layout as (rows, columns)
            cell_size (tuple): Size of each grid cell as (width, height)
            position (str): Label position ('top', 'bottom', 'left', 'right')
            
        Returns:
            PIL.Image: Grid image with labels
        """
        if not grid_img or not labels:
            return grid_img
        
        rows, cols = layout
        cell_width, cell_height = cell_size
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Create a new image to accommodate labels
        padding = 20  # Padding for labels
        
        if position in ['top', 'bottom']:
            new_width = grid_img.width
            new_height = grid_img.height + padding
            
            if position == 'top':
                paste_y = padding
            else:  # bottom
                paste_y = 0
                
            new_img = Image.new('RGB', (new_width, new_height), color=self.background_color)
            new_img.paste(grid_img, (0, paste_y))
            
        else:  # left or right
            new_width = grid_img.width + padding
            new_height = grid_img.height
            
            if position == 'left':
                paste_x = padding
            else:  # right
                paste_x = 0
                
            new_img = Image.new('RGB', (new_width, new_height), color=self.background_color)
            new_img.paste(grid_img, (paste_x, 0))
        
        # Draw labels
        draw = ImageDraw.Draw(new_img)
        
        for i, label in enumerate(labels):
            if i >= rows * cols:
                break  # Skip if we've labeled all cells
                
            row = i // cols
            col = i % cols
            
            # Calculate label position
            if position == 'top':
                x = col * (cell_width + self.spacing) + cell_width // 2
                y = 0
            elif position == 'bottom':
                x = col * (cell_width + self.spacing) + cell_width // 2
                y = grid_img.height
            elif position == 'left':
                x = 0
                y = row * (cell_height + self.spacing) + cell_height // 2
            else:  # right
                x = grid_img.width
                y = row * (cell_height + self.spacing) + cell_height // 2
            
            # Draw text
            text_width, text_height = draw.textsize(label, font=font)
            
            if position in ['top', 'bottom']:
                text_x = x - text_width // 2
                text_y = y + (padding - text_height) // 2
            else:  # left or right
                text_x = x + (padding - text_width) // 2
                text_y = y - text_height // 2
            
            draw.text((text_x, text_y), label, fill=(0, 0, 0), font=font)
        
        return new_img
    
    def add_annotations(self, grid_img, annotations, layout, cell_size):
        """
        Add annotations (boxes, arrows, etc.) to a grid visualization.
        
        Args:
            grid_img (PIL.Image): Grid image to modify
            annotations (list): List of annotation dictionaries
            layout (tuple): Grid layout as (rows, columns)
            cell_size (tuple): Size of each grid cell as (width, height)
            
        Returns:
            PIL.Image: Grid image with annotations
        """
        if not grid_img or not annotations:
            return grid_img
        
        rows, cols = layout
        cell_width, cell_height = cell_size
        
        # Create a copy of the image to draw on
        annotated_img = grid_img.copy()
        draw = ImageDraw.Draw(annotated_img)
        
        # Process each annotation
        for annotation in annotations:
            annotation_type = annotation.get('type')
            cell_index = annotation.get('cell_index', 0)
            
            # Calculate cell position
            row = cell_index // cols
            col = cell_index % cols
            
            cell_x = col * (cell_width + self.spacing)
            cell_y = row * (cell_height + self.spacing)
            
            if annotation_type == 'box':
                # Draw a box
                box = annotation.get('box')
                color = annotation.get('color', (255, 0, 0))
                width = annotation.get('width', 2)
                
                x, y, w, h = box
                draw.rectangle(
                    [cell_x + x, cell_y + y, cell_x + x + w, cell_y + y + h],
                    outline=color,
                    width=width
                )
                
            elif annotation_type == 'text':
                # Draw text
                text = annotation.get('text', '')
                position = annotation.get('position', (0, 0))
                color = annotation.get('color', (0, 0, 0))
                
                try:
                    font_size = annotation.get('font_size', 10)
                    font = ImageFont.truetype("arial.ttf", font_size)
                except IOError:
                    font = ImageFont.load_default()
                
                x, y = position
                draw.text(
                    (cell_x + x, cell_y + y),
                    text,
                    fill=color,
                    font=font
                )
                
            elif annotation_type == 'line':
                # Draw a line
                start = annotation.get('start', (0, 0))
                end = annotation.get('end', (0, 0))
                color = annotation.get('color', (255, 0, 0))
                width = annotation.get('width', 2)
                
                start_x, start_y = start
                end_x, end_y = end
                
                draw.line(
                    [cell_x + start_x, cell_y + start_y, cell_x + end_x, cell_y + end_y],
                    fill=color,
                    width=width
                )
                
            elif annotation_type == 'arrow':
                # Draw an arrow (line with an arrowhead)
                start = annotation.get('start', (0, 0))
                end = annotation.get('end', (0, 0))
                color = annotation.get('color', (255, 0, 0))
                width = annotation.get('width', 2)
                
                start_x, start_y = start
                end_x, end_y = end
                
                # Draw the line
                draw.line(
                    [cell_x + start_x, cell_y + start_y, cell_x + end_x, cell_y + end_y],
                    fill=color,
                    width=width
                )
                
                # Draw the arrowhead
                self._draw_arrowhead(
                    draw,
                    (cell_x + end_x, cell_y + end_y),
                    (cell_x + start_x, cell_y + start_y),
                    color,
                    size=10
                )
        
        return annotated_img
    
    def _draw_arrowhead(self, draw, p2, p1, color, size=10):
        """
        Draw an arrowhead at p2 pointing from p1 to p2.
        
        Args:
            draw (PIL.ImageDraw): Drawing context
            p2 (tuple): End point (x, y)
            p1 (tuple): Start point (x, y)
            color (tuple): Arrow color (R, G, B)
            size (int): Arrowhead size
        """
        import math
        
        x2, y2 = p2
        x1, y1 = p1
        
        # Calculate the angle of the line
        angle = math.atan2(y2 - y1, x2 - x1)
        
        # Calculate the two points that form the arrowhead
        x3 = x2 - size * math.cos(angle - math.pi/6)
        y3 = y2 - size * math.sin(angle - math.pi/6)
        
        x4 = x2 - size * math.cos(angle + math.pi/6)
        y4 = y2 - size * math.sin(angle + math.pi/6)
        
        # Draw the arrowhead
        draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)
