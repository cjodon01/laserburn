"""
G-Code Preview Widget - Visual preview of what will be engraved.

Shows a burn preview by parsing G-code and rendering where the laser will actually engrave.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QWheelEvent, QMouseEvent
import re
from typing import List, Tuple, Optional
from pathlib import Path


class GCodePreviewWidget(QWidget):
    """Widget that displays a visual preview of G-code engraving."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._engraving_points: List[Tuple[float, float]] = []
        self._bounds: Optional[Tuple[float, float, float, float]] = None  # min_x, max_x, min_y, max_y
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._pan_start = QPointF()
        self._is_panning = False
        self._zoom = 1.0
        
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        
        # Background color (dark theme)
        self.setStyleSheet("background-color: #2b2b2b;")
    
    def load_gcode(self, filepath: str):
        """Load and parse G-code file."""
        self._engraving_points = []
        self._bounds = None
        
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Parse G-code
            x = 0.0
            y = 0.0
            relative_mode = False
            
            min_x = float('inf')
            max_x = float('-inf')
            min_y = float('inf')
            max_y = float('-inf')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Check for mode changes
                if 'G90' in line:
                    relative_mode = False
                elif 'G91' in line:
                    relative_mode = True
                
                # Parse G0/G1 moves
                if line.startswith('G0') or line.startswith('G1'):
                    # Extract X, Y, S values
                    x_match = re.search(r'X([-\d.]+)', line)
                    y_match = re.search(r'Y([-\d.]+)', line)
                    s_match = re.search(r'S(\d+)', line)
                    
                    # Update position
                    if x_match:
                        x_val = float(x_match.group(1))
                        if relative_mode:
                            x += x_val
                        else:
                            x = x_val
                    
                    if y_match:
                        y_val = float(y_match.group(1))
                        if relative_mode:
                            y += y_val
                        else:
                            y = y_val
                    
                    # Check if laser is on (S > 0)
                    laser_on = False
                    if s_match:
                        s_val = int(s_match.group(1))
                        laser_on = (s_val > 0)
                    
                    # Record engraving point if laser is on
                    if laser_on:
                        self._engraving_points.append((x, y))
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)
            
            if self._engraving_points:
                self._bounds = (min_x, max_x, min_y, max_y)
                self._fit_to_view()
            
            self.update()
            
        except Exception as e:
            print(f"Error loading G-code: {e}")
            import traceback
            traceback.print_exc()
    
    def _fit_to_view(self):
        """Calculate scale and offset to fit engraving in view."""
        if not self._bounds:
            return
        
        min_x, max_x, min_y, max_y = self._bounds
        
        if max_x == min_x or max_y == min_y:
            return
        
        width = max_x - min_x
        height = max_y - min_y
        
        # Calculate scale to fit with margin
        margin = 20
        view_width = self.width() - 2 * margin
        view_height = self.height() - 2 * margin
        
        scale_x = view_width / width if width > 0 else 1.0
        scale_y = view_height / height if height > 0 else 1.0
        self._scale = min(scale_x, scale_y)
        
        # Center the engraving
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        self._offset_x = self.width() / 2 - center_x * self._scale
        # For Y: flip because screen Y increases downward, but laser Y increases upward
        # When we negate Y, we need to adjust the offset: offset = height/2 - (-center_y) * scale
        self._offset_y = self.height() / 2 - (-center_y) * self._scale
    
    def paintEvent(self, event):
        """Paint the engraving preview."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(43, 43, 43))  # Dark gray
        
        if not self._engraving_points or not self._bounds:
            # Show placeholder
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                           "No G-code loaded\n\nLoad a G-code file to see burn preview")
            return
        
        # Draw grid (optional, for reference)
        self._draw_grid(painter)
        
        # Draw engraving points
        # Use a small dot for each point, or connect them for paths
        painter.setPen(QPen(QColor(255, 100, 100), 1))  # Red for burn marks
        painter.setBrush(QBrush(QColor(255, 100, 100, 180)))  # Semi-transparent red
        
        # Draw points - use small circles
        point_size = max(1.0, self._scale * 0.1)  # Scale point size with zoom
        
        for x, y in self._engraving_points:
            screen_x = x * self._scale + self._offset_x
            # Flip Y: negate Y coordinate (screen Y increases downward, laser Y increases upward)
            screen_y = -y * self._scale + self._offset_y
            
            # Only draw if in viewport
            if 0 <= screen_x <= self.width() and 0 <= screen_y <= self.height():
                painter.drawEllipse(QPointF(screen_x, screen_y), point_size, point_size)
        
        # Draw bounds rectangle (flip Y)
        min_x, max_x, min_y, max_y = self._bounds
        rect_x = min_x * self._scale + self._offset_x
        # Flip Y: in laser coords, min_y is bottom, max_y is top
        # After negating: -max_y is at bottom of screen, -min_y is at top
        # Qt draws from top, so use -max_y as the top Y position
        rect_y = -max_y * self._scale + self._offset_y
        rect_w = (max_x - min_x) * self._scale
        rect_h = (max_y - min_y) * self._scale  # Height is still positive
        
        painter.setPen(QPen(QColor(100, 150, 255), 1, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush())
        painter.drawRect(QRectF(rect_x, rect_y, rect_w, rect_h))
        
        # Draw info text
        painter.setPen(QColor(200, 200, 200))
        info = f"Points: {len(self._engraving_points)} | "
        if self._bounds:
            width = max_x - min_x
            height = max_y - min_y
            info += f"Size: {width:.1f}mm × {height:.1f}mm"
        painter.drawText(10, 20, info)
    
    def _draw_grid(self, painter: QPainter):
        """Draw a subtle grid for reference."""
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        
        # Draw grid lines every 10mm (scaled)
        grid_spacing = 10.0 * self._scale
        
        if grid_spacing < 5:  # Don't draw if too dense
            return
        
        # Vertical lines
        start_x = (self._offset_x % grid_spacing) - grid_spacing
        x = start_x
        while x < self.width():
            painter.drawLine(int(x), 0, int(x), self.height())
            x += grid_spacing
        
        # Horizontal lines
        start_y = (self._offset_y % grid_spacing) - grid_spacing
        y = start_y
        while y < self.height():
            painter.drawLine(0, int(y), self.width(), int(y))
            y += grid_spacing
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        
        # Zoom around mouse position
        mouse_pos = event.position()
        old_scale = self._scale
        
        self._scale *= zoom_factor
        self._scale = max(0.1, min(10.0, self._scale))  # Limit zoom
        
        # Adjust offset to zoom around mouse
        scale_change = self._scale / old_scale
        self._offset_x = mouse_pos.x() - (mouse_pos.x() - self._offset_x) * scale_change
        self._offset_y = mouse_pos.y() - (mouse_pos.y() - self._offset_y) * scale_change
        
        self.update()
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning."""
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._offset_x += delta.x()
            self._offset_y += delta.y()
            self._pan_start = event.position()
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def resizeEvent(self, event):
        """Handle resize - refit to view."""
        if self._bounds:
            self._fit_to_view()
        super().resizeEvent(event)


