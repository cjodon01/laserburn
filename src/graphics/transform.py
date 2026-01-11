"""
Transform Operations for LaserBurn

Handles transformation of shapes including:
- Scaling (via handles)
- Rotation
- Mirroring (flip horizontal/vertical)
- Translation (movement)
"""

from typing import List, Optional, Tuple, Union
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QTransform
import math

from ..core.shapes import Shape, Point, BoundingBox
from .items import ShapeGraphicsItem


class TransformManager:
    """
    Manages transformations of selected shapes.
    
    Provides methods for:
    - Scaling shapes via handles
    - Rotating shapes
    - Mirroring shapes
    - Moving shapes
    """
    
    def __init__(self):
        """Initialize transform manager."""
        self._transform_start_pos: Optional[QPointF] = None
        self._transform_start_bounds: Optional[BoundingBox] = None
        self._transform_center: Optional[QPointF] = None
        self._is_transforming = False
    
    def _get_shape_from_item(self, item: QGraphicsItem) -> Optional[Shape]:
        """Get the Shape from a graphics item (ShapeGraphicsItem or EditableTextItem)."""
        # Try ShapeGraphicsItem.shape_ref
        if hasattr(item, 'shape_ref') and item.shape_ref:
            return item.shape_ref
        # Try EditableTextItem._text_shape
        if hasattr(item, '_text_shape') and item._text_shape:
            return item._text_shape
        # Try item data
        return item.data(0)
    
    def _update_item_from_shape(self, item: QGraphicsItem, shape: Shape):
        """Update a graphics item after its shape has been transformed."""
        # For ShapeGraphicsItem
        if hasattr(item, 'update_from_shape'):
            item.update_from_shape()
        # For EditableTextItem - update position
        elif hasattr(item, 'setPos'):
            from PyQt6.QtCore import QPointF
            item.setPos(QPointF(shape.position.x, shape.position.y))
    
    def start_transform(self, items: List[QGraphicsItem], handle_pos: QPointF, 
                       handle_type: str, center: Optional[QPointF] = None):
        """
        Start a transformation operation.
        
        Args:
            items: List of items to transform
            handle_pos: Initial position of the handle
            handle_type: Type of handle ("corner", "edge", "rotation")
            center: Transform center point (defaults to selection center)
        """
        if not items:
            return
        
        self._is_transforming = True
        self._transform_start_pos = handle_pos
        
        # Calculate selection bounds
        all_points = []
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                paths = shape.get_paths()
                for path in paths:
                    all_points.extend(path)
        
        if all_points:
            self._transform_start_bounds = BoundingBox(
                min_x=min(p.x for p in all_points),
                min_y=min(p.y for p in all_points),
                max_x=max(p.x for p in all_points),
                max_y=max(p.y for p in all_points)
            )
        
        # Set transform center
        if center:
            self._transform_center = center
        elif self._transform_start_bounds:
            center_x = (self._transform_start_bounds.min_x + self._transform_start_bounds.max_x) / 2
            center_y = (self._transform_start_bounds.min_y + self._transform_start_bounds.max_y) / 2
            self._transform_center = QPointF(center_x, center_y)
        else:
            self._transform_center = QPointF(0, 0)
    
    def update_transform(self, items: List[QGraphicsItem], current_pos: QPointF, 
                        handle_type: str) -> bool:
        """
        Update transformation based on handle movement.
        
        Args:
            items: List of items to transform
            current_pos: Current handle position
            handle_type: Type of handle ("corner", "edge", "rotation")
        
        Returns:
            True if transform was applied, False otherwise
        """
        if not self._is_transforming or not items or not self._transform_start_bounds:
            return False
        
        if handle_type == "corner":
            return self._update_scale_corner(items, current_pos)
        elif handle_type == "edge":
            return self._update_scale_edge(items, current_pos)
        elif handle_type == "rotation":
            return self._update_rotation(items, current_pos)
        
        return False
    
    def _update_scale_corner(self, items: List[QGraphicsItem], current_pos: QPointF) -> bool:
        """Update scale transformation via corner handle."""
        if not self._transform_center or not self._transform_start_pos:
            return False
        
        # Calculate scale factors
        start_delta_x = self._transform_start_pos.x() - self._transform_center.x()
        start_delta_y = self._transform_start_pos.y() - self._transform_center.y()
        current_delta_x = current_pos.x() - self._transform_center.x()
        current_delta_y = current_pos.y() - self._transform_center.y()
        
        # Avoid division by zero
        if abs(start_delta_x) < 0.001 or abs(start_delta_y) < 0.001:
            return False
        
        scale_x = current_delta_x / start_delta_x
        scale_y = current_delta_y / start_delta_y
        
        # Apply scale to all selected shapes
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Get original bounds
                bounds = shape.get_bounding_box()
                center_x = (bounds.min_x + bounds.max_x) / 2
                center_y = (bounds.min_y + bounds.max_y) / 2
                
                # Scale around shape center
                shape.scale_x *= scale_x
                shape.scale_y *= scale_y
                
                # Invalidate cache for text shapes
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Update position to maintain center
                new_bounds = shape.get_bounding_box()
                new_center_x = (new_bounds.min_x + new_bounds.max_x) / 2
                new_center_y = (new_bounds.min_y + new_bounds.max_y) / 2
                
                shape.position.x += (center_x - new_center_x)
                shape.position.y += (center_y - new_center_y)
                
                # Update graphics item
                self._update_item_from_shape(item, shape)
        
        # Update start position for next frame
        self._transform_start_pos = current_pos
        return True
    
    def _update_scale_edge(self, items: List[QGraphicsItem], current_pos: QPointF) -> bool:
        """Update scale transformation via edge handle."""
        if not self._transform_center or not self._transform_start_pos:
            return False
        
        # Determine which edge based on handle position relative to center
        start_delta = self._transform_start_pos - self._transform_center
        current_delta = current_pos - self._transform_center
        
        # Check if horizontal or vertical edge
        is_horizontal = abs(start_delta.y()) > abs(start_delta.x())
        
        if is_horizontal:
            # Vertical scaling
            if abs(start_delta.y()) < 0.001:
                return False
            scale_y = current_delta.y() / start_delta.y()
            scale_x = 1.0
        else:
            # Horizontal scaling
            if abs(start_delta.x()) < 0.001:
                return False
            scale_x = current_delta.x() / start_delta.x()
            scale_y = 1.0
        
        # Apply scale to all selected shapes
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                bounds = shape.get_bounding_box()
                center_x = (bounds.min_x + bounds.max_x) / 2
                center_y = (bounds.min_y + bounds.max_y) / 2
                
                shape.scale_x *= scale_x
                shape.scale_y *= scale_y
                
                # Invalidate cache for text shapes
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                new_bounds = shape.get_bounding_box()
                new_center_x = (new_bounds.min_x + new_bounds.max_x) / 2
                new_center_y = (new_bounds.min_y + new_bounds.max_y) / 2
                
                shape.position.x += (center_x - new_center_x)
                shape.position.y += (center_y - new_center_y)
                
                self._update_item_from_shape(item, shape)
        
        self._transform_start_pos = current_pos
        return True
    
    def _update_rotation(self, items: List[QGraphicsItem], current_pos: QPointF) -> bool:
        """Update rotation transformation."""
        if not self._transform_center or not self._transform_start_pos:
            return False
        
        # Calculate angles
        start_angle = math.atan2(
            self._transform_start_pos.y() - self._transform_center.y(),
            self._transform_start_pos.x() - self._transform_center.x()
        )
        current_angle = math.atan2(
            current_pos.y() - self._transform_center.y(),
            current_pos.x() - self._transform_center.x()
        )
        
        # Calculate rotation delta
        rotation_delta = current_angle - start_angle
        
        # Apply rotation to all selected shapes
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Rotate around transform center
                shape.rotation += rotation_delta
                
                # Invalidate cache for text shapes
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Update position to rotate around center
                bounds = shape.get_bounding_box()
                shape_center = Point(
                    (bounds.min_x + bounds.max_x) / 2,
                    (bounds.min_y + bounds.max_y) / 2
                )
                
                # Rotate shape center around transform center
                dx = shape_center.x - self._transform_center.x()
                dy = shape_center.y - self._transform_center.y()
                
                cos_r = math.cos(rotation_delta)
                sin_r = math.sin(rotation_delta)
                
                new_dx = dx * cos_r - dy * sin_r
                new_dy = dx * sin_r + dy * cos_r
                
                shape.position.x += (new_dx - dx)
                shape.position.y += (new_dy - dy)
                
                self._update_item_from_shape(item, shape)
        
        self._transform_start_pos = current_pos
        return True
    
    def finish_transform(self):
        """Finish the current transformation."""
        self._is_transforming = False
        self._transform_start_pos = None
        self._transform_start_bounds = None
        self._transform_center = None
    
    def cancel_transform(self):
        """Cancel the current transformation."""
        self.finish_transform()
    
    def mirror_horizontal(self, items: List[QGraphicsItem], center_x: Optional[float] = None):
        """
        Mirror shapes horizontally (flip left-right).
        
        Args:
            items: List of items to mirror
            center_x: X coordinate of mirror axis (defaults to selection center)
        """
        if not items:
            return
        
        # Calculate mirror center if not provided
        if center_x is None:
            all_points = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    paths = shape.get_paths()
                    for path in paths:
                        all_points.extend(path)
            
            if all_points:
                center_x = (min(p.x for p in all_points) + max(p.x for p in all_points)) / 2
            else:
                center_x = 0.0
        
        # Apply mirror to each shape
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Mirror scale
                shape.scale_x *= -1
                
                # Invalidate cache for text shapes
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Mirror position
                bounds = shape.get_bounding_box()
                shape_center_x = (bounds.min_x + bounds.max_x) / 2
                offset = 2 * (center_x - shape_center_x)
                shape.position.x += offset
                
                self._update_item_from_shape(item, shape)
    
    def mirror_vertical(self, items: List[QGraphicsItem], center_y: Optional[float] = None):
        """
        Mirror shapes vertically (flip top-bottom).
        
        Args:
            items: List of items to mirror
            center_y: Y coordinate of mirror axis (defaults to selection center)
        """
        if not items:
            return
        
        # Calculate mirror center if not provided
        if center_y is None:
            all_points = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    paths = shape.get_paths()
                    for path in paths:
                        all_points.extend(path)
            
            if all_points:
                center_y = (min(p.y for p in all_points) + max(p.y for p in all_points)) / 2
            else:
                center_y = 0.0
        
        # Apply mirror to each shape
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Mirror scale
                shape.scale_y *= -1
                
                # Invalidate cache for text shapes
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Mirror position
                bounds = shape.get_bounding_box()
                shape_center_y = (bounds.min_y + bounds.max_y) / 2
                offset = 2 * (center_y - shape_center_y)
                shape.position.y += offset
                
                self._update_item_from_shape(item, shape)
    
    def rotate(self, items: List[QGraphicsItem], angle: float, 
              center: Optional[QPointF] = None):
        """
        Rotate shapes by a specific angle.
        
        Args:
            items: List of items to rotate
            angle: Rotation angle in radians
            center: Rotation center (defaults to selection center)
        """
        if not items:
            return
        
        # Calculate rotation center if not provided
        if center is None:
            all_points = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    paths = shape.get_paths()
                    for path in paths:
                        all_points.extend(path)
            
            if all_points:
                center_x = (min(p.x for p in all_points) + max(p.x for p in all_points)) / 2
                center_y = (min(p.y for p in all_points) + max(p.y for p in all_points)) / 2
                center = QPointF(center_x, center_y)
            else:
                center = QPointF(0, 0)
        
        # Apply rotation to each shape
        cos_r = math.cos(angle)
        sin_r = math.sin(angle)
        
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Add rotation
                shape.rotation += angle
                
                # Invalidate cache for text shapes
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Rotate position around center
                bounds = shape.get_bounding_box()
                shape_center = Point(
                    (bounds.min_x + bounds.max_x) / 2,
                    (bounds.min_y + bounds.max_y) / 2
                )
                
                dx = shape_center.x - center.x()
                dy = shape_center.y - center.y()
                
                new_dx = dx * cos_r - dy * sin_r
                new_dy = dx * sin_r + dy * cos_r
                
                shape.position.x += (new_dx - dx)
                shape.position.y += (new_dy - dy)
                
                self._update_item_from_shape(item, shape)
    
    def scale(self, items: List[QGraphicsItem], scale_x: float, scale_y: float,
             center: Optional[QPointF] = None):
        """
        Scale shapes by specific factors.
        
        Args:
            items: List of items to scale
            scale_x: X scale factor
            scale_y: Y scale factor
            center: Scale center (defaults to selection center)
        """
        if not items:
            return
        
        # Calculate scale center if not provided
        if center is None:
            all_points = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    paths = shape.get_paths()
                    for path in paths:
                        all_points.extend(path)
            
            if all_points:
                center_x = (min(p.x for p in all_points) + max(p.x for p in all_points)) / 2
                center_y = (min(p.y for p in all_points) + max(p.y for p in all_points)) / 2
                center = QPointF(center_x, center_y)
            else:
                center = QPointF(0, 0)
        
        # Apply scale to each shape
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                bounds = shape.get_bounding_box()
                shape_center_x = (bounds.min_x + bounds.max_x) / 2
                shape_center_y = (bounds.min_y + bounds.max_y) / 2
                
                # Scale
                shape.scale_x *= scale_x
                shape.scale_y *= scale_y
                
                # Invalidate cache for text shapes
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Adjust position to maintain center
                new_bounds = shape.get_bounding_box()
                new_center_x = (new_bounds.min_x + new_bounds.max_x) / 2
                new_center_y = (new_bounds.min_y + new_bounds.max_y) / 2
                
                shape.position.x += (shape_center_x - new_center_x)
                shape.position.y += (shape_center_y - new_center_y)
                
                self._update_item_from_shape(item, shape)


