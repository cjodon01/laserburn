"""
Drawing Tools for LaserBurn

Provides abstract base class and implementations for various drawing tools.
Each tool handles mouse interaction and shape creation.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from enum import Enum
from PyQt6.QtCore import QPointF, Qt, QRectF
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QPainterPath, QPen, QBrush
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsEllipseItem

from ..core.shapes import Shape, Point, Rectangle, Ellipse, Path, Text
from ..core.layer import Layer


class ToolType(Enum):
    """Types of drawing tools."""
    SELECT = "select"
    LINE = "line"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"
    TEXT = "text"
    PEN = "pen"
    NODE_EDIT = "node_edit"


class DrawingTool(ABC):
    """
    Abstract base class for drawing tools.
    
    Each tool implements:
    - Mouse press/move/release handling
    - Temporary item creation during drawing
    - Final shape creation
    """
    
    def __init__(self, tool_type: ToolType):
        self.tool_type = tool_type
        self._is_active = False
        self._start_point: Optional[QPointF] = None
        self._current_point: Optional[QPointF] = None
        self._temp_item: Optional[QGraphicsItem] = None
        self._points: List[QPointF] = []
    
    @abstractmethod
    def start_drawing(self, point: QPointF, scene) -> Optional[QGraphicsItem]:
        """
        Start drawing at the given point.
        
        Args:
            point: Starting point in scene coordinates
            scene: QGraphicsScene to add temporary items to
        
        Returns:
            Temporary QGraphicsItem for preview, or None
        """
        pass
    
    @abstractmethod
    def update_drawing(self, point: QPointF) -> None:
        """
        Update drawing as mouse moves.
        
        Args:
            point: Current mouse position in scene coordinates
        """
        pass
    
    @abstractmethod
    def finish_drawing(self, point: QPointF, layer: Layer) -> Optional[Shape]:
        """
        Finish drawing and create the final shape.
        
        Args:
            point: Final mouse position
            layer: Layer to add the shape to
        
        Returns:
            Created Shape object, or None if creation cancelled
        """
        pass
    
    def cancel_drawing(self, scene) -> None:
        """
        Cancel the current drawing operation.
        
        Args:
            scene: QGraphicsScene to remove temporary items from
        """
        if self._temp_item and scene:
            scene.removeItem(self._temp_item)
            self._temp_item = None
        self._is_active = False
        self._start_point = None
        self._current_point = None
        self._points = []
    
    def handle_key_press(self, event: QKeyEvent) -> bool:
        """
        Handle key press events.
        
        Args:
            event: Key event
        
        Returns:
            True if event was handled, False otherwise
        """
        if event.key() == Qt.Key.Key_Escape:
            return True  # Signal to cancel
        return False


class LineTool(DrawingTool):
    """Tool for drawing straight lines."""
    
    def __init__(self):
        super().__init__(ToolType.LINE)
    
    def start_drawing(self, point: QPointF, scene) -> Optional[QGraphicsItem]:
        """Start drawing a line."""
        self._is_active = True
        self._start_point = point
        self._current_point = point
        
        # Create temporary path item
        path = QPainterPath()
        path.moveTo(point)
        path.lineTo(point)
        
        item = QGraphicsPathItem(path)
        item.setPen(QPen(Qt.GlobalColor.cyan, 1))
        scene.addItem(item)
        self._temp_item = item
        
        return item
    
    def update_drawing(self, point: QPointF) -> None:
        """Update line endpoint."""
        if not self._temp_item or not self._start_point:
            return
        
        self._current_point = point
        
        # Update path
        path = QPainterPath()
        path.moveTo(self._start_point)
        path.lineTo(point)
        self._temp_item.setPath(path)
    
    def finish_drawing(self, point: QPointF, layer: Layer) -> Optional[Shape]:
        """Create a line Path shape."""
        if not self._start_point:
            return None
        
        # Create path shape
        path = Path()
        path.move_to(self._start_point.x(), self._start_point.y())
        path.line_to(point.x(), point.y())
        
        return path


class RectangleTool(DrawingTool):
    """Tool for drawing rectangles."""
    
    def __init__(self):
        super().__init__(ToolType.RECTANGLE)
    
    def start_drawing(self, point: QPointF, scene) -> Optional[QGraphicsItem]:
        """Start drawing a rectangle."""
        self._is_active = True
        self._start_point = point
        self._current_point = point
        
        # Create temporary rect item
        rect = QRectF(point, point)
        item = QGraphicsRectItem(rect)
        item.setPen(QPen(Qt.GlobalColor.cyan, 1))
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        scene.addItem(item)
        self._temp_item = item
        
        return item
    
    def update_drawing(self, point: QPointF) -> None:
        """Update rectangle size."""
        if not self._temp_item or not self._start_point:
            return
        
        self._current_point = point
        
        # Update rect
        rect = QRectF(self._start_point, point).normalized()
        self._temp_item.setRect(rect)
    
    def finish_drawing(self, point: QPointF, layer: Layer) -> Optional[Shape]:
        """Create a Rectangle shape."""
        if not self._start_point:
            return None
        
        rect = QRectF(self._start_point, point).normalized()
        
        shape = Rectangle(
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height()
        )
        
        return shape


class EllipseTool(DrawingTool):
    """Tool for drawing ellipses and circles."""
    
    def __init__(self):
        super().__init__(ToolType.ELLIPSE)
    
    def start_drawing(self, point: QPointF, scene) -> Optional[QGraphicsItem]:
        """Start drawing an ellipse."""
        self._is_active = True
        self._start_point = point
        self._current_point = point
        
        # Create temporary ellipse item
        rect = QRectF(point, point)
        item = QGraphicsEllipseItem(rect)
        item.setPen(QPen(Qt.GlobalColor.cyan, 1))
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        scene.addItem(item)
        self._temp_item = item
        
        return item
    
    def update_drawing(self, point: QPointF) -> None:
        """Update ellipse size."""
        if not self._temp_item or not self._start_point:
            return
        
        self._current_point = point
        
        # Update ellipse rect
        rect = QRectF(self._start_point, point).normalized()
        self._temp_item.setRect(rect)
    
    def finish_drawing(self, point: QPointF, layer: Layer) -> Optional[Shape]:
        """Create an Ellipse shape."""
        if not self._start_point:
            return None
        
        rect = QRectF(self._start_point, point).normalized()
        center = rect.center()
        
        shape = Ellipse(
            center.x(),
            center.y(),
            rect.width() / 2,
            rect.height() / 2
        )
        
        return shape


class PolygonTool(DrawingTool):
    """Tool for drawing polygons."""
    
    def __init__(self):
        super().__init__(ToolType.POLYGON)
        self._is_complete = False
    
    def start_drawing(self, point: QPointF, scene) -> Optional[QGraphicsItem]:
        """Start drawing a polygon."""
        self._is_active = True
        self._start_point = point
        self._points = [point]
        
        # Create temporary path item
        path = QPainterPath()
        path.moveTo(point)
        item = QGraphicsPathItem(path)
        item.setPen(QPen(Qt.GlobalColor.cyan, 1))
        scene.addItem(item)
        self._temp_item = item
        
        return item
    
    def update_drawing(self, point: QPointF) -> None:
        """Update polygon preview."""
        if not self._temp_item or not self._points:
            return
        
        self._current_point = point
        
        # Update path
        path = QPainterPath()
        path.moveTo(self._points[0])
        for p in self._points[1:]:
            path.lineTo(p)
        path.lineTo(point)
        self._temp_item.setPath(path)
    
    def add_point(self, point: QPointF) -> None:
        """Add a point to the polygon."""
        self._points.append(point)
        self.update_drawing(point)
    
    def finish_drawing(self, point: QPointF, layer: Layer) -> Optional[Shape]:
        """Create a polygon Path shape."""
        if len(self._points) < 2:
            return None
        
        # Create path shape
        path = Path()
        path.move_to(self._points[0].x(), self._points[0].y())
        for p in self._points[1:]:
            path.line_to(p.x(), p.y())
        
        # Close if we have at least 3 points
        if len(self._points) >= 3:
            path.close()
        
        return path
    
    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle Enter to finish polygon."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._is_complete = True
            return True
        return super().handle_key_press(event)


class PenTool(DrawingTool):
    """Tool for freehand drawing (pen tool)."""
    
    def __init__(self):
        super().__init__(ToolType.PEN)
        self._path_points: List[QPointF] = []
    
    def start_drawing(self, point: QPointF, scene) -> Optional[QGraphicsItem]:
        """Start freehand drawing."""
        self._is_active = True
        self._path_points = [point]
        
        # Create temporary path item
        path = QPainterPath()
        path.moveTo(point)
        item = QGraphicsPathItem(path)
        item.setPen(QPen(Qt.GlobalColor.cyan, 1))
        scene.addItem(item)
        self._temp_item = item
        
        return item
    
    def update_drawing(self, point: QPointF) -> None:
        """Add point to freehand path."""
        if not self._temp_item:
            return
        
        self._path_points.append(point)
        self._current_point = point
        
        # Update path
        path = QPainterPath()
        if self._path_points:
            path.moveTo(self._path_points[0])
            for p in self._path_points[1:]:
                path.lineTo(p)
        self._temp_item.setPath(path)
    
    def finish_drawing(self, point: QPointF, layer: Layer) -> Optional[Shape]:
        """Create a freehand Path shape."""
        if len(self._path_points) < 2:
            return None
        
        # Create path shape
        path = Path()
        path.move_to(self._path_points[0].x(), self._path_points[0].y())
        for p in self._path_points[1:]:
            path.line_to(p.x(), p.y())
        
        return path


class TextTool(DrawingTool):
    """Tool for creating text shapes with PowerPoint-style inline editing."""
    
    def __init__(self):
        super().__init__(ToolType.TEXT)
        self._font_family = "Arial"
        self._font_size = 24.0  # Default size in points
        self._bold = False
        self._italic = False
    
    def start_drawing(self, point: QPointF, scene) -> Optional[QGraphicsItem]:
        """Start text placement - creates editable text item immediately."""
        self._is_active = True
        self._start_point = point
        
        # Create editable text item (PowerPoint-style)
        from .text_item import EditableTextItem
        
        item = EditableTextItem(
            text="",  # Empty text to start editing immediately
            position=point,
            font_family=self._font_family,
            font_size=self._font_size,
            bold=self._bold,
            italic=self._italic
        )
        
        scene.addItem(item)
        self._temp_item = item
        
        return item
    
    def update_drawing(self, point: QPointF) -> None:
        """Update text position (not used for text tool)."""
        pass
    
    def finish_drawing(self, point: QPointF, layer: Layer) -> Optional[Shape]:
        """Create text shape from editable item."""
        from .text_item import EditableTextItem
        
        if not self._temp_item or not isinstance(self._temp_item, EditableTextItem):
            return None
        
        # Get text from item
        text = self._temp_item.toPlainText()
        if not text or not text.strip():
            return None
        
        # Convert to Text shape
        text_shape = self._temp_item.to_text_shape()
        return text_shape
    
    def set_font(self, family: str, size: float, bold: bool = False, italic: bool = False):
        """Set font properties."""
        self._font_family = family
        self._font_size = size
        self._bold = bold
        self._italic = italic
        # Update temp item if it exists
        if self._temp_item:
            from .text_item import EditableTextItem
            if isinstance(self._temp_item, EditableTextItem):
                font = QFont(family, int(size))
                font.setBold(bold)
                font.setItalic(italic)
                self._temp_item.setFont(font)


def create_tool(tool_type: ToolType) -> DrawingTool:
    """
    Factory function to create a tool instance.
    
    Args:
        tool_type: Type of tool to create
    
    Returns:
        DrawingTool instance
    """
    tool_map = {
        ToolType.LINE: LineTool,
        ToolType.RECTANGLE: RectangleTool,
        ToolType.ELLIPSE: EllipseTool,
        ToolType.POLYGON: PolygonTool,
        ToolType.PEN: PenTool,
        ToolType.TEXT: TextTool,
    }
    
    tool_class = tool_map.get(tool_type)
    if tool_class:
        return tool_class()
    
    raise ValueError(f"Unknown tool type: {tool_type}")

