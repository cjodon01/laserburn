"""
LaserBurn Canvas - Main drawing and editing surface.

Uses Qt's Graphics View Framework for efficient rendering
and interaction with vector graphics.
"""

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QGraphicsRectItem, QGraphicsEllipseItem, QDialog
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QLineF, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QWheelEvent, QMouseEvent, QKeyEvent
)
from typing import List, Optional
from enum import Enum

from ..core.document import Document
from ..core.layer import Layer
from ..core.shapes import Shape, Point, Rectangle, Ellipse, Path, Text
from ..graphics import (
    ShapeGraphicsItem, SelectionManager,
    ToolType, create_tool, DrawingTool, PolygonTool
)
from ..graphics.items import SelectionHandleItem


class LaserCanvas(QGraphicsView):
    """
    Main canvas for displaying and editing designs.
    
    Features:
    - Zoom and pan
    - Grid display
    - Shape rendering
    - Tool handling
    - Selection
    - Snapping
    """
    
    # Signals
    selection_changed = pyqtSignal(list)  # List of selected shapes
    cursor_position = pyqtSignal(float, float)  # Mouse position in mm
    zoom_changed = pyqtSignal(float)  # Current zoom level
    
    def __init__(self, document: Document):
        super().__init__()
        
        self.document = document
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        # Canvas state
        self._zoom = 1.0
        self._canvas_rotation = -90.0  # Rotate canvas 90° CCW to match laser orientation
        self._current_tool_type = ToolType.SELECT
        self._current_drawing_tool: Optional[DrawingTool] = None
        self._is_panning = False
        self._pan_start = QPointF()
        self._is_drawing = False
        self._draw_start = QPointF()
        self._temp_item: Optional[QGraphicsItem] = None
        self._selected_items: List[QGraphicsItem] = []
        self._active_layer: Optional[Layer] = None
        
        # Selection manager
        self._selection_manager = SelectionManager(self.scene)
        self._selection_manager.selection_changed.connect(self._on_selection_changed)
        
        # Grid settings
        self._show_grid = True
        self._grid_spacing = 10.0  # mm
        self._snap_to_grid = True
        self._snap_distance = 2.0  # pixels
        
        # Colors
        self._background_color = QColor(40, 40, 40)
        self._grid_color = QColor(60, 60, 60)
        self._grid_color_major = QColor(80, 80, 80)
        self._workspace_color = QColor(50, 50, 50)
        self._selection_color = QColor(0, 120, 215)
        
        # Setup
        self._setup_scene()
        self._update_view()
        
        # Set active layer
        if document.layers:
            self._active_layer = document.layers[0]
    
    def _setup_scene(self):
        """Initialize scene with workspace."""
        # Set scene rect larger than workspace for scrolling
        padding = 100
        self.scene.setSceneRect(
            -padding, -padding,
            self.document.width + 2 * padding,
            self.document.height + 2 * padding
        )
        
        # Background is handled in drawBackground
        self.setBackgroundBrush(QBrush(self._background_color))
    
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw background with grid."""
        # Draw scene background
        painter.fillRect(rect, self._background_color)
        
        # Draw workspace area
        workspace = QRectF(0, 0, self.document.width, self.document.height)
        painter.fillRect(workspace, self._workspace_color)
        
        # Draw grid if enabled
        if self._show_grid:
            painter.setPen(QPen(self._grid_color, 0.5))
            
            # Calculate grid bounds
            left = int(rect.left() // self._grid_spacing) * self._grid_spacing
            right = rect.right()
            top = int(rect.top() // self._grid_spacing) * self._grid_spacing
            bottom = rect.bottom()
            
            # Draw vertical lines
            x = left
            while x <= right:
                if 0 <= x <= self.document.width:
                    line = QLineF(x, max(0.0, rect.top()), x, min(float(self.document.height), rect.bottom()))
                    painter.drawLine(line)
                x += self._grid_spacing
            
            # Draw horizontal lines
            y = top
            while y <= bottom:
                if 0 <= y <= self.document.height:
                    line = QLineF(max(0.0, rect.left()), y, min(float(self.document.width), rect.right()), y)
                    painter.drawLine(line)
                y += self._grid_spacing
            
            # Draw major grid lines (every 5th line)
            painter.setPen(QPen(self._grid_color_major, 1))
            x = left
            major_count = 0
            while x <= right:
                if 0 <= x <= self.document.width and major_count % 5 == 0:
                    line = QLineF(x, max(0.0, rect.top()), x, min(float(self.document.height), rect.bottom()))
                    painter.drawLine(line)
                x += self._grid_spacing
                major_count += 1
            
            y = top
            major_count = 0
            while y <= bottom:
                if 0 <= y <= self.document.height and major_count % 5 == 0:
                    line = QLineF(max(0.0, rect.left()), y, min(float(self.document.width), rect.right()), y)
                    painter.drawLine(line)
                y += self._grid_spacing
                major_count += 1
        
        # Draw workspace border
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(workspace)
        
        # Draw grid labels (numbers on the edges)
        if self._show_grid:
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            
            # Draw X axis labels (along bottom, origin at bottom-left like laser)
            major_spacing = self._grid_spacing * 5  # Major grid spacing
            x = 0
            while x <= self.document.width:
                if x >= 0:
                    # Draw at bottom edge (outside workspace)
                    label_rect = QRectF(x - 15, self.document.height + 2, 30, 12)
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, f"{int(x)}")
                x += major_spacing
            
            # Draw Y axis labels (along left, Y increases upward to match laser)
            y = 0
            while y <= self.document.height:
                if y >= 0:
                    # Draw at left edge (outside workspace)
                    # Y coordinate on canvas = document.height - laser_y to flip Y axis
                    laser_y = self.document.height - y  # Flip for display
                    label_rect = QRectF(-25, y - 6, 23, 12)
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{int(laser_y)}")
                y += major_spacing
            
            # Draw axis labels
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            font.setBold(True)
            painter.setFont(font)
            # X axis label
            painter.drawText(QRectF(self.document.width / 2 - 10, self.document.height + 14, 20, 14), 
                           Qt.AlignmentFlag.AlignCenter, "X")
            # Y axis label
            painter.drawText(QRectF(-35, self.document.height / 2 - 7, 14, 14), 
                           Qt.AlignmentFlag.AlignCenter, "Y")
            
            # Draw origin marker (0,0 at bottom-left of laser = top-left of screen)
            painter.setPen(QPen(QColor(255, 100, 100), 2))
            painter.drawLine(QLineF(-5, self.document.height, 5, self.document.height))
            painter.drawLine(QLineF(0, self.document.height - 5, 0, self.document.height + 5))
    
    def set_document(self, document: Document):
        """Set the document to display."""
        self.document = document
        self._setup_scene()
        self._update_view()
        
        if document.layers:
            self._active_layer = document.layers[0]
    
    def set_active_layer(self, layer: Layer):
        """Set the active layer for drawing."""
        self._active_layer = layer
    
    def set_tool(self, tool_type: ToolType):
        """Set the current drawing tool."""
        self._current_tool_type = tool_type
        
        # Cancel any active drawing
        if self._is_drawing and self._current_drawing_tool:
            self._current_drawing_tool.cancel_drawing(self.scene)
            self._is_drawing = False
        
        # Create tool instance if it's a drawing tool
        if tool_type == ToolType.SELECT:
            self._current_drawing_tool = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            try:
                self._current_drawing_tool = create_tool(tool_type)
                self.setCursor(Qt.CursorShape.CrossCursor)
            except ValueError:
                # Tool not implemented yet
                self._current_drawing_tool = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _update_view(self):
        """Refresh the view with current document state."""
        try:
            from ..graphics.text_item import EditableTextItem
            from ..core.shapes import Text as TextShape
            
            # Clear existing items (except temp item and EditableTextItems)
            items_to_remove = []
            text_items_to_keep = {}  # Map shape ID to item
            
            for item in self.scene.items():
                if item == self._temp_item:
                    continue
                # Keep EditableTextItems - we'll update them instead of removing
                if isinstance(item, EditableTextItem):
                    shape = item.data(0)
                    if shape and hasattr(shape, 'id'):
                        text_items_to_keep[shape.id] = item
                    continue
                items_to_remove.append(item)
            
            for item in items_to_remove:
                self.scene.removeItem(item)
            
            # Add shapes from all layers
            for layer in self.document.layers:
                if not layer.visible:
                    continue
                
                try:
                    color = QColor(layer.color)
                    pen = QPen(color, 1)
                    pen.setCosmetic(True)  # Constant width regardless of zoom
                    
                    for shape in layer.shapes:
                        if not shape.visible:
                            continue
                        
                        try:
                            # Handle Text shapes specially - use EditableTextItem
                            if isinstance(shape, TextShape):
                                # Check if we already have an item for this shape
                                if shape.id in text_items_to_keep:
                                    # Update existing item
                                    item = text_items_to_keep[shape.id]
                                    item.set_text_shape(shape)
                                else:
                                    # Create new EditableTextItem
                                    item = EditableTextItem(
                                        text=shape.text,
                                        position=QPointF(shape.position.x, shape.position.y),
                                        font_family=shape.font_family,
                                        font_size=shape.font_size,
                                        bold=shape.bold,
                                        italic=shape.italic
                                    )
                                    item.set_text_shape(shape)
                                    # Connect signals for editing
                                    item.editing_finished.connect(self._on_text_editing_finished)
                                    item.editing_cancelled.connect(self._on_text_editing_cancelled)
                                    item.setData(0, shape)  # Store shape reference
                                    item.setData(1, layer)  # Store layer reference
                                    self.scene.addItem(item)
                            else:
                                # Use regular graphics item for other shapes
                                item = self._create_graphics_item(shape, pen)
                                if item:
                                    item.setData(0, shape)  # Store shape reference
                                    item.setData(1, layer)  # Store layer reference
                                    self.scene.addItem(item)
                        except Exception as e:
                            print(f"Error creating graphics item for shape: {e}")
                            continue
                except Exception as e:
                    print(f"Error processing layer {layer.name}: {e}")
                    continue
        except Exception as e:
            print(f"Error in _update_view: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_graphics_item(self, shape: Shape, 
                              pen: QPen) -> Optional[QGraphicsItem]:
        """Create a QGraphicsItem from a Shape using ShapeGraphicsItem."""
        try:
            item = ShapeGraphicsItem(shape, pen)
            return item
        except Exception as e:
            print(f"Error creating ShapeGraphicsItem: {e}")
            # Fallback to old method if ShapeGraphicsItem fails
            paths = shape.get_paths()
            if not paths:
                return None
            
            painter_path = QPainterPath()
            is_first_subpath = True
            for path_points in paths:
                if not path_points or len(path_points) == 0:
                    continue
                
                if len(path_points) > 0:
                    if is_first_subpath:
                        painter_path.moveTo(path_points[0].x, path_points[0].y)
                        is_first_subpath = False
                    else:
                        painter_path.moveTo(path_points[0].x, path_points[0].y)
                    
                    for point in path_points[1:]:
                        painter_path.lineTo(point.x, point.y)
            
            item = QGraphicsPathItem(painter_path)
            item.setPen(pen)
            item.setBrush(QBrush())
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            return item
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        scene_pos = self.mapToScene(event.pos())
        
        # Middle button or Space+Left = Pan
        if (event.button() == Qt.MouseButton.MiddleButton or
            (event.button() == Qt.MouseButton.LeftButton and
             event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        
        # Handle based on current tool
        if event.button() == Qt.MouseButton.LeftButton:
            if self._current_tool_type == ToolType.SELECT:
                # Check if clicking on a handle first - if so, let it handle the event
                item = self.itemAt(event.pos())
                from ..graphics.text_item import EditableTextItem
                
                if item and isinstance(item, SelectionHandleItem):
                    # Let the handle handle the event - don't interfere
                    super().mousePressEvent(event)
                    return
                
                # Check if clicking on a text item
                if item and isinstance(item, EditableTextItem):
                    # Select the text item (it's already selectable)
                    add_to_selection = (event.modifiers() & Qt.KeyboardModifier.ControlModifier) != 0
                    if not add_to_selection:
                        self.scene.clearSelection()
                    item.setSelected(True)
                    self._update_selection()
                    super().mousePressEvent(event)
                    return
                
                # Check if clicking on a shape item
                if item and isinstance(item, ShapeGraphicsItem):
                    # Use SelectionManager to handle selection
                    add_to_selection = (event.modifiers() & Qt.KeyboardModifier.ControlModifier) != 0
                    self._selection_manager.select_item(item, add_to_selection=add_to_selection)
                else:
                    # Clicked on empty space - clear selection
                    self._selection_manager.clear_selection()
                # Still call super to handle other events
                super().mousePressEvent(event)
            elif self._current_drawing_tool:
                # Handle polygon tool specially (multi-click)
                if self._current_tool_type == ToolType.POLYGON:
                    if not self._is_drawing:
                        # Start new polygon
                        self._is_drawing = True
                        self._draw_start = self._snap_point(scene_pos)
                        self._temp_item = self._current_drawing_tool.start_drawing(
                            self._draw_start, self.scene
                        )
                    else:
                        # Add point to existing polygon
                        snapped = self._snap_point(scene_pos)
                        if isinstance(self._current_drawing_tool, PolygonTool):
                            self._current_drawing_tool.add_point(snapped)
                elif self._current_tool_type == ToolType.TEXT:
                    # Text tool: create editable text item immediately (PowerPoint-style)
                    if not self._is_drawing:
                        self._is_drawing = True
                        self._draw_start = self._snap_point(scene_pos)
                        # Create editable text item
                        from ..graphics.text_item import EditableTextItem
                        
                        if not self._active_layer:
                            if self.document.layers:
                                self._active_layer = self.document.layers[0]
                            else:
                                self._active_layer = Layer(name="Layer 1")
                                self.document.add_layer(self._active_layer)
                        
                        # Create editable text item
                        text_item = EditableTextItem(
                            text="",
                            position=self._draw_start,
                            font_family=getattr(self._current_drawing_tool, '_font_family', 'Arial'),
                            font_size=getattr(self._current_drawing_tool, '_font_size', 24.0),
                            bold=getattr(self._current_drawing_tool, '_bold', False),
                            italic=getattr(self._current_drawing_tool, '_italic', False)
                        )
                        
                        # Connect signals
                        text_item.editing_finished.connect(self._on_text_editing_finished)
                        text_item.editing_cancelled.connect(self._on_text_editing_cancelled)
                        
                        self.scene.addItem(text_item)
                        self._temp_item = text_item
                        # Start editing immediately
                        text_item.start_editing()
                else:
                    # Start drawing with the tool
                    self._is_drawing = True
                    self._draw_start = self._snap_point(scene_pos)
                    self._temp_item = self._current_drawing_tool.start_drawing(
                        self._draw_start, self.scene
                    )
            else:
                # Fallback to old drawing logic for tools not yet using new system
                self._is_drawing = True
                self._draw_start = self._snap_point(scene_pos)
                self._start_drawing(self._draw_start)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        scene_pos = self.mapToScene(event.pos())
        
        # Emit cursor position
        self.cursor_position.emit(scene_pos.x(), scene_pos.y())
        
        # Handle panning
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            return
        
        # Handle drawing - update temporary shape
        if self._is_drawing:
            snapped = self._snap_point(scene_pos)
            if self._current_drawing_tool:
                # For polygon tool, only update preview (don't add point on move)
                if self._current_tool_type == ToolType.POLYGON:
                    if isinstance(self._current_drawing_tool, PolygonTool):
                        # Update preview line from last point to current mouse position
                        # This shows where the next line will go
                        self._current_drawing_tool.update_drawing(snapped)
                else:
                    # For other tools, update normally
                    self._current_drawing_tool.update_drawing(snapped)
            else:
                self._update_drawing(snapped)
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        
        if self._is_drawing:
            if event.button() == Qt.MouseButton.LeftButton:
                # For polygon tool, left click adds points, doesn't finish
                if self._current_tool_type == ToolType.POLYGON:
                    # Point was already added in mousePressEvent
                    # Continue drawing (don't finish) - user can add more points
                    # or right-click/Enter to finish
                    return
                elif self._current_tool_type == ToolType.TEXT:
                    # Text tool: editing is handled by EditableTextItem signals
                    # Don't finish here - let the item handle it
                    return
                else:
                    # Finish drawing for other tools
                    scene_pos = self.mapToScene(event.pos())
                    snapped = self._snap_point(scene_pos)
                    if self._current_drawing_tool:
                        self._finish_drawing_with_tool(snapped)
                    else:
                        self._finish_drawing(snapped)
            elif event.button() == Qt.MouseButton.RightButton:
                # Right click finishes polygon
                if self._current_tool_type == ToolType.POLYGON and self._current_drawing_tool:
                    # Finish the polygon (don't add the right-click point)
                    if isinstance(self._current_drawing_tool, PolygonTool):
                        # Use the last added point, not the right-click position
                        if self._current_drawing_tool._points:
                            last_point = self._current_drawing_tool._points[-1]
                            self._finish_drawing_with_tool(last_point)
                        else:
                            # No points added, cancel
                            self._cancel_drawing()
                    else:
                        scene_pos = self.mapToScene(event.pos())
                        snapped = self._snap_point(scene_pos)
                        self._finish_drawing_with_tool(snapped)
        else:
            super().mouseReleaseEvent(event)
            self._update_selection()
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.01, min(100, self._zoom))
        
        self.scale(factor, factor)
        self.zoom_changed.emit(self._zoom)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press."""
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selection()
        elif event.key() == Qt.Key.Key_Escape:
            if self._is_drawing and self._current_drawing_tool:
                self._current_drawing_tool.cancel_drawing(self.scene)
                self._is_drawing = False
                self._temp_item = None
            else:
                self._clear_selection()
        elif self._current_drawing_tool:
            # Let tool handle key events
            if self._current_drawing_tool.handle_key_press(event):
                # Tool handled it (e.g., Enter to finish polygon)
                if isinstance(self._current_drawing_tool, PolygonTool) and self._current_drawing_tool._is_complete:
                    # Finish polygon using last point
                    if self._current_drawing_tool._points:
                        last_point = self._current_drawing_tool._points[-1]
                        self._finish_drawing_with_tool(last_point)
                    else:
                        self._cancel_drawing()
        else:
            super().keyPressEvent(event)
    
    def _update_selection(self):
        """Update selection state using SelectionManager."""
        from ..graphics.text_item import EditableTextItem
        
        # Collect selected shapes from scene items
        selected_shapes = []
        for item in self.scene.selectedItems():
            if isinstance(item, EditableTextItem):
                shape = item.data(0)
                if shape:
                    selected_shapes.append(shape)
            elif isinstance(item, ShapeGraphicsItem):
                shape = item.shape_ref
                if shape:
                    selected_shapes.append(shape)
            else:
                # Try to get shape from data
                shape = item.data(0)
                if shape:
                    selected_shapes.append(shape)
        
        # Also get from SelectionManager for consistency
        manager_shapes = self._selection_manager.get_selected_shapes()
        # Combine and deduplicate
        all_shapes = selected_shapes + [s for s in manager_shapes if s not in selected_shapes]
        
        self.selection_changed.emit(all_shapes)
    
    def _clear_selection(self):
        """Clear all selection."""
        self.scene.clearSelection()
        self._update_selection()
    
    def _delete_selection(self):
        """Delete selected shapes."""
        from ..graphics.text_item import EditableTextItem
        
        items_to_delete = []
        shapes_to_remove = []
        
        # Collect all items to delete
        for item in self.scene.selectedItems():
            # Handle EditableTextItem specially
            if isinstance(item, EditableTextItem):
                shape = item.data(0)
                layer = item.data(1)
                if shape and layer:
                    shapes_to_remove.append((shape, layer))
                    items_to_delete.append(item)
            else:
                # Handle regular ShapeGraphicsItem
                shape = item.data(0)
                layer = item.data(1)
                if shape and layer:
                    shapes_to_remove.append((shape, layer))
                    items_to_delete.append(item)
        
        # Remove shapes from layers
        for shape, layer in shapes_to_remove:
            if shape in layer.shapes:
                layer.remove_shape(shape)
        
        # Remove items from scene
        for item in items_to_delete:
            self.scene.removeItem(item)
        
        # Clear selection
        self.scene.clearSelection()
        
        self._update_view()
        self._update_selection()
    
    def select_all(self):
        """Select all shapes."""
        from ..graphics.text_item import EditableTextItem
        from ..graphics.items import SelectionHandleItem
        
        for item in self.scene.items():
            # Skip temp items and handles
            if item == self._temp_item:
                continue
            if isinstance(item, SelectionHandleItem):
                continue
            
            if item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)
        
        self._update_selection()
    
    def zoom_in(self):
        """Zoom in."""
        self._zoom *= 1.25
        self.scale(1.25, 1.25)
        self.zoom_changed.emit(self._zoom)
    
    def zoom_out(self):
        """Zoom out."""
        self._zoom /= 1.25
        self.scale(1 / 1.25, 1 / 1.25)
        self.zoom_changed.emit(self._zoom)
    
    def zoom_to_fit(self):
        """Zoom to fit all content."""
        self.fitInView(
            0, 0,
            self.document.width,
            self.document.height,
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self._zoom = self.transform().m11()
        self.zoom_changed.emit(self._zoom)
    
    def zoom_to_100(self):
        """Reset zoom to 100%."""
        self.resetTransform()
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)
    
    def _snap_point(self, point: QPointF) -> QPointF:
        """Snap point to grid if enabled."""
        if not self._snap_to_grid:
            return point
        
        x = round(point.x() / self._grid_spacing) * self._grid_spacing
        y = round(point.y() / self._grid_spacing) * self._grid_spacing
        
        return QPointF(x, y)
    
    def _start_drawing(self, start: QPointF):
        """Start drawing a new shape (legacy method for tools not using new system)."""
        try:
            # Ensure we have an active layer
            if not self._active_layer:
                if self.document.layers:
                    self._active_layer = self.document.layers[0]
                else:
                    self._active_layer = Layer(name="Layer 1")
                    self.document.add_layer(self._active_layer)
            
            # Legacy tool handling (for tools not yet migrated)
            if self._current_tool_type == ToolType.RECTANGLE:
                self._temp_item = QGraphicsRectItem(
                    start.x(), start.y(), 0, 0
                )
            
            elif self._current_tool_type == ToolType.ELLIPSE:
                self._temp_item = QGraphicsEllipseItem(
                    start.x(), start.y(), 0, 0
                )
            
            if self._temp_item:
                pen = QPen(self._selection_color, 1)
                pen.setCosmetic(True)
                self._temp_item.setPen(pen)
                self._temp_item.setBrush(QBrush())  # No brush
                self.scene.addItem(self._temp_item)
        except Exception as e:
            print(f"Error in _start_drawing: {e}")
            import traceback
            traceback.print_exc()
            self._is_drawing = False
            self._temp_item = None
    
    def _update_drawing(self, current: QPointF):
        """Update temporary shape while drawing (legacy method)."""
        try:
            if not self._temp_item or not self._is_drawing:
                return
            
            # Legacy tool handling
            if self._current_tool_type == ToolType.RECTANGLE:
                if isinstance(self._temp_item, QGraphicsRectItem):
                    rect = QRectF(self._draw_start, current).normalized()
                    self._temp_item.setRect(rect)
            
            elif self._current_tool_type == ToolType.ELLIPSE:
                if isinstance(self._temp_item, QGraphicsEllipseItem):
                    rect = QRectF(self._draw_start, current).normalized()
                    self._temp_item.setRect(rect)
        except Exception as e:
            print(f"Error in _update_drawing: {e}")
            import traceback
            traceback.print_exc()
            # Don't crash, just log the error
    
    def _finish_drawing(self, end: QPointF):
        """Finish drawing and create the shape."""
        try:
            if not self._is_drawing:
                return
            
            # Ensure we have an active layer
            if not self._active_layer:
                if self.document.layers:
                    self._active_layer = self.document.layers[0]
                else:
                    # Create a default layer
                    self._active_layer = Layer(name="Layer 1")
                    self.document.add_layer(self._active_layer)
            
            # Create shape based on tool (legacy method)
            shape = None
            
            if self._current_tool_type == ToolType.RECTANGLE:
                rect = QRectF(self._draw_start, end).normalized()
                # Only create if size is meaningful
                if rect.width() > 0.1 and rect.height() > 0.1:
                    shape = Rectangle(
                        rect.x(), rect.y(),
                        rect.width(), rect.height()
                    )
            
            elif self._current_tool_type == ToolType.ELLIPSE:
                rect = QRectF(self._draw_start, end).normalized()
                # Only create if size is meaningful
                if rect.width() > 0.1 and rect.height() > 0.1:
                    shape = Ellipse(
                        rect.center().x(), rect.center().y(),
                        rect.width() / 2, rect.height() / 2
                    )
            
            if shape:
                self._active_layer.add_shape(shape)
                self._update_view()
            
            # Remove temporary item
            if self._temp_item:
                try:
                    self.scene.removeItem(self._temp_item)
                except Exception as e:
                    print(f"Error removing temp item: {e}")
                self._temp_item = None
            
            self._is_drawing = False
        except Exception as e:
            print(f"Error in _finish_drawing: {e}")
            import traceback
            traceback.print_exc()
            # Clean up on error
            if self._temp_item:
                try:
                    self.scene.removeItem(self._temp_item)
                except:
                    pass
                self._temp_item = None
            self._is_drawing = False
    
    def _finish_drawing_with_tool(self, end: QPointF):
        """Finish drawing using the current drawing tool."""
        try:
            if not self._is_drawing or not self._current_drawing_tool:
                return
            
            # Ensure we have an active layer
            if not self._active_layer:
                if self.document.layers:
                    self._active_layer = self.document.layers[0]
                else:
                    self._active_layer = Layer(name="Layer 1")
                    self.document.add_layer(self._active_layer)
            
            # For polygon tool, check if we have enough points
            if isinstance(self._current_drawing_tool, PolygonTool):
                if len(self._current_drawing_tool._points) < 2:
                    # Not enough points, just cancel
                    self._cancel_drawing()
                    return
            
            # Let the tool create the shape
            # For polygon, end point is ignored (uses _points)
            shape = self._current_drawing_tool.finish_drawing(end, self._active_layer)
            
            if shape:
                self._active_layer.add_shape(shape)
                self._update_view()
            
            # Clean up
            self._current_drawing_tool.cancel_drawing(self.scene)
            self._temp_item = None
            self._is_drawing = False
            
            # Reset polygon tool state
            if isinstance(self._current_drawing_tool, PolygonTool):
                self._current_drawing_tool._is_complete = False
        except Exception as e:
            print(f"Error in _finish_drawing_with_tool: {e}")
            import traceback
            traceback.print_exc()
            if self._current_drawing_tool:
                self._current_drawing_tool.cancel_drawing(self.scene)
            self._is_drawing = False
            self._temp_item = None
    
    def _on_selection_changed(self, shapes: List[Shape]):
        """Handle selection changes from SelectionManager."""
        self.selection_changed.emit(shapes)
    
    def _cancel_drawing(self):
        """Cancel current drawing operation."""
        if self._current_drawing_tool:
            self._current_drawing_tool.cancel_drawing(self.scene)
        elif self._temp_item:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None
        self._is_drawing = False
    
    def mirror_horizontal(self):
        """Mirror selected shapes horizontally."""
        self._selection_manager.mirror_horizontal()
        self._update_view()
    
    def mirror_vertical(self):
        """Mirror selected shapes vertically."""
        self._selection_manager.mirror_vertical()
        self._update_view()
    
    def rotate(self, angle: float):
        """Rotate selected shapes by angle (in radians)."""
        self._selection_manager.rotate(angle)
        self._update_view()
    
    def _on_text_editing_finished(self, text: str, position: QPointF):
        """Handle text editing finished - convert to Text shape."""
        from ..graphics.text_item import EditableTextItem
        from ..core.shapes import Text as TextShape
        
        # Find the text item that finished editing
        text_item = None
        if self._temp_item and isinstance(self._temp_item, EditableTextItem):
            text_item = self._temp_item
        else:
            # Check if any EditableTextItem in scene just finished editing
            for item in self.scene.items():
                if isinstance(item, EditableTextItem):
                    # Check if this item just finished (not editing anymore)
                    if not item.is_editing and item.toPlainText() == text:
                        text_item = item
                        break
        
        if not text_item:
            return
        
        # Only create/update shape if text is not empty
        if text and text.strip():
            # Ensure we have an active layer
            if not self._active_layer:
                if self.document.layers:
                    self._active_layer = self.document.layers[0]
                else:
                    self._active_layer = Layer(name="Layer 1")
                    self.document.add_layer(self._active_layer)
            
            # Get or create text shape
            text_shape = text_item.data(0)  # Get existing shape if any
            layer = text_item.data(1) or self._active_layer
            
            if text_shape and isinstance(text_shape, TextShape):
                # Update existing shape
                text_shape.text = text
                text_shape.position = Point(position.x(), position.y())
                font = text_item.font()
                text_shape.font_family = font.family()
                text_shape.font_size = font.pointSizeF()
                text_shape.bold = font.bold()
                text_shape.italic = font.italic()
                text_shape.visible = True  # Ensure it's visible
                text_shape.invalidate_cache()  # Force path recalculation
                
                # Ensure shape is in layer (might have been removed)
                if text_shape not in layer.shapes:
                    layer.add_shape(text_shape)
            else:
                # Create new Text shape
                font = text_item.font()
                text_shape = TextShape(
                    position.x(),
                    position.y(),
                    text,
                    font.family(),
                    font.pointSizeF(),
                    font.bold(),
                    font.italic()
                )
                text_shape.visible = True  # Ensure it's visible
                layer.add_shape(text_shape)
            
            # Store reference to shape in item
            text_item.set_text_shape(text_shape)
            text_item.setData(0, text_shape)  # Store shape reference
            text_item.setData(1, layer)  # Store layer reference
            
            # Update view to ensure everything is synced
            self._update_view()
        else:
            # Empty text - remove shape if it exists
            text_shape = text_item.data(0)
            layer = text_item.data(1)
            if text_shape and layer:
                layer.remove_shape(text_shape)
                self.scene.removeItem(text_item)
                self._update_view()
        
        # Clean up drawing state
        if text_item == self._temp_item:
            self._is_drawing = False
            # Don't remove temp_item - keep it for editing
    
    def _on_text_editing_cancelled(self):
        """Handle text editing cancelled - remove item."""
        if self._temp_item:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None
        self._is_drawing = False