class GCodePreviewDialog(QWidget):
    """Dialog/widget with G-code preview and controls."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("G-Code Burn Preview")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Controls
        controls = QWidget()
        controls_layout = QVBoxLayout()
        
        btn_layout = QVBoxLayout()
        load_btn = QPushButton("Load G-Code File...")
        load_btn.clicked.connect(self._load_gcode)
        btn_layout.addWidget(load_btn)
        
        fit_btn = QPushButton("Fit to View")
        fit_btn.clicked.connect(self._fit_to_view)
        btn_layout.addWidget(fit_btn)
        
        btn_layout.addStretch()
        controls_layout.addLayout(btn_layout)
        controls.setLayout(controls_layout)
        
        layout.addWidget(controls)
        
        # Preview widget
        self.preview = GCodePreviewWidget()
        layout.addWidget(self.preview)
        
        self.setLayout(layout)
    
    def _load_gcode(self):
        """Load G-code file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load G-Code File",
            "",
            "G-Code Files (*.gcode *.nc *.ngc);;All Files (*)"
        )
        if filepath:
            self.preview.load_gcode(filepath)
    
    def _fit_to_view(self):
        """Fit preview to view."""
        self.preview._fit_to_view()
        self.preview.update()
    
    def load_gcode_file(self, filepath: str):
        """Load G-code file programmatically."""
        self.preview.load_gcode(filepath)
