"""
Graphics Items for LaserBurn

Custom QGraphicsItems that wrap Shape objects for display in the canvas.
These items provide the visual representation and interaction capabilities.
"""

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QStyle
from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPainterPathStroker, QMouseEvent
from typing import Optional

from ..core.shapes import Shape, Point


class ShapeGraphicsItem(QGraphicsPathItem):
    """
    A QGraphicsItem that wraps a Shape for display.
    
    This item:
    - Renders the shape's path
    - Handles selection visualization
    - Stores reference to the underlying Shape
    - Provides hover effects
    """
    
    def __init__(self, shape: Shape, pen: QPen, parent: Optional[QGraphicsItem] = None):
        """
        Create a graphics item for a shape.
        
        Args:
            shape: The Shape object to display
            pen: QPen for drawing the shape
            parent: Optional parent item
        """
        super().__init__(parent)
        
        self._shape = shape
        self._base_pen = pen
        self._hover_pen = QPen(pen)
        self._hover_pen.setWidth(pen.width() + 1)
        
        # Create the path from shape
        self._update_path()
        
        # Make selectable and movable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Accept hover events for highlighting
        self.setAcceptHoverEvents(True)
        
        # Store shape reference in item data
        self.setData(0, shape)
    
    def _update_path(self):
        """Update the QPainterPath from the shape's paths."""
        paths = self._shape.get_paths()
        if not paths:
            return
        
        painter_path = QPainterPath()
        
        for path_points in paths:
            if not path_points or len(path_points) == 0:
                continue
            
            # Filter out paths with less than 2 points (can't draw a line with 1 point)
            if len(path_points) < 2:
                continue
            
            # Each subpath must start with moveTo to create disconnected subpaths
            # This ensures no connecting lines between subpaths
            painter_path.moveTo(path_points[0].x, path_points[0].y)
            
            # Add line segments for this subpath
            for point in path_points[1:]:
                painter_path.lineTo(point.x, point.y)
        
        self.setPath(painter_path)
    
    def shape(self) -> QPainterPath:
        """
        Return the shape for hit testing.
        
        This allows for better selection, especially for thin lines.
        """
        stroker = QPainterPathStroker()
        stroker.setWidth(5.0)  # Hit test area width
        return stroker.createStroke(self.path())
    
    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle."""
        rect = super().boundingRect()
        # Add padding for selection handles
        padding = 5.0
        return rect.adjusted(-padding, -padding, padding, padding)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        """
        Paint the item with selection highlighting.
        """
        # Use hover pen if hovering, otherwise base pen
        # In PyQt6, use QStyle.StateFlag for state checking
        if option.state & QStyle.StateFlag.State_Selected:
            # Selected: use selection color
            pen = QPen(QColor(0, 120, 215), self._base_pen.width() + 1)
            pen.setCosmetic(self._base_pen.isCosmetic())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            # Hovering: use hover pen
            pen = self._hover_pen
        else:
            # Normal: use base pen
            pen = self._base_pen
        
        painter.setPen(pen)
        painter.setBrush(QBrush())  # No brush
        painter.drawPath(self.path())
    
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        """
        Handle item changes (position, selection, etc.).
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update shape position when item is moved
            if self._shape:
                new_pos = self.pos()
                self._shape.position = Point(new_pos.x(), new_pos.y())
        
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event):
        """Handle mouse press - don't block if clicking on a handle."""
        # Check if there's a handle at this position
        # If so, let the handle handle it
        scene = self.scene()
        if scene:
            views = scene.views()
            if views:
                item_at_pos = scene.itemAt(event.scenePos(), views[0].transform())
                # Import here to avoid circular dependency
                from .items import SelectionHandleItem
                if item_at_pos and isinstance(item_at_pos, SelectionHandleItem):
                    # Let the handle handle the event
                    return
        super().mousePressEvent(event)
    
    def update_from_shape(self):
        """Update the graphics item when the underlying shape changes."""
        self._update_path()
        self.update()
    
    @property
    def shape_ref(self) -> Shape:
        """Get the underlying Shape object."""
        return self._shape


class SelectionHandleItem(QGraphicsItem):
    """
    A handle for manipulating selected shapes.
    
    These are the small squares that appear at corners/edges
    of selected items for resizing/rotating.
    """
    
    HANDLE_SIZE = 8.0
    
    def __init__(self, position: QPointF, handle_type: str = "corner", parent=None):
        """
        Create a selection handle.
        
        Args:
            position: Position of the handle
            handle_type: Type of handle ("corner", "edge", "rotation")
            parent: Parent item
        """
        super().__init__(parent)
        
        self._position = position
        self._handle_type = handle_type
        self._is_pressed = False
        self._start_pos: Optional[QPointF] = None
        self._transform_callback = None
        
        # Make it selectable and movable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Set position
        self.setPos(position)
        
        # Accept hover events
        self.setAcceptHoverEvents(True)
    
    def set_transform_callback(self, callback):
        """Set callback for transform events."""
        self._transform_callback = callback
    
    def boundingRect(self) -> QRectF:
        """Return bounding rectangle for the handle."""
        size = self.HANDLE_SIZE
        # Make hit area larger for easier clicking
        hit_padding = 4.0
        return QRectF(-size/2 - hit_padding, -size/2 - hit_padding, 
                      size + 2*hit_padding, size + 2*hit_padding)
    
    def shape(self) -> QPainterPath:
        """Return shape for hit testing - use larger area for easier clicking."""
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        size = self.HANDLE_SIZE
        hit_padding = 4.0
        path.addRect(QRectF(-size/2 - hit_padding, -size/2 - hit_padding, 
                            size + 2*hit_padding, size + 2*hit_padding))
        return path
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        """Paint the selection handle."""
        size = self.HANDLE_SIZE
        
        # Fill color based on state
        # In PyQt6, use QStyle.StateFlag for state checking
        if option.state & QStyle.StateFlag.State_Selected:
            fill_color = QColor(0, 120, 215)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            fill_color = QColor(100, 150, 255)
        else:
            fill_color = QColor(255, 255, 255)
        
        # Draw handle - use circle for rotation handle, square for others
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setBrush(QBrush(fill_color))
        
        if self._handle_type == "rotation":
            # Draw circle for rotation handle
            painter.drawEllipse(QRectF(-size/2, -size/2, size, size))
        else:
            # Draw square for corner/edge handles
            painter.drawRect(QRectF(-size/2, -size/2, size, size))
    
    def mousePressEvent(self, event):
        """Handle mouse press on handle."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            # Get scene position from the event
            scene_pos = event.scenePos()
            self._start_pos = scene_pos
            if self._transform_callback:
                self._transform_callback(self, "start", scene_pos)
            event.accept()  # Accept the event so parent doesn't get it
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move on handle."""
        if self._is_pressed and self._transform_callback:
            # Get scene position from the event
            scene_pos = event.scenePos()
            self._transform_callback(self, "update", scene_pos)
            event.accept()  # Accept the event
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release on handle."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_pressed:
            self._is_pressed = False
            if self._transform_callback:
                scene_pos = event.scenePos()
                self._transform_callback(self, "finish", scene_pos)
            self._start_pos = None
            event.accept()  # Accept the event
        else:
            super().mouseReleaseEvent(event)
    
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        """Handle position changes."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Position update is handled in mouseMoveEvent
            # We don't want to prevent the move, just track it
            pass
        
        return super().itemChange(change, value)

