"""
LaserBurn Image Processing Module

Contains image processing tools:
- Cylinder warping for non-rotary cylinder engraving
- Dithering algorithms (coming soon)
- Image tracing (coming soon)
"""

from .cylinder_warp import CylinderParams, CylinderWarper

__all__ = [
    'CylinderParams',
    'CylinderWarper',
]
