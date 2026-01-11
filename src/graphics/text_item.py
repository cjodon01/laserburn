"""
Editable Text Item for PowerPoint-style text editing.

This provides inline text editing directly on the canvas, similar to PowerPoint.
"""

from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsItem, QStyleOptionGraphicsItem, QStyle
from PyQt6.QtCore import QRectF, QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QTextCursor, QKeyEvent, QFocusEvent
from typing import Optional

from ..core.shapes import Text, Point


class EditableTextItem(QGraphicsTextItem):
    """
    An editable text item that can be edited inline on the canvas.
    
    Similar to PowerPoint - click to create, type to edit, click outside to finish.
    """
    
    # Signal emitted when editing is finished
    editing_finished = pyqtSignal(str, QPointF)  # text, position
    editing_cancelled = pyqtSignal()
    
    def __init__(self, text: str = "", position: QPointF = QPointF(0, 0),
                 font_family: str = "Arial", font_size: float = 24.0,
                 bold: bool = False, italic: bool = False,
                 parent: Optional[QGraphicsItem] = None):
        """
        Create an editable text item.
        
        Args:
            text: Initial text content
            position: Position on canvas
            font_family: Font family
            font_size: Font size in points
            bold: Whether text is bold
            italic: Whether text is italic
            parent: Parent graphics item
        """
        super().__init__(text, parent)
        
        self._is_editing = False
        self._original_text = text
        self._text_shape: Optional[Text] = None  # Reference to Text shape if created
        
        # Set font
        font = QFont(font_family, int(font_size))
        font.setBold(bold)
        font.setItalic(italic)
        self.setFont(font)
        
        # Set position
        self.setPos(position)
        
        # Set default text color
        self.setDefaultTextColor(QColor(0, 0, 0))
        
        # Make it selectable and movable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Accept focus for editing
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        
        # Accept hover events
        self.setAcceptHoverEvents(True)
        
        # Set text interaction flags for editing
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        
        # Start editing immediately if text is empty
        if not text or text.strip() == "":
            self.start_editing()
    
    def start_editing(self):
        """Start editing the text."""
        self._is_editing = True
        self._original_text = self.toPlainText()
        self.setFocus()
        
        # Select all text for easy replacement
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)
        
        self.update()
    
    def finish_editing(self, accept: bool = True):
        """Finish editing the text."""
        if not self._is_editing:
            return
        
        self._is_editing = False
        
        if accept:
            text = self.toPlainText()
            # Update shape if it exists
            if self._text_shape:
                self._text_shape.text = text
                self._text_shape.position = Point(self.pos().x(), self.pos().y())
                font = self.font()
                self._text_shape.font_family = font.family()
                self._text_shape.font_size = font.pointSizeF()
                self._text_shape.bold = font.bold()
                self._text_shape.italic = font.italic()
                self._text_shape.invalidate_cache()
            # Emit signal with final text and position
            self.editing_finished.emit(text, self.pos())
        else:
            # Restore original text
            self.setPlainText(self._original_text)
            self.editing_cancelled.emit()
        
        # Clear focus
        self.clearFocus()
        self.update()
    
    def cancel_editing(self):
        """Cancel editing and restore original text."""
        self.finish_editing(accept=False)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to start editing."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_editing()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
    
    def focusOutEvent(self, event: QFocusEvent):
        """Handle focus loss - finish editing."""
        # Finish editing when focus is lost
        if self._is_editing:
            self.finish_editing(accept=True)
        super().focusOutEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key presses during editing."""
        if event.key() == Qt.Key.Key_Escape:
            # Cancel editing on Escape
            self.cancel_editing()
            event.accept()
        elif event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Enter to finish editing
            self.finish_editing(accept=True)
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        """Paint the text item with editing border."""
        # Draw border when editing
        if self._is_editing or self.hasFocus():
            # Draw border around text
            rect = self.boundingRect()
            pen = QPen(QColor(0, 120, 215), 2)  # Blue border
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 50)))  # Semi-transparent white
            painter.drawRect(rect.adjusted(-2, -2, 2, 2))
        
        # Draw selection highlight
        if option.state & QStyle.StateFlag.State_Selected:
            rect = self.boundingRect()
            pen = QPen(QColor(0, 120, 215), 1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush())
            painter.drawRect(rect.adjusted(-1, -1, 1, 1))
        
        # Draw the text
        super().paint(painter, option, widget)
    
    def to_text_shape(self) -> Text:
        """Convert this editable item to a Text shape."""
        if self._text_shape:
            # Update existing shape
            self._text_shape.text = self.toPlainText()
            self._text_shape.position = Point(self.pos().x(), self.pos().y())
            return self._text_shape
        
        # Create new Text shape
        font = self.font()
        text_shape = Text(
            self.pos().x(),
            self.pos().y(),
            self.toPlainText(),
            font.family(),
            font.pointSizeF(),
            font.bold(),
            font.italic()
        )
        self._text_shape = text_shape
        return text_shape
    
    def set_text_shape(self, shape: Text):
        """Set the Text shape this item represents."""
        self._text_shape = shape
        # Update item from shape
        self.setPlainText(shape.text)
        self.setPos(QPointF(shape.position.x, shape.position.y))
        
        font = QFont(shape.font_family, int(shape.font_size))
        font.setBold(shape.bold)
        font.setItalic(shape.italic)
        self.setFont(font)
    
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        """Handle item changes (position, selection, etc.)."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update shape position when item is moved
            if self._text_shape:
                new_pos = self.pos()
                self._text_shape.position = Point(new_pos.x(), new_pos.y())
                # Invalidate cache so paths are recalculated
                self._text_shape.invalidate_cache()
        
        return super().itemChange(change, value)
    
    @property
    def is_editing(self) -> bool:
        """Check if currently editing."""
        return self._is_editing

