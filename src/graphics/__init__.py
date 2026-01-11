"""
LaserBurn Graphics Module

Contains the graphics/rendering components:
- Items: Custom QGraphicsItems for shapes
- Tools: Drawing and editing tools
- Selection: Selection handling
"""

from .items import ShapeGraphicsItem, SelectionHandleItem, ImageGraphicsItem
from .text_item import EditableTextItem
from .tools import (
    DrawingTool, LineTool, RectangleTool, EllipseTool,
    PolygonTool, PenTool, TextTool, ToolType, create_tool
)
from .selection import SelectionManager
from .transform import TransformManager

__all__ = [
    # Items
    'ShapeGraphicsItem',
    'SelectionHandleItem',
    'ImageGraphicsItem',
    'EditableTextItem',
    # Tools
    'DrawingTool',
    'LineTool',
    'RectangleTool',
    'EllipseTool',
    'PolygonTool',
    'PenTool',
    'TextTool',
    'ToolType',
    'create_tool',
    # Selection
    'SelectionManager',
    # Transform
    'TransformManager',
]
