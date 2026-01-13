"""
Graphics Items for LaserBurn

Custom QGraphicsItems that wrap Shape objects for display in the canvas.
These items provide the visual representation and interaction capabilities.
"""

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QStyle
from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPainterPathStroker, QMouseEvent, QImage, QPixmap
from typing import Optional

from ..core.shapes import Shape, Point, ImageShape


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
            # The paths include position already, so we need to:
            # 1. Calculate delta from item's pos() movement
            # 2. Add delta to shape.position
            # 3. Rebuild path (which will include new position)
            # 4. Reset item pos() to 0,0
            if self._shape:
                new_pos = self.pos()
                if new_pos.x() != 0 or new_pos.y() != 0:
                    print(f"[ShapeGraphicsItem] itemChange: Item moved, new_pos=({new_pos.x():.2f}, {new_pos.y():.2f})")
                    print(f"  shape.position before=({self._shape.position.x:.2f}, {self._shape.position.y:.2f})")
                    # Add movement delta to shape position
                    self._shape.position.x += new_pos.x()
                    self._shape.position.y += new_pos.y()
                    print(f"  shape.position after=({self._shape.position.x:.2f}, {self._shape.position.y:.2f})")
                    # Rebuild path with new position baked in
                    self._update_path()
                    # Reset item position (path now includes the position)
                    self.setPos(0, 0)
                    print(f"  Reset item pos to (0, 0)")
        
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
        if self._shape:
            print(f"[ShapeGraphicsItem] update_from_shape: shape_id={self._shape.id}")
            print(f"  shape.position=({self._shape.position.x:.2f}, {self._shape.position.y:.2f})")
            print(f"  shape.scale=({self._shape.scale_x:.3f}, {self._shape.scale_y:.3f})")
            if hasattr(self._shape, 'rotation'):
                import math
                print(f"  shape.rotation={math.degrees(self._shape.rotation):.2f}°")
        self._update_path()
        self.update()
    
    @property
    def shape_ref(self) -> Shape:
        """Get the underlying Shape object."""
        return self._shape


