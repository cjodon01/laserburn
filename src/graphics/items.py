"""
Graphics Items for LaserBurn

Custom QGraphicsItems that wrap Shape objects for display in the canvas.
These items provide the visual representation and interaction capabilities.
"""

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QStyle
from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPainterPathStroker, QMouseEvent, QImage, QPixmap
from typing import Optional

import numpy as np

from ..core.shapes import Shape, Point, ImageShape

# Import dithering functions with fallback
try:
    from ..image.dithering import adjust_brightness_contrast
    HAS_DITHERING = True
except ImportError:
    HAS_DITHERING = False
    def adjust_brightness_contrast(image, brightness=0.0, contrast=1.0, alpha_channel=None):
        """Fallback brightness/contrast adjustment."""
        result = image.copy().astype(np.float32)
        result = (result - 127.5) * contrast + 127.5 + brightness
        return np.clip(result, 0, 255).astype(np.uint8)


class ShapeGraphicsItem(QGraphicsPathItem):
    """
    A QGraphicsItem that wraps a Shape for display.
    
    This item:
    - Renders the shape's path
    - Handles selection visualization
    - Stores reference to the underlying Shape
    - Provides hover effects
    
    Position is handled via setPos() - paths are drawn in local coordinates.
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
        
        # Create the path from shape (in local coordinates)
        self._update_path()
        
        # Make selectable and movable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Accept hover events for highlighting
        self.setAcceptHoverEvents(True)
        
        # Store shape reference in item data
        self.setData(0, shape)
        
        # Set position from shape - this is the only positioning
        self.setPos(shape.position.x, shape.position.y)
    
    def _update_path(self):
        """Update the QPainterPath from the shape's paths in LOCAL coordinates."""
        paths = self._shape.get_paths()
        if not paths:
            return
        
        # Get shape position to convert to local coordinates
        offset_x = self._shape.position.x
        offset_y = self._shape.position.y
        
        painter_path = QPainterPath()
        
        for path_points in paths:
            if not path_points or len(path_points) == 0:
                continue
            
            # Filter out paths with less than 2 points (can't draw a line with 1 point)
            if len(path_points) < 2:
                continue
            
            # Each subpath must start with moveTo to create disconnected subpaths
            # Convert from world coordinates to local coordinates by subtracting position
            painter_path.moveTo(path_points[0].x - offset_x, path_points[0].y - offset_y)
            
            # Add line segments for this subpath
            for point in path_points[1:]:
                painter_path.lineTo(point.x - offset_x, point.y - offset_y)
        
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
        """Handle item changes (position, selection, etc.)."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update shape position when item is moved
            # This is the simple approach - just sync shape.position to item.pos()
            if self._shape:
                new_pos = self.pos()
                self._shape.position.x = new_pos.x()
                self._shape.position.y = new_pos.y()
        
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
            # Update position
            self.setPos(self._shape.position.x, self._shape.position.y)
        # Update path (in local coordinates)
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
        
        # Get image data
        img_data = self._shape.image_data.copy()
        alpha_channel = getattr(self._shape, 'alpha_channel', None)
        
        # Apply brightness/contrast adjustments for preview (transparent pixels not adjusted)
        brightness = getattr(self._shape, 'brightness', 0.0)
        contrast = getattr(self._shape, 'contrast', 1.0)
        
        if brightness != 0 or contrast != 1.0:
            img_data = adjust_brightness_contrast(img_data, brightness, contrast, alpha_channel)
        
        # Apply invert if enabled (transparent pixels not inverted)
        if getattr(self._shape, 'invert', False):
            if alpha_channel is not None:
                mask = alpha_channel >= 255
                img_data[mask] = 255 - img_data[mask]
            else:
                img_data = 255 - img_data
        
        # Apply dithering for canvas preview (at lower resolution for performance)
        # This matches what the user sees in the dialog preview
        dither_mode = getattr(self._shape, 'dither_mode', 'floyd_steinberg')
        threshold = getattr(self._shape, 'threshold', 128)
        
        # Downscale for dithering preview (max 512px width) to keep it fast
        max_preview_width = 512
        height, width = img_data.shape
        preview_scale = 1.0
        preview_img = img_data
        preview_alpha = alpha_channel
        
        if width > max_preview_width:
            preview_scale = max_preview_width / width
            new_width = max_preview_width
            new_height = int(height * preview_scale)
            
            # Downscale image and alpha for dithering
            try:
                from PIL import Image
                pil_img = Image.fromarray(img_data, mode='L')
                pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                preview_img = np.array(pil_img, dtype=np.uint8)
                
                if alpha_channel is not None:
                    pil_alpha = Image.fromarray(alpha_channel, mode='L')
                    pil_alpha = pil_alpha.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    preview_alpha = np.array(pil_alpha, dtype=np.uint8)
            except ImportError:
                # Fallback: use original image (no downscaling)
                preview_img = img_data
                preview_alpha = alpha_channel
        
        # Apply dithering to preview image
        try:
            from ..image.dithering import DitheringMethod, ImageDitherer
            # Map dither mode string to enum
            mode_map = {
                "none": DitheringMethod.NONE,
                "floyd_steinberg": DitheringMethod.FLOYD_STEINBERG,
                "jarvis": DitheringMethod.JARVIS_JUDICE_NINKE,
                "jarvis_judice_ninke": DitheringMethod.JARVIS_JUDICE_NINKE,
                "stucki": DitheringMethod.STUCKI,
                "atkinson": DitheringMethod.ATKINSON,
                "bayer_2x2": DitheringMethod.BAYER_2x2,
                "bayer_4x4": DitheringMethod.BAYER_4x4,
                "bayer_8x8": DitheringMethod.BAYER_8x8,
            }
            method = mode_map.get(dither_mode, DitheringMethod.FLOYD_STEINBERG)
            ditherer = ImageDitherer(method)
            preview_img = ditherer.dither(preview_img, threshold, preview_alpha)
            
            # Upscale back to original size if we downscaled
            if preview_scale < 1.0:
                try:
                    from PIL import Image
                    pil_dithered = Image.fromarray(preview_img, mode='L')
                    pil_dithered = pil_dithered.resize((width, height), Image.Resampling.NEAREST)
                    img_data = np.array(pil_dithered, dtype=np.uint8)
                except ImportError:
                    # Fallback: use original image without dithering (can't upscale without PIL)
                    # This means we show the non-dithered version, but at least it matches dimensions
                    pass
            else:
                # No downscaling was done, use dithered result directly
                img_data = preview_img
        except ImportError:
            # Dithering module not available - skip dithering, use original img_data
            pass
        
        # Ensure we have the correct dimensions
        height, width = img_data.shape
        
        # Create RGBA image to show transparency properly
        if alpha_channel is not None:
            # Create checkerboard pattern for transparent areas (like LightBurn)
            checkerboard = self._create_checkerboard(width, height, 8)
            
            # Composite image onto checkerboard for transparent areas
            rgb_data = np.stack([img_data, img_data, img_data], axis=-1)
            alpha_3d = alpha_channel[:, :, np.newaxis] / 255.0
            
            # Blend: transparent areas show checkerboard, opaque areas show image
            composite = (rgb_data * alpha_3d + checkerboard * (1 - alpha_3d)).astype(np.uint8)
            
            # Create RGBA image
            rgba_data = np.zeros((height, width, 4), dtype=np.uint8)
            rgba_data[:, :, :3] = composite
            rgba_data[:, :, 3] = 255  # Full opacity for display
            
            bytes_per_line = 4 * width
            qimage = QImage(
                rgba_data.tobytes(),
                width, height,
                bytes_per_line,
                QImage.Format.Format_RGBA8888
            )
        else:
            # No transparency - convert grayscale to RGB
            rgb_data = np.stack([img_data, img_data, img_data], axis=-1)
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
    
    def _create_checkerboard(self, width: int, height: int, tile_size: int = 8) -> np.ndarray:
        """Create a checkerboard pattern for transparent areas (vectorized for speed)."""
        # Create coordinate arrays
        y_coords = np.arange(height) // tile_size
        x_coords = np.arange(width) // tile_size
        
        # Create meshgrid and checkerboard mask
        yy, xx = np.meshgrid(y_coords, x_coords, indexing='ij')
        mask = (xx + yy) % 2 == 0
        
        # Create pattern using broadcasting (fast)
        pattern = np.zeros((height, width, 3), dtype=np.uint8)
        pattern[mask] = [240, 240, 240]  # Light gray
        pattern[~mask] = [200, 200, 200]  # Darker gray
        
        return pattern
    
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

