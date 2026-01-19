"""
Transform Operations for LaserBurn

Handles transformation of shapes including:
- Scaling (via handles)
- Rotation
- Mirroring (flip horizontal/vertical)
- Translation (movement)
"""

from typing import List, Optional, Tuple, Union, Dict
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
        self._transform_center: Optional[QPointF] = None
        self._is_transforming = False
        
        # Store ORIGINAL shape states at transform start
        # Key: shape id, Value: dict with original position, scale, rotation
        self._original_states: Dict[str, dict] = {}
    
    def _get_shape_from_item(self, item: QGraphicsItem) -> Optional[Shape]:
        """Get the Shape from a graphics item."""
        # Try ShapeGraphicsItem.shape_ref
        if hasattr(item, 'shape_ref') and item.shape_ref:
            return item.shape_ref
        # Try EditableTextItem._text_shape
        if hasattr(item, '_text_shape') and item._text_shape:
            return item._text_shape
        # Try ImageGraphicsItem._shape
        if hasattr(item, '_shape') and item._shape:
            return item._shape
        # Try item data
        return item.data(0)
    
    def _update_item_from_shape(self, item: QGraphicsItem, shape: Shape):
        """Update a graphics item after its shape has been transformed."""
        item_type = type(item).__name__
        print(f"[TRANSFORM] _update_item_from_shape: item_type={item_type}, shape_id={shape.id}")
        print(f"  shape.position=({shape.position.x:.2f}, {shape.position.y:.2f})")
        print(f"  shape.scale=({shape.scale_x:.3f}, {shape.scale_y:.3f})")
        print(f"  shape.rotation={math.degrees(shape.rotation):.2f}°")
        
        item_pos_before = item.pos()
        print(f"  item.pos() before=({item_pos_before.x():.2f}, {item_pos_before.y():.2f})")
        
        # For ShapeGraphicsItem and ImageGraphicsItem
        if hasattr(item, 'update_from_shape'):
            print(f"  Calling item.update_from_shape()")
            item.update_from_shape()
        # For EditableTextItem - update position and transforms
        elif hasattr(item, '_text_shape') and hasattr(item, '_apply_shape_transforms'):
            from PyQt6.QtCore import QPointF
            print(f"  Updating EditableTextItem")
            if hasattr(item, '_is_transforming'):
                item._is_transforming = True
            new_pos = QPointF(shape.position.x, shape.position.y)
            print(f"  Setting item position to ({new_pos.x():.2f}, {new_pos.y():.2f})")
            item.setPos(new_pos)
            print(f"  Calling item._apply_shape_transforms()")
            item._apply_shape_transforms()
            if hasattr(item, '_is_transforming'):
                item._is_transforming = False
        elif hasattr(item, 'setPos'):
            from PyQt6.QtCore import QPointF
            new_pos = QPointF(shape.position.x, shape.position.y)
            print(f"  Setting item position to ({new_pos.x():.2f}, {new_pos.y():.2f})")
            item.setPos(new_pos)
        
        item_pos_after = item.pos()
        print(f"  item.pos() after=({item_pos_after.x():.2f}, {item_pos_after.y():.2f})")
        
        if hasattr(item, 'boundingRect'):
            item_bounds = item.boundingRect()
            print(f"  item.boundingRect()=({item_bounds.x():.2f}, {item_bounds.y():.2f}, {item_bounds.width():.2f}, {item_bounds.height():.2f})")
    
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
            print(f"[TRANSFORM] start_transform: No items provided")
            return
        
        print(f"[TRANSFORM] start_transform: handle_type={handle_type}, handle_pos=({handle_pos.x():.2f}, {handle_pos.y():.2f}), items={len(items)}")
        
        self._is_transforming = True
        self._transform_start_pos = handle_pos
        self._original_states.clear()
        
        # Store original state for each shape
        all_centers = []
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Store original values
                self._original_states[shape.id] = {
                    'position_x': shape.position.x,
                    'position_y': shape.position.y,
                    'scale_x': shape.scale_x,
                    'scale_y': shape.scale_y,
                    'rotation': shape.rotation
                }
                
                print(f"[TRANSFORM] start_transform: Shape {shape.id} original state:")
                print(f"  position=({shape.position.x:.2f}, {shape.position.y:.2f})")
                print(f"  scale=({shape.scale_x:.3f}, {shape.scale_y:.3f})")
                print(f"  rotation={math.degrees(shape.rotation):.2f}°")
                
                # Calculate center using BASE (untransformed) bounds
                # For Rectangle, center is position + (width/2, height/2)
                # For other shapes, use get_bounding_box but we need to account for transforms
                if hasattr(shape, 'width') and hasattr(shape, 'height'):
                    # Rectangle or ImageShape - use base dimensions
                    base_center_x = shape.position.x + (shape.width * abs(shape.scale_x)) / 2
                    base_center_y = shape.position.y + (shape.height * abs(shape.scale_y)) / 2
                    all_centers.append(Point(base_center_x, base_center_y))
                    print(f"  base center (from width/height)=({base_center_x:.2f}, {base_center_y:.2f})")
                elif hasattr(shape, 'radius_x') and hasattr(shape, 'radius_y'):
                    # Ellipse - center is at position
                    all_centers.append(Point(shape.position.x, shape.position.y))
                    print(f"  base center (ellipse position)=({shape.position.x:.2f}, {shape.position.y:.2f})")
                else:
                    # For other shapes, use transformed bounding box center
                    # This is less accurate but works for Path/Text
                    bounds = shape.get_bounding_box()
                    cx = (bounds.min_x + bounds.max_x) / 2
                    cy = (bounds.min_y + bounds.max_y) / 2
                    all_centers.append(Point(cx, cy))
                    print(f"  bounds center (transformed)=({cx:.2f}, {cy:.2f})")
        
        # Set transform center
        if center:
            self._transform_center = center
        elif all_centers:
            center_x = sum(p.x for p in all_centers) / len(all_centers)
            center_y = sum(p.y for p in all_centers) / len(all_centers)
            self._transform_center = QPointF(center_x, center_y)
        else:
            self._transform_center = QPointF(0, 0)
        
        print(f"[TRANSFORM] start_transform: Transform center=({self._transform_center.x():.2f}, {self._transform_center.y():.2f})")
    
    def update_transform(self, items: List[QGraphicsItem], current_pos: QPointF, 
                        handle_type: str, maintain_aspect: bool = False) -> bool:
        """
        Update transformation based on handle movement.
        """
        if not self._is_transforming or not items or not self._transform_start_pos:
            return False
        
        if handle_type == "corner":
            return self._update_scale_corner(items, current_pos, maintain_aspect)
        elif handle_type == "edge":
            return self._update_scale_edge(items, current_pos)
        elif handle_type == "rotation":
            return self._update_rotation(items, current_pos)
        
        return False
    
    def _update_scale_corner(self, items: List[QGraphicsItem], current_pos: QPointF, 
                            maintain_aspect: bool = False) -> bool:
        """Update scale transformation via corner handle."""
        if not self._transform_center or not self._transform_start_pos:
            print(f"[TRANSFORM] _update_scale_corner: Missing transform center or start pos")
            return False
        
        print(f"[TRANSFORM] _update_scale_corner: current_pos=({current_pos.x():.2f}, {current_pos.y():.2f})")
        
        # Calculate scale factors from ORIGINAL start to current (not frame-to-frame)
        start_delta_x = self._transform_start_pos.x() - self._transform_center.x()
        start_delta_y = self._transform_start_pos.y() - self._transform_center.y()
        current_delta_x = current_pos.x() - self._transform_center.x()
        current_delta_y = current_pos.y() - self._transform_center.y()
        
        print(f"[TRANSFORM] _update_scale_corner: start_delta=({start_delta_x:.2f}, {start_delta_y:.2f})")
        print(f"[TRANSFORM] _update_scale_corner: current_delta=({current_delta_x:.2f}, {current_delta_y:.2f})")
        
        # Avoid division by zero
        min_delta = 1.0
        if abs(start_delta_x) < min_delta:
            start_delta_x = min_delta if start_delta_x >= 0 else -min_delta
        if abs(start_delta_y) < min_delta:
            start_delta_y = min_delta if start_delta_y >= 0 else -min_delta
        
        # Calculate TOTAL scale factor from original position
        total_scale_x = current_delta_x / start_delta_x
        total_scale_y = current_delta_y / start_delta_y
        
        # If maintaining aspect ratio, use the larger scale factor
        if maintain_aspect:
            # Use the scale factor with the larger magnitude
            if abs(total_scale_x) > abs(total_scale_y):
                total_scale_y = total_scale_x * (1 if total_scale_y >= 0 else -1)
            else:
                total_scale_x = total_scale_y * (1 if total_scale_x >= 0 else -1)
        
        print(f"[TRANSFORM] _update_scale_corner: raw scale=({total_scale_x:.3f}, {total_scale_y:.3f})")
        
        # Clamp scale to reasonable values
        min_scale = 0.01
        max_scale = 100.0
        total_scale_x = max(min_scale, min(max_scale, abs(total_scale_x))) * (1 if total_scale_x >= 0 else -1)
        total_scale_y = max(min_scale, min(max_scale, abs(total_scale_y))) * (1 if total_scale_y >= 0 else -1)
        
        print(f"[TRANSFORM] _update_scale_corner: clamped scale=({total_scale_x:.3f}, {total_scale_y:.3f})")
        
        # Apply to all selected shapes using ORIGINAL values
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape and shape.id in self._original_states:
                orig = self._original_states[shape.id]
                
                print(f"[TRANSFORM] _update_scale_corner: Shape {shape.id}:")
                print(f"  original scale=({orig['scale_x']:.3f}, {orig['scale_y']:.3f})")
                
                # Apply total scale to original scale values
                new_scale_x = orig['scale_x'] * total_scale_x
                new_scale_y = orig['scale_y'] * total_scale_y
                
                # Calculate shape center in local coordinates
                # For Rectangle/ImageShape: center is at (width/2, height/2) in local coords
                # For Ellipse: center is at (0, 0) in local coords (position is the center)
                local_center_x = 0.0
                local_center_y = 0.0
                
                if hasattr(shape, 'width') and hasattr(shape, 'height'):
                    # Rectangle or ImageShape - center is at half width/height
                    local_center_x = shape.width / 2.0
                    local_center_y = shape.height / 2.0
                elif hasattr(shape, 'radius_x') and hasattr(shape, 'radius_y'):
                    # Ellipse - center is at position (0,0 in local)
                    local_center_x = 0.0
                    local_center_y = 0.0
                
                # Transform local center to world coordinates with NEW scale and rotation
                # Scale first
                scaled_cx = local_center_x * new_scale_x
                scaled_cy = local_center_y * new_scale_y
                # Then rotate
                cos_r = math.cos(orig['rotation'])
                sin_r = math.sin(orig['rotation'])
                rotated_cx = scaled_cx * cos_r - scaled_cy * sin_r
                rotated_cy = scaled_cx * sin_r + scaled_cy * cos_r
                
                # To keep transform center fixed, adjust position
                # new_position + rotated_center = transform_center
                # So: new_position = transform_center - rotated_center
                new_pos_x = self._transform_center.x() - rotated_cx
                new_pos_y = self._transform_center.y() - rotated_cy
                
                # Apply changes
                shape.scale_x = new_scale_x
                shape.scale_y = new_scale_y
                shape.position.x = new_pos_x
                shape.position.y = new_pos_y
                
                print(f"  new scale=({new_scale_x:.3f}, {new_scale_y:.3f})")
                print(f"  new position=({new_pos_x:.2f}, {new_pos_y:.2f})")
                print(f"  shape.scale_x={shape.scale_x:.3f}, shape.scale_y={shape.scale_y:.3f}")
                
                # Invalidate cache
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Update graphics item
                self._update_item_from_shape(item, shape)
                
                # Log final state
                bounds = shape.get_bounding_box()
                print(f"  final bounds: min=({bounds.min_x:.2f}, {bounds.min_y:.2f}), max=({bounds.max_x:.2f}, {bounds.max_y:.2f})")
        
        return True
    
    def _update_scale_edge(self, items: List[QGraphicsItem], current_pos: QPointF) -> bool:
        """Update scale transformation via edge handle."""
        if not self._transform_center or not self._transform_start_pos:
            return False
        
        # Determine which edge based on handle position relative to center
        start_delta = self._transform_start_pos - self._transform_center
        current_delta = current_pos - self._transform_center
        
        # Check if horizontal or vertical edge
        is_vertical_edge = abs(start_delta.y()) > abs(start_delta.x())
        
        min_delta = 1.0
        min_scale = 0.01
        max_scale = 100.0
        
        if is_vertical_edge:
            # Vertical scaling (top/bottom edge)
            if abs(start_delta.y()) < min_delta:
                start_delta.setY(min_delta if start_delta.y() >= 0 else -min_delta)
            total_scale_y = current_delta.y() / start_delta.y()
            total_scale_y = max(min_scale, min(max_scale, abs(total_scale_y))) * (1 if total_scale_y >= 0 else -1)
            total_scale_x = 1.0
        else:
            # Horizontal scaling (left/right edge)
            if abs(start_delta.x()) < min_delta:
                start_delta.setX(min_delta if start_delta.x() >= 0 else -min_delta)
            total_scale_x = current_delta.x() / start_delta.x()
            total_scale_x = max(min_scale, min(max_scale, abs(total_scale_x))) * (1 if total_scale_x >= 0 else -1)
            total_scale_y = 1.0
        
        # Apply to all selected shapes using ORIGINAL values
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape and shape.id in self._original_states:
                orig = self._original_states[shape.id]
                
                # Apply total scale to original scale values
                shape.scale_x = orig['scale_x'] * total_scale_x
                shape.scale_y = orig['scale_y'] * total_scale_y
                
                # Invalidate cache
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                self._update_item_from_shape(item, shape)
        
        return True
    
    def _update_rotation(self, items: List[QGraphicsItem], current_pos: QPointF) -> bool:
        """Update rotation transformation."""
        if not self._transform_center or not self._transform_start_pos:
            print(f"[TRANSFORM] _update_rotation: Missing transform center or start pos")
            return False
        
        print(f"[TRANSFORM] _update_rotation: current_pos=({current_pos.x():.2f}, {current_pos.y():.2f})")
        
        # Calculate angles from ORIGINAL start position
        start_angle = math.atan2(
            self._transform_start_pos.y() - self._transform_center.y(),
            self._transform_start_pos.x() - self._transform_center.x()
        )
        current_angle = math.atan2(
            current_pos.y() - self._transform_center.y(),
            current_pos.x() - self._transform_center.x()
        )
        
        # Calculate TOTAL rotation from start
        total_rotation = current_angle - start_angle
        
        print(f"[TRANSFORM] _update_rotation: start_angle={math.degrees(start_angle):.2f}°, current_angle={math.degrees(current_angle):.2f}°")
        print(f"[TRANSFORM] _update_rotation: total_rotation={math.degrees(total_rotation):.2f}° ({total_rotation:.4f} rad)")
        
        # Apply to all selected shapes using ORIGINAL values
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape and shape.id in self._original_states:
                orig = self._original_states[shape.id]
                
                print(f"[TRANSFORM] _update_rotation: Shape {shape.id}:")
                print(f"  original rotation={math.degrees(orig['rotation']):.2f}° ({orig['rotation']:.4f} rad)")
                print(f"  original position=({orig['position_x']:.2f}, {orig['position_y']:.2f})")
                
                # Apply total rotation to original rotation
                new_rotation = orig['rotation'] + total_rotation
                shape.rotation = new_rotation
                
                print(f"  new rotation={math.degrees(new_rotation):.2f}° ({new_rotation:.4f} rad)")
                
                # Rotate position around transform center
                orig_x = orig['position_x']
                orig_y = orig['position_y']
                orig_scale_x = orig['scale_x']
                orig_scale_y = orig['scale_y']
                
                # Calculate ORIGINAL untransformed center from original position and dimensions
                # This is critical - we must use original values, not transformed bounding box
                orig_center_x = orig_x
                orig_center_y = orig_y
                offset_x = 0.0
                offset_y = 0.0
                
                if hasattr(shape, 'width') and hasattr(shape, 'height'):
                    # Rectangle or ImageShape - center is at position + (width/2 * scale_x, height/2 * scale_y)
                    offset_x = (shape.width * abs(orig_scale_x)) / 2.0
                    offset_y = (shape.height * abs(orig_scale_y)) / 2.0
                    orig_center_x = orig_x + offset_x
                    orig_center_y = orig_y + offset_y
                elif hasattr(shape, 'radius_x') and hasattr(shape, 'radius_y'):
                    # Ellipse - position IS the center (no offset)
                    orig_center_x = orig_x
                    orig_center_y = orig_y
                else:
                    # For Path/Text, we need to calculate from untransformed paths
                    # Temporarily set shape to original state to get untransformed bounds
                    temp_pos = shape.position
                    temp_scale_x = shape.scale_x
                    temp_scale_y = shape.scale_y
                    temp_rotation = shape.rotation
                    
                    shape.position = Point(orig_x, orig_y)
                    shape.scale_x = orig_scale_x
                    shape.scale_y = orig_scale_y
                    shape.rotation = orig['rotation']
                    
                    bounds = shape.get_bounding_box()
                    orig_center_x = (bounds.min_x + bounds.max_x) / 2
                    orig_center_y = (bounds.min_y + bounds.max_y) / 2
                    offset_x = orig_center_x - orig_x
                    offset_y = orig_center_y - orig_y
                    
                    # Restore temporary values
                    shape.position = temp_pos
                    shape.scale_x = temp_scale_x
                    shape.scale_y = temp_scale_y
                    shape.rotation = temp_rotation
                
                print(f"  original center=({orig_center_x:.2f}, {orig_center_y:.2f})")
                print(f"  offset from pos to center=({offset_x:.2f}, {offset_y:.2f})")
                
                # Rotate original center around transform center
                dx = orig_center_x - self._transform_center.x()
                dy = orig_center_y - self._transform_center.y()
                
                print(f"  delta from transform center=({dx:.2f}, {dy:.2f})")
                
                cos_r = math.cos(total_rotation)
                sin_r = math.sin(total_rotation)
                
                new_center_x = self._transform_center.x() + dx * cos_r - dy * sin_r
                new_center_y = self._transform_center.y() + dx * sin_r + dy * cos_r
                
                print(f"  rotated center=({new_center_x:.2f}, {new_center_y:.2f})")
                
                # Calculate new position from new center (subtract the offset)
                new_pos_x = new_center_x - offset_x
                new_pos_y = new_center_y - offset_y
                shape.position.x = new_pos_x
                shape.position.y = new_pos_y
                
                print(f"  new position=({new_pos_x:.2f}, {new_pos_y:.2f})")
                print(f"  shape.position=({shape.position.x:.2f}, {shape.position.y:.2f})")
                
                # Invalidate cache
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                self._update_item_from_shape(item, shape)
                
                # Log final state
                final_bounds = shape.get_bounding_box()
                print(f"  final bounds: min=({final_bounds.min_x:.2f}, {final_bounds.min_y:.2f}), max=({final_bounds.max_x:.2f}, {final_bounds.max_y:.2f})")
        
        return True
    
    def finish_transform(self):
        """Finish the current transformation."""
        print(f"[TRANSFORM] finish_transform: Ending transformation")
        self._is_transforming = False
        self._transform_start_pos = None
        self._transform_center = None
        self._original_states.clear()
    
    def cancel_transform(self):
        """Cancel the current transformation and restore original values."""
        # Restore original states
        # Note: We'd need to store item references to do this properly
        self.finish_transform()
    
    def mirror_horizontal(self, items: List[QGraphicsItem], center_x: Optional[float] = None):
        """Mirror shapes horizontally (flip left-right)."""
        if not items:
            return
        
        # Calculate mirror center if not provided
        if center_x is None:
            all_points = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    bounds = shape.get_bounding_box()
                    all_points.append(bounds.min_x)
                    all_points.append(bounds.max_x)
            
            if all_points:
                center_x = (min(all_points) + max(all_points)) / 2
            else:
                center_x = 0.0
        
        # Apply mirror to each shape
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Mirror scale
                shape.scale_x *= -1
                
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                # Mirror position around center
                bounds = shape.get_bounding_box()
                shape_center_x = (bounds.min_x + bounds.max_x) / 2
                offset = 2 * (center_x - shape_center_x)
                shape.position.x += offset
                
                self._update_item_from_shape(item, shape)
    
    def mirror_vertical(self, items: List[QGraphicsItem], center_y: Optional[float] = None):
        """Mirror shapes vertically (flip top-bottom)."""
        if not items:
            return
        
        if center_y is None:
            all_points = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    bounds = shape.get_bounding_box()
                    all_points.append(bounds.min_y)
                    all_points.append(bounds.max_y)
            
            if all_points:
                center_y = (min(all_points) + max(all_points)) / 2
            else:
                center_y = 0.0
        
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                shape.scale_y *= -1
                
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                bounds = shape.get_bounding_box()
                shape_center_y = (bounds.min_y + bounds.max_y) / 2
                offset = 2 * (center_y - shape_center_y)
                shape.position.y += offset
                
                self._update_item_from_shape(item, shape)
    
    def rotate(self, items: List[QGraphicsItem], angle: float, 
              center: Optional[QPointF] = None):
        """Rotate shapes by a specific angle (in radians)."""
        if not items:
            return
        
        # Calculate rotation center if not provided
        if center is None:
            all_centers = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    bounds = shape.get_bounding_box()
                    cx = (bounds.min_x + bounds.max_x) / 2
                    cy = (bounds.min_y + bounds.max_y) / 2
                    all_centers.append(Point(cx, cy))
            
            if all_centers:
                center_x = sum(p.x for p in all_centers) / len(all_centers)
                center_y = sum(p.y for p in all_centers) / len(all_centers)
                center = QPointF(center_x, center_y)
            else:
                center = QPointF(0, 0)
        
        cos_r = math.cos(angle)
        sin_r = math.sin(angle)
        
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                # Get shape center
                bounds = shape.get_bounding_box()
                shape_center = Point(
                    (bounds.min_x + bounds.max_x) / 2,
                    (bounds.min_y + bounds.max_y) / 2
                )
                
                # Rotate shape center around rotation center
                dx = shape_center.x - center.x()
                dy = shape_center.y - center.y()
                
                new_dx = dx * cos_r - dy * sin_r
                new_dy = dx * sin_r + dy * cos_r
                
                # Update position
                shape.position.x += (new_dx - dx)
                shape.position.y += (new_dy - dy)
                
                # Add rotation
                shape.rotation += angle
                
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                self._update_item_from_shape(item, shape)
    
    def scale(self, items: List[QGraphicsItem], scale_x: float, scale_y: float,
             center: Optional[QPointF] = None):
        """Scale shapes by specific factors."""
        if not items:
            return
        
        if center is None:
            all_points = []
            for item in items:
                shape = self._get_shape_from_item(item)
                if shape:
                    bounds = shape.get_bounding_box()
                    all_points.append(bounds.min_x)
                    all_points.append(bounds.max_x)
                    all_points.append(bounds.min_y)
                    all_points.append(bounds.max_y)
            
            if all_points:
                center = QPointF(
                    (min(all_points[::2]) + max(all_points[::2])) / 2,
                    (min(all_points[1::2]) + max(all_points[1::2])) / 2
                )
            else:
                center = QPointF(0, 0)
        
        for item in items:
            shape = self._get_shape_from_item(item)
            if shape:
                shape.scale_x *= scale_x
                shape.scale_y *= scale_y
                
                if hasattr(shape, 'invalidate_cache'):
                    shape.invalidate_cache()
                
                self._update_item_from_shape(item, shape)
