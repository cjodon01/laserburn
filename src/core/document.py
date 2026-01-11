"""
LaserBurn Document Model

The Document class is the root container for all design data.
"""

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from .layer import Layer
from .shapes import Shape

if TYPE_CHECKING:
    from ..image.cylinder_warp import CylinderParams


@dataclass
class Document:
    """
    The root document containing all design data.
    
    A Document contains multiple Layers, each Layer contains Shapes.
    This is the central data structure that gets saved/loaded.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = "Untitled"
    width: float = 300.0      # mm
    height: float = 200.0     # mm
    layers: List[Layer] = field(default_factory=list)
    
    # Laser settings
    device_profile: Optional[str] = None
    origin: str = "bottom-left"  # or "top-left"
    
    # Cylinder engraving settings
    cylinder_params: Optional['CylinderParams'] = None
    cylinder_warp_image: bool = False
    cylinder_compensate_power: bool = False
    cylinder_compensate_z: bool = False
    
    # Metadata
    created_at: str = ""
    modified_at: str = ""
    
    def add_layer(self, layer: Layer) -> None:
        """Add a layer to the document."""
        self.layers.append(layer)
    
    def remove_layer(self, layer: Layer) -> None:
        """Remove a layer from the document."""
        if layer in self.layers:
            self.layers.remove(layer)
    
    def get_all_shapes(self) -> List[Shape]:
        """Flatten all shapes from all layers."""
        shapes = []
        for layer in self.layers:
            shapes.extend(layer.shapes)
        return shapes
    
    def get_layer_by_name(self, name: str) -> Optional[Layer]:
        """Find a layer by name."""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None
    
    def get_design_bounds(self) -> Optional['BoundingBox']:
        """
        Calculate the bounding box of all visible shapes in the document.
        
        Returns:
            BoundingBox of all visible shapes, or None if no visible shapes
        """
        from .shapes import BoundingBox
        
        visible_shapes = []
        for layer in self.layers:
            if not layer.visible:
                continue
            for shape in layer.shapes:
                if shape.visible:
                    visible_shapes.append(shape)
        
        if not visible_shapes:
            return None
        
        # Get bounding boxes of all visible shapes
        bboxes = [shape.get_bounding_box() for shape in visible_shapes]
        
        # Calculate union of all bounding boxes
        min_x = min(bb.min_x for bb in bboxes)
        min_y = min(bb.min_y for bb in bboxes)
        max_x = max(bb.max_x for bb in bboxes)
        max_y = max(bb.max_y for bb in bboxes)
        
        return BoundingBox(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)