class ImageGraphicsItem(QGraphicsItem):
    """
    A QGraphicsItem that displays an ImageShape.
    
    This renders the actual image data, not just an outline.
    Position is handled via setPos(), scale/rotation are applied in paint().
    """
    
    def __init__(self, image_shape: ImageShape, parent: Optional[QGraphicsItem] = None):
        """
        Create a graphics item for an image shape.
        
        Args:
            image_shape: The ImageShape object to display
            parent: Optional parent item
        """
        super().__init__(parent)
        
        self._shape = image_shape
        self._pixmap: Optional[QPixmap] = None
        
        # Create the pixmap from image data
        self._update_pixmap()
        
        # Make selectable and movable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Accept hover events for highlighting
        self.setAcceptHoverEvents(True)
        
        # Store shape reference in item data
        self.setData(0, image_shape)
        
        # Set position - this is the only positioning, no transform for position
        self.setPos(image_shape.position.x, image_shape.position.y)
    
    def _update_pixmap(self):
        """Update the QPixmap from the image shape's data with adjustments applied."""
        if self._shape.image_data is None:
            self._pixmap = None
            return
        
        import numpy as np
        
        # Get image data
        img_data = self._shape.image_data.copy()
        
        # Apply brightness/contrast adjustments for preview
        brightness = getattr(self._shape, 'brightness', 0.0)
        contrast = getattr(self._shape, 'contrast', 1.0)
        
        if brightness != 0 or contrast != 1.0:
            # Apply brightness and contrast
            img_float = img_data.astype(np.float32)
            img_float = (img_float - 127.5) * contrast + 127.5
            img_float += brightness
            img_data = np.clip(img_float, 0, 255).astype(np.uint8)
        
        # Apply invert if enabled
        if getattr(self._shape, 'invert', False):
            img_data = 255 - img_data
        
        height, width = img_data.shape
        
        # Convert grayscale to RGB for QImage
        rgb_data = np.stack([img_data, img_data, img_data], axis=-1)
        
        # Create QImage from numpy array
        bytes_per_line = 3 * width
        qimage = QImage(
            rgb_data.tobytes(),
            width, height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
        
        # Scale to display size (3 pixels per mm for display)
        scaled_image = qimage.scaled(
            int(self._shape.width * 3),
            int(self._shape.height * 3),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self._pixmap = QPixmap.fromImage(scaled_image)
    
    def refresh(self):
        """Refresh the pixmap to reflect setting changes."""
        self._update_pixmap()
        self.prepareGeometryChange()
        self.update()
    
    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle (actual size including scale)."""
        if self._shape:
            # Return ACTUAL size (base * scale) so handles appear at correct positions
            actual_width = self._shape.width * abs(self._shape.scale_x)
            actual_height = self._shape.height * abs(self._shape.scale_y)
            return QRectF(0, 0, actual_width, actual_height)
        return QRectF(0, 0, 100, 100)
    
    def shape(self) -> QPainterPath:
        """Return the shape for hit testing."""
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        """Paint the image with scale and rotation applied."""
        if not self._shape:
            return
        
        import math
        
        # Get actual size
        actual_width = self._shape.width * abs(self._shape.scale_x)
        actual_height = self._shape.height * abs(self._shape.scale_y)
        rect = QRectF(0, 0, actual_width, actual_height)
        
        # Save painter state
        painter.save()
        
        # Apply rotation around center
        if abs(self._shape.rotation) > 0.001:
            center = rect.center()
            painter.translate(center)
            painter.rotate(math.degrees(self._shape.rotation))
            painter.translate(-center)
        
        # Handle negative scale (mirroring)
        if self._shape.scale_x < 0 or self._shape.scale_y < 0:
            center = rect.center()
            painter.translate(center)
            painter.scale(
                -1 if self._shape.scale_x < 0 else 1,
                -1 if self._shape.scale_y < 0 else 1
            )
            painter.translate(-center)
        
        # Draw image or placeholder
        if self._pixmap and not self._pixmap.isNull():
            painter.drawPixmap(rect.toRect(), self._pixmap)
        else:
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setBrush(QBrush(QColor(60, 60, 60)))
            painter.drawRect(rect)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Image")
        
        painter.restore()
        
        # Draw selection/hover border (not rotated - around bounding box)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.setBrush(QBrush())
            painter.drawRect(rect)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.setPen(QPen(QColor(100, 150, 255), 1))
            painter.setBrush(QBrush())
            painter.drawRect(rect)
    
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        """Handle item changes (position, selection, etc.)."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update shape position when item is moved
            if self._shape:
                new_pos = self.pos()
                self._shape.position.x = new_pos.x()
                self._shape.position.y = new_pos.y()
        
        return super().itemChange(change, value)
    
    def update_from_shape(self):
        """Update the graphics item when the underlying shape changes."""
        # Notify Qt that geometry is changing
        self.prepareGeometryChange()
        
        if self._shape:
            # Update position
            self.setPos(self._shape.position.x, self._shape.position.y)
        
        # Update pixmap (applies brightness/contrast/invert settings)
        self._update_pixmap()
        
        # Trigger repaint
        self.update()
    
    @property
    def shape_ref(self) -> ImageShape:
        """Get the underlying ImageShape object."""
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
            print(f"[HANDLE] mousePressEvent: handle_type={self._handle_type}, scene_pos=({scene_pos.x():.2f}, {scene_pos.y():.2f})")
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
            print(f"[HANDLE] mouseMoveEvent: handle_type={self._handle_type}, scene_pos=({scene_pos.x():.2f}, {scene_pos.y():.2f})")
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
                print(f"[HANDLE] mouseReleaseEvent: handle_type={self._handle_type}, scene_pos=({scene_pos.x():.2f}, {scene_pos.y():.2f})")
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

