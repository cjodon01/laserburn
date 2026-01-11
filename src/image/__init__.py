"""
LaserBurn Image Processing Module

Contains image processing tools:
- Cylinder warping for non-rotary cylinder engraving
- Dithering algorithms for grayscale engraving
- Image loading and processing
"""

from .cylinder_warp import CylinderParams, CylinderWarper
from .dithering import (
    DitheringMethod, ImageDitherer,
    load_image, adjust_brightness_contrast
)

__all__ = [
    'CylinderParams',
    'CylinderWarper',
    'DitheringMethod',
    'ImageDitherer',
    'load_image',
    'adjust_brightness_contrast',
]