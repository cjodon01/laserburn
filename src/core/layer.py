"""
LaserBurn Layer System

A layer containing shapes with shared laser settings.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4

from .shapes import Shape, LaserSettings


@dataclass
class Layer:
    """
    A layer containing shapes with shared laser settings.
    
    Layers allow organizing shapes and applying different
    laser parameters to different groups of shapes.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = "Layer"
    visible: bool = True
    locked: bool = False
    
    # Layer-level laser settings (override shape settings if set)
    laser_settings: LaserSettings = field(default_factory=LaserSettings)
    use_layer_settings: bool = True
    
    # Visual properties
    color: str = "#0000FF"  # Display color in UI
    
    # Shapes in this layer
    shapes: List[Shape] = field(default_factory=list)
    
    # Cut order
    cut_order: int = 0  # Lower numbers cut first
    
    def add_shape(self, shape: Shape) -> None:
        """Add a shape to this layer."""
        self.shapes.append(shape)
    
    def remove_shape(self, shape: Shape) -> None:
        """Remove a shape from this layer."""
        if shape in self.shapes:
            self.shapes.remove(shape)
    
    def get_shape_by_id(self, shape_id: UUID) -> Optional[Shape]:
        """Find a shape by its ID."""
        for shape in self.shapes:
            if shape.id == shape_id:
                return shape
        return None
    
    def move_shape_up(self, shape: Shape) -> None:
        """Move shape up in the z-order."""
        if shape not in self.shapes:
            return
        idx = self.shapes.index(shape)
        if idx < len(self.shapes) - 1:
            self.shapes[idx], self.shapes[idx + 1] = \
                self.shapes[idx + 1], self.shapes[idx]
    
    def move_shape_down(self, shape: Shape) -> None:
        """Move shape down in the z-order."""
        if shape not in self.shapes:
            return
        idx = self.shapes.index(shape)
        if idx > 0:
            self.shapes[idx], self.shapes[idx - 1] = \
                self.shapes[idx - 1], self.shapes[idx]

