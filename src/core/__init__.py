"""
LaserBurn Core Module

Contains the core data structures:
- Document: Root container for all design data
- Layer: Groups shapes with shared laser settings
- Shapes: Rectangle, Ellipse, Path, Text, etc.
- Transform: Matrix transformations
"""

# Import order matters - shapes first, then layer, then document
from .shapes import (
    Point, BoundingBox, LaserSettings, Shape,
    Rectangle, Ellipse, Path, Text
)
from .layer import Layer
from .document import Document

__all__ = [
    'Point', 'BoundingBox', 'LaserSettings', 'Shape',
    'Rectangle', 'Ellipse', 'Path', 'Text',
    'Layer',
    'Document'
]

