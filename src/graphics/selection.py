"""
Selection Handling for LaserBurn

Manages selection state, selection handles, and selection operations.
"""

from typing import List, Set, Optional, Union
from PyQt6.QtCore import QRectF, QPointF, pyqtSignal, QObject, Qt
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor

from ..core.shapes import Shape, Point, BoundingBox
from .transform import TransformManager
from .items import ShapeGraphicsItem, SelectionHandleItem

# Type alias for items that can be selected
SelectableItem = Union[ShapeGraphicsItem, 'EditableTextItem']


class SelectionManager(QObject):
    """
    Manages selection state and operations.
    
    Features:
    - Single and multi-selection
    - Selection handles for transformation
    - Selection rectangle (rubber band)
    - Selection operations (delete, copy, etc.)
    """
    
    # Signals
    selection_changed = pyqtSignal(list)  # List of selected shapes
    
    def __init__(self, scene: QGraphicsScene):
        """
        Initialize selection manager.
        
        Args:
            scene: QGraphicsScene to manage selections in
        """
        super().__init__()
        
        self.scene = scene
        self._selected_items: Set[QGraphicsItem] = set()  # Can be ShapeGraphicsItem or EditableTextItem
        self._selected_shapes: List[Shape] = []
        self._handles: List[SelectionHandleItem] = []
        self._show_handles = True
        
        # Transform manager
        self._transform_manager = TransformManager()
        self._active_handle: Optional[SelectionHandleItem] = None
        
        # Selection rectangle
        self._selection_rect_item: Optional[QGraphicsItem] = None
        self._is_selecting = False
        self._select_start: Optional[QPointF] = None
    
    def _get_shape_from_item(self, item: QGraphicsItem) -> Optional[Shape]:
        """Get the Shape from a graphics item."""
        # Try EditableTextItem first
        if hasattr(item, '_text_shape') and item._text_shape:
            return item._text_shape
        # Try ShapeGraphicsItem
        if hasattr(item, 'shape_ref') and item.shape_ref:
            return item.shape_ref
        # Try data
        return item.data(0)
    
    def _is_selectable_item(self, item: QGraphicsItem) -> bool:
        """Check if an item can be selected."""
        from .text_item import EditableTextItem
        return isinstance(item, (ShapeGraphicsItem, EditableTextItem))
    
    def clear_selection(self):
        """Clear all selections."""
        for item in list(self._selected_items):
            item.setSelected(False)
        
        self._remove_handles()
        self._selected_items.clear()
        self._selected_shapes.clear()
        self.selection_changed.emit([])
    
    def select_item(self, item: QGraphicsItem, add_to_selection: bool = False):
        """
        Select an item.
        
        Args:
            item: Item to select (ShapeGraphicsItem or EditableTextItem)
            add_to_selection: If True, add to existing selection; otherwise replace
        """
        if not self._is_selectable_item(item):
            return
        
        if not add_to_selection:
            self.clear_selection()
        
        if item not in self._selected_items:
            item.setSelected(True)
            self._selected_items.add(item)
            
            shape = self._get_shape_from_item(item)
            if shape:
                self._selected_shapes.append(shape)
            
            if self._show_handles:
                self._add_handles(item)
            
            self.selection_changed.emit(self._selected_shapes.copy())
    
    def deselect_item(self, item: QGraphicsItem):
        """
        Deselect an item.
        
        Args:
            item: Item to deselect
        """
        if item in self._selected_items:
            item.setSelected(False)
            self._selected_items.discard(item)
            
            shape = self._get_shape_from_item(item)
            if shape and shape in self._selected_shapes:
                self._selected_shapes.remove(shape)
            
            self._remove_handles()
            if self._selected_items and self._show_handles:
                # Re-add handles for remaining selection
                for selected_item in self._selected_items:
                    self._add_handles(selected_item)
            
            self.selection_changed.emit(self._selected_shapes.copy())
    
    def select_all(self):
        """Select all selectable items in the scene."""
        self.clear_selection()
        
        for item in self.scene.items():
            if self._is_selectable_item(item):
                self.select_item(item, add_to_selection=True)
    
    def select_in_rect(self, rect: QRectF, add_to_selection: bool = False):
        """
        Select all items within a rectangle.
        
        Args:
            rect: Selection rectangle
            add_to_selection: If True, add to existing selection
        """
        if not add_to_selection:
            self.clear_selection()
        
        items_in_rect = self.scene.items(rect)
        for item in items_in_rect:
            if self._is_selectable_item(item):
                self.select_item(item, add_to_selection=True)
    
    def get_selected_shapes(self) -> List[Shape]:
        """Get list of currently selected shapes."""
        return self._selected_shapes.copy()
    
    def get_selected_items(self) -> List[QGraphicsItem]:
        """Get list of currently selected graphics items."""
        return list(self._selected_items)
    
    def get_selection_bounds(self) -> Optional[BoundingBox]:
        """
        Get bounding box of all selected items.
        
        Returns:
            BoundingBox encompassing all selections, or None if nothing selected
        """
        if not self._selected_shapes:
            return None
        
        all_points = []
        for shape in self._selected_shapes:
            paths = shape.get_paths()
            for path in paths:
                all_points.extend(path)
        
        if not all_points:
            return None
        
        return BoundingBox(
            min_x=min(p.x for p in all_points),
            min_y=min(p.y for p in all_points),
            max_x=max(p.x for p in all_points),
            max_y=max(p.y for p in all_points)
        )
    
    def start_selection_rect(self, point: QPointF):
        """
        Start selection rectangle (rubber band selection).
        
        Args:
            point: Starting point
        """
        self._is_selecting = True
        self._select_start = point
        
        # Create selection rectangle item
        from PyQt6.QtWidgets import QGraphicsRectItem
        rect = QRectF(point, point)
        self._selection_rect_item = QGraphicsRectItem(rect)
        
        # Style the selection rectangle
        pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
        brush = QBrush(QColor(0, 120, 215, 30))  # Semi-transparent
        self._selection_rect_item.setPen(pen)
        self._selection_rect_item.setBrush(brush)
        
        self.scene.addItem(self._selection_rect_item)
    
    def update_selection_rect(self, point: QPointF):
        """
        Update selection rectangle.
        
        Args:
            point: Current mouse position
        """
        if not self._is_selecting or not self._selection_rect_item or not self._select_start:
            return
        
        from PyQt6.QtCore import QRectF
        rect = QRectF(self._select_start, point).normalized()
        self._selection_rect_item.setRect(rect)
    
    def finish_selection_rect(self, point: QPointF, add_to_selection: bool = False):
        """
        Finish selection rectangle and select items within it.
        
        Args:
            point: End point
            add_to_selection: If True, add to existing selection
        """
        if not self._is_selecting or not self._selection_rect_item:
            return
        
        rect = self._selection_rect_item.rect()
        self.select_in_rect(rect, add_to_selection=add_to_selection)
        
        # Remove selection rectangle
        self.scene.removeItem(self._selection_rect_item)
        self._selection_rect_item = None
        self._is_selecting = False
        self._select_start = None
    
    def cancel_selection_rect(self):
        """Cancel selection rectangle."""
        if self._selection_rect_item:
            self.scene.removeItem(self._selection_rect_item)
            self._selection_rect_item = None
        self._is_selecting = False
        self._select_start = None
    
    def _add_handles(self, item: QGraphicsItem):
        """
        Add selection handles to an item.
        
        Args:
            item: Item to add handles to (ShapeGraphicsItem or EditableTextItem)
        """
        # Get bounding box
        bounds = item.boundingRect()
        
        # Calculate handle positions (corners and midpoints)
        corners = [
            QPointF(bounds.left(), bounds.top()),      # Top-left
            QPointF(bounds.right(), bounds.top()),     # Top-right
            QPointF(bounds.right(), bounds.bottom()),  # Bottom-right
            QPointF(bounds.left(), bounds.bottom()),   # Bottom-left
        ]
        
        midpoints = [
            QPointF(bounds.center().x(), bounds.top()),    # Top
            QPointF(bounds.right(), bounds.center().y()),  # Right
            QPointF(bounds.center().x(), bounds.bottom()), # Bottom
            QPointF(bounds.left(), bounds.center().y()),   # Left
        ]
        
        # Convert item-relative positions to scene coordinates
        item_scene_pos = item.scenePos()
        item_transform = item.sceneTransform()
        
        # Create handles with transform callbacks
        # Add handles directly to scene (not as children) so they're on top
        for corner in corners:
            # Convert to scene coordinates
            scene_corner = item_transform.map(corner)
            handle = SelectionHandleItem(scene_corner, "corner", None)  # No parent
            handle.set_transform_callback(self._on_handle_transform)
            handle.setZValue(item.zValue() + 100)  # Put handles on top
            self.scene.addItem(handle)
            self._handles.append(handle)
        
        for midpoint in midpoints:
            # Convert to scene coordinates
            scene_midpoint = item_transform.map(midpoint)
            handle = SelectionHandleItem(scene_midpoint, "edge", None)  # No parent
            handle.set_transform_callback(self._on_handle_transform)
            handle.setZValue(item.zValue() + 100)  # Put handles on top
            self.scene.addItem(handle)
            self._handles.append(handle)
        
        # Add rotation handle (above top-center, outside bounding box)
        rotation_handle_offset = 20.0  # Distance above top edge
        rotation_handle_pos = QPointF(
            bounds.center().x(),
            bounds.top() - rotation_handle_offset
        )
        # Convert to scene coordinates
        scene_rotation_pos = item_transform.map(rotation_handle_pos)
        rotation_handle = SelectionHandleItem(scene_rotation_pos, "rotation", None)  # No parent
        rotation_handle.set_transform_callback(self._on_handle_transform)
        rotation_handle.setZValue(item.zValue() + 100)  # Put handles on top
        self.scene.addItem(rotation_handle)
        self._handles.append(rotation_handle)
    
    def _remove_handles(self):
        """Remove all selection handles."""
        for handle in self._handles:
            self.scene.removeItem(handle)
        self._handles.clear()
    
    def _on_handle_transform(self, handle: SelectionHandleItem, event_type: str, pos: QPointF):
        """
        Handle transform events from selection handles.
        
        Args:
            handle: The handle that triggered the event
            event_type: "start", "update", or "finish"
            pos: Current position of the handle
        """
        selected_items = list(self._selected_items)
        if not selected_items:
            return
        
        if event_type == "start":
            # Start transform
            self._active_handle = handle
            self._transform_manager.start_transform(
                selected_items,
                pos,
                handle._handle_type
            )
        elif event_type == "update":
            # Update transform
            if self._active_handle == handle:
                self._transform_manager.update_transform(
                    selected_items,
                    pos,
                    handle._handle_type
                )
        elif event_type == "finish":
            # Finish transform
            if self._active_handle == handle:
                self._transform_manager.finish_transform()
                self._active_handle = None
                # Update handles positions after transform
                self._update_handles()
    
    def _update_handles(self):
        """Update handle positions after transformation."""
        # Remove old handles
        self._remove_handles()
        # Re-add handles at new positions
        for item in self._selected_items:
            if self._show_handles:
                self._add_handles(item)
    
    def mirror_horizontal(self):
        """Mirror selected shapes horizontally."""
        selected_items = list(self._selected_items)
        if selected_items:
            self._transform_manager.mirror_horizontal(selected_items)
            self._update_handles()
    
    def mirror_vertical(self):
        """Mirror selected shapes vertically."""
        selected_items = list(self._selected_items)
        if selected_items:
            self._transform_manager.mirror_vertical(selected_items)
            self._update_handles()
    
    def rotate(self, angle: float):
        """Rotate selected shapes by angle (in radians)."""
        selected_items = list(self._selected_items)
        if selected_items:
            self._transform_manager.rotate(selected_items, angle)
            self._update_handles()
    
    def set_show_handles(self, show: bool):
        """
        Enable or disable selection handles.
        
        Args:
            show: True to show handles, False to hide
        """
        self._show_handles = show
        if not show:
            self._remove_handles()
        elif self._selected_items:
            # Re-add handles for current selection
            for item in self._selected_items:
                self._add_handles(item)
    
    def delete_selection(self) -> List[Shape]:
        """
        Delete all selected shapes.
        
        Returns:
            List of deleted shapes
        """
        deleted = self._selected_shapes.copy()
        
        # Remove items from scene
        for item in list(self._selected_items):
            self.scene.removeItem(item)
        
        self.clear_selection()
        
        return deleted

