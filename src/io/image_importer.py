"""
Image Importer for LaserBurn

Imports raster images as ImageShape objects for laser engraving.
The image is stored as-is and converted to scanlines during G-code generation.
This matches how LightBurn handles images - fast import, rasterization at engrave time.
"""

import numpy as np
from typing import Optional, Tuple
from pathlib import Path

from ..core.shapes import ImageShape, LaserSettings
from ..core.layer import Layer

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ImageImporter:
    """
    Import raster images for laser engraving.
    
    Creates an ImageShape that stores the image data directly.
    No conversion to vectors - G-code generation handles scanline creation.
    """
    
    def __init__(self,
                 dpi: float = 254.0,
                 max_size_mm: Optional[Tuple[float, float]] = None,
                 invert: bool = False):
        """
        Initialize image importer.
        
        Args:
            dpi: Engraving resolution (dots per inch). 254 is standard.
            max_size_mm: Maximum size in mm (width, height). If None, uses image size at DPI.
            invert: Invert image colors (swap black/white)
        """
        self.dpi = dpi
        self.max_size_mm = max_size_mm
        self.invert = invert
    
    def import_image(self, filepath: str, 
                    layer_name: Optional[str] = None) -> Layer:
        """
        Import an image and create a layer with an ImageShape.
        
        This is fast - it just loads the image and stores it.
        Dithering and scanline generation happen during G-code generation.
        
        Args:
            filepath: Path to image file
            layer_name: Name for the created layer (defaults to image filename)
            
        Returns:
            Layer containing the ImageShape
        """
        if not HAS_PIL:
            raise ImportError("Pillow (PIL) is required for image loading")
        
        # Load image
        img = Image.open(filepath)
        
        # Automatically downscale very large images to prevent excessive G-code size
        # Maximum dimension: 2000px (good balance between quality and file size)
        MAX_IMAGE_DIMENSION = 2000
        original_width, original_height = img.size
        if original_width > MAX_IMAGE_DIMENSION or original_height > MAX_IMAGE_DIMENSION:
            # Calculate scale to fit within max dimension while maintaining aspect ratio
            scale = min(MAX_IMAGE_DIMENSION / original_width, MAX_IMAGE_DIMENSION / original_height)
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            # Use high-quality resampling for downscaling
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"Downscaled image from {original_width}x{original_height} to {new_width}x{new_height} pixels")
        
        # Preserve transparency instead of compositing onto white
        # Extract alpha channel if present
        alpha_channel = None
        has_transparency = False
        
        if img.mode in ('RGBA', 'LA'):
            # Extract alpha channel before converting
            if img.mode == 'RGBA':
                alpha_channel = np.array(img.split()[3], dtype=np.uint8)  # Get alpha channel
                has_transparency = np.any(alpha_channel < 255)  # Check if any pixels are transparent
            elif img.mode == 'LA':
                alpha_channel = np.array(img.split()[1], dtype=np.uint8)  # Get alpha channel
                has_transparency = np.any(alpha_channel < 255)
            # Convert to RGB first, then to grayscale (preserving alpha separately)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            else:
                img = img.convert('L')
        elif img.mode == 'P':
            # Palette mode - check for transparency
            if 'transparency' in img.info:
                # Convert to RGBA to get alpha channel
                img_rgba = img.convert('RGBA')
                alpha_channel = np.array(img_rgba.split()[3], dtype=np.uint8)
                has_transparency = np.any(alpha_channel < 255)
                img = img_rgba.convert('RGB')
        
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Convert to numpy array
        image_data = np.array(img, dtype=np.uint8)
        
        # If we have transparency, store alpha channel
        # Transparent pixels will be skipped during processing and engraving
        
        # Invert if requested (for images where black should be engraved)
        if self.invert:
            image_data = 255 - image_data
        
        # Get image dimensions
        height_px, width_px = image_data.shape
        
        # Calculate size in mm
        mm_per_inch = 25.4
        width_mm = (width_px / self.dpi) * mm_per_inch
        height_mm = (height_px / self.dpi) * mm_per_inch
        
        # Scale to fit max size if specified
        if self.max_size_mm:
            max_width, max_height = self.max_size_mm
            scale_w = max_width / width_mm
            scale_h = max_height / height_mm
            scale = min(scale_w, scale_h, 1.0)  # Don't scale up
            width_mm *= scale
            height_mm *= scale
        
        # Create layer
        if layer_name is None:
            layer_name = Path(filepath).stem
        
        layer = Layer(name=layer_name)
        
        # Create ImageShape
        shape = ImageShape(
            x=0,
            y=0,
            width=width_mm,
            height=height_mm,
            image_data=image_data,
            filepath=filepath
        )
        shape.dpi = self.dpi
        shape.invert = self.invert
        shape.alpha_channel = alpha_channel if has_transparency else None
        
        # Set layer settings for image engraving
        layer.laser_settings.operation = "image"
        layer.laser_settings.power = 50.0
        layer.laser_settings.speed = 100.0
        
        layer.add_shape(shape)
        
        return layer
