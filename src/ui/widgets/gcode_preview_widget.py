"""
G-Code Preview Widget - Visual preview of what will be engraved.

Shows a burn preview by parsing G-code and rendering where the laser will actually engrave.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QWheelEvent, QMouseEvent, QPixmap, QImage
import re
from typing import List, Tuple, Optional
from pathlib import Path


class GCodePreviewWidget(QWidget):
    """Widget that displays a visual preview of G-code engraving."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._engraving_points: List[Tuple[float, float]] = []
        self._bounds: Optional[Tuple[float, float, float, float]] = None  # min_x, max_x, min_y, max_y
        self._preview_pixmap: Optional[QPixmap] = None  # Cached preview image
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._pan_start = QPointF()
        self._is_panning = False
        self._zoom = 1.0
        self._max_points_to_render = 500000  # Limit for performance
        
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        
        # Background color (dark theme)
        self.setStyleSheet("background-color: #2b2b2b;")
    
    def load_gcode(self, filepath: str):
        """Load and parse G-code file."""
        self._engraving_points = []
        self._bounds = None
        self._preview_pixmap = None
        
        try:
            print(f"Loading G-code file: {filepath}")
            print("NOTE: S0 moves (laser off) will be filtered out - only S>0 moves will be shown")
            with open(filepath, 'r', encoding='utf-8') as f:
                # For very large files, read in chunks
                lines = f.readlines()
            
            total_lines = len(lines)
            print(f"Parsing {total_lines:,} lines...")
            
            # Parse G-code
            x = 0.0
            y = 0.0
            relative_mode = False
            laser_on = False  # Track laser state across lines
            current_power = 0
            
            # Try to parse bounds from header comment for validation
            expected_bounds = None
            for line in lines[:50]:  # Check first 50 lines for bounds comment
                if 'Bounds:' in line or 'bounds:' in line.lower():
                    # Parse: ; Bounds: X0.00 Y12.50 to X300.00 Y200.00
                    bounds_match = re.search(r'X([-\d.]+)\s+Y([-\d.]+)\s+to\s+X([-\d.]+)\s+Y([-\d.]+)', line)
                    if bounds_match:
                        expected_bounds = (
                            float(bounds_match.group(1)),  # min_x
                            float(bounds_match.group(3)),  # max_x
                            float(bounds_match.group(2)),  # min_y
                            float(bounds_match.group(4))   # max_y
                        )
                        print(f"Found bounds in header: X[{expected_bounds[0]:.2f}, {expected_bounds[1]:.2f}] Y[{expected_bounds[2]:.2f}, {expected_bounds[3]:.2f}]")
                        break
            
            min_x = float('inf')
            max_x = float('-inf')
            min_y = float('inf')
            max_y = float('-inf')
            
            point_count = 0
            sample_rate = 1  # Will adjust for very large files
            
            # Check file size to determine if we need sampling
            if total_lines > 100000:
                # For very large files, sample points to improve performance
                estimated_points = total_lines // 2  # Rough estimate
                if estimated_points > self._max_points_to_render:
                    sample_rate = max(1, estimated_points // self._max_points_to_render)
                    print(f"Large file detected. Using sample rate of 1:{sample_rate} for preview")
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Check for mode changes
                if 'G90' in line:
                    relative_mode = False
                elif 'G91' in line:
                    relative_mode = True
                
                # Check for laser on/off commands (M3 = on, M4 = dynamic mode, M5 = off)
                if 'M3' in line or 'M03' in line:
                    # M3 = constant power mode, laser is on
                    laser_on = True
                    # Extract S value if present
                    s_match = re.search(r'S(\d+)', line)
                    if s_match:
                        current_power = int(s_match.group(1))
                        laser_on = (current_power > 0)
                elif 'M4' in line or 'M04' in line:
                    # M4 = dynamic power mode, laser state depends on S value in each G1 move
                    # Extract S value if present
                    s_match = re.search(r'S(\d+)', line)
                    if s_match:
                        current_power = int(s_match.group(1))
                        laser_on = (current_power > 0)
                    else:
                        # M4 without S value - laser state will be determined by S values in G1 moves
                        # Don't assume laser is on - wait for first G1 move with S value
                        laser_on = False
                        current_power = 0
                elif 'M5' in line or 'M05' in line:
                    laser_on = False
                    current_power = 0
                
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
                    
                    # Update laser state if S value is present in this line
                    # This is critical for M4 mode where S value controls laser on/off per move
                    # For M4 mode, every G1 line should have an S value
                    if s_match:
                        current_power = int(s_match.group(1))
                        laser_on = (current_power > 0)  # S0 = laser off, S>0 = laser on
                    # Note: If no S value in G1 line, we keep previous state (shouldn't happen for M4 mode)
                    
                    # Record engraving point ONLY if laser is on (S > 0)
                    # G0 is rapid move (laser off), G1 is cutting move (may have laser on or off)
                    # CRITICAL: Only record G1 moves where current_power > 0 (laser is actually on)
                    # S0 moves must NEVER be recorded - they represent white/empty areas
                    if line.startswith('G1'):
                        # Explicitly check: only record if we have a positive power value
                        # This ensures S0 moves are never recorded
                        if current_power > 0 and laser_on:
                            point_count += 1
                            # Sample points for very large files
                            if point_count % sample_rate == 0:
                                self._engraving_points.append((x, y))
                                min_x = min(min_x, x)
                                max_x = max(max_x, x)
                                min_y = min(min_y, y)
                                max_y = max(max_y, y)
                        # All other cases (S0, no S value, laser off) are explicitly NOT recorded
                        # Debug: Track S0 moves to verify they're not being recorded
                        elif s_match and current_power == 0:
                            # This is an S0 move - explicitly skip it (do nothing)
                            pass
                
                # Progress update for large files
                if total_lines > 100000 and line_num % 100000 == 0:
                    print(f"  Parsed {line_num:,} / {total_lines:,} lines ({100*line_num//total_lines}%)")
            
            if self._engraving_points:
                # Recalculate bounds from actual points to ensure accuracy
                actual_min_x = min(p[0] for p in self._engraving_points)
                actual_max_x = max(p[0] for p in self._engraving_points)
                actual_min_y = min(p[1] for p in self._engraving_points)
                actual_max_y = max(p[1] for p in self._engraving_points)
                self._bounds = (actual_min_x, actual_max_x, actual_min_y, actual_max_y)
                print(f"Found {len(self._engraving_points):,} points (sampled from {point_count:,} total)")
                print(f"VERIFIED: Only S>0 moves were recorded - S0 moves were filtered out")
                print(f"Calculated bounds: X[{actual_min_x:.2f}, {actual_max_x:.2f}] Y[{actual_min_y:.2f}, {actual_max_y:.2f}]")
                
                # Compare with expected bounds if available
                if expected_bounds:
                    exp_min_x, exp_max_x, exp_min_y, exp_max_y = expected_bounds
                    x_diff = abs(actual_min_x - exp_min_x) + abs(actual_max_x - exp_max_x)
                    y_diff = abs(actual_min_y - exp_min_y) + abs(actual_max_y - exp_max_y)
                    if x_diff > 0.1 or y_diff > 0.1:
                        print(f"WARNING: Bounds mismatch! Expected X[{exp_min_x:.2f}, {exp_max_x:.2f}] Y[{exp_min_y:.2f}, {exp_max_y:.2f}]")
                        print(f"  Difference: X={x_diff:.2f}mm, Y={y_diff:.2f}mm")
                        # For significant differences, use expected bounds from header
                        # The header bounds represent the actual design area, while calculated bounds
                        # may include coordinate system artifacts (like Y=0 when design starts at Y=137)
                        if x_diff > 5.0 or y_diff > 5.0:
                            print(f"  Large difference detected - using expected bounds from G-code header")
                            print(f"  (This eliminates empty space from coordinate system artifacts)")
                            # Use expected bounds for display, but keep actual points for rendering
                            self._bounds = expected_bounds
                        # For small differences, trust calculated bounds
                
                # Generate preview pixmap
                self._generate_preview_pixmap()
                
                # Only fit to view if widget has valid size, otherwise defer
                if self.width() > 0 and self.height() > 0:
                    self._fit_to_view()
            else:
                print("No engraving points found in G-code")
            
            self.update()
            
        except Exception as e:
            print(f"Error loading G-code: {e}")
            import traceback
            traceback.print_exc()
    
    def _generate_preview_pixmap(self):
        """Generate a pixmap preview of the engraving points for fast rendering."""
        if not self._engraving_points or not self._bounds:
            return
        
        min_x, max_x, min_y, max_y = self._bounds
        width_mm = max_x - min_x
        height_mm = max_y - min_y
        
        if width_mm <= 0 or height_mm <= 0:
            return
        
        # Create a high-resolution preview image
        # Use a reasonable resolution that balances quality and memory
        max_preview_size = 2000  # Max dimension in pixels
        aspect_ratio = width_mm / height_mm
        
        if aspect_ratio > 1:
            preview_width = max_preview_size
            preview_height = int(max_preview_size / aspect_ratio)
        else:
            preview_height = max_preview_size
            preview_width = int(max_preview_size * aspect_ratio)
        
        # Scale factor from mm to pixels
        scale_x = preview_width / width_mm
        scale_y = preview_height / height_mm
        
        # Create image
        image = QImage(preview_width, preview_height, QImage.Format.Format_ARGB32)
        image.fill(QColor(43, 43, 43).rgb())  # Dark gray background
        
        # Draw lines and points
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Disable antialiasing for sharper lines
        
        # Detect if this is a dense fill pattern (many points in small area)
        # If so, use thinner lines and possibly skip some lines to show pattern structure
        total_points = len(self._engraving_points)
        area_mm2 = width_mm * height_mm if width_mm > 0 and height_mm > 0 else 1.0
        points_per_mm2 = total_points / area_mm2 if area_mm2 > 0 else 0
        
        # Use thinner lines for dense patterns to show structure
        base_line_width = min(scale_x, scale_y)
        if points_per_mm2 > 100:  # Very dense pattern (like image scanlines)
            line_width = 1  # Single pixel for dense patterns
            line_skip = max(1, int(points_per_mm2 / 50))  # Skip some lines to show pattern
        else:
            line_width = max(1, min(2, int(base_line_width * 0.3)))  # 1-2 pixels for normal patterns
            line_skip = 1  # Don't skip lines for sparse patterns
        
        painter.setPen(QPen(QColor(255, 50, 50, 255), line_width))  # Bright red for burn marks
        painter.setBrush(QBrush())  # No fill for lines
        
        # Draw lines between consecutive points
        # This will properly show fill patterns as filled areas
        lines_drawn = 0
        line_index = 0
        if len(self._engraving_points) > 1:
            prev_x, prev_y = self._engraving_points[0]
            prev_img_x = int((prev_x - min_x) * scale_x)
            prev_img_y = int((max_y - prev_y) * scale_y)  # Flip Y
            
            for x, y in self._engraving_points[1:]:
                line_index += 1
                
                # Convert to image coordinates
                img_x = int((x - min_x) * scale_x)
                img_y = int((max_y - y) * scale_y)  # Flip Y
                
                # Skip lines for very dense patterns to show structure
                if line_index % line_skip != 0:
                    # Still update previous position for next line
                    prev_img_x = img_x
                    prev_img_y = img_y
                    continue
                
                # Draw line if both points are in bounds (or at least one is)
                if (0 <= img_x < preview_width and 0 <= img_y < preview_height) or \
                   (0 <= prev_img_x < preview_width and 0 <= prev_img_y < preview_height):
                    # Clip line to bounds if needed
                    painter.drawLine(prev_img_x, prev_img_y, img_x, img_y)
                    lines_drawn += 1
                
                prev_img_x = img_x
                prev_img_y = img_y
        
        # For very dense patterns, also draw a sample of points to show the pattern
        if points_per_mm2 > 100:
            point_size = 1  # Single pixel for dense patterns
            point_skip = max(1, int(total_points / 10000))  # Sample points for preview
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 50, 50, 180))  # Slightly transparent red
            
            points_drawn = 0
            for i, (x, y) in enumerate(self._engraving_points):
                if i % point_skip != 0:
                    continue
                # Convert to image coordinates
                img_x = int((x - min_x) * scale_x)
                img_y = int((max_y - y) * scale_y)  # Flip Y
                
                # Draw point if in bounds
                if 0 <= img_x < preview_width and 0 <= img_y < preview_height:
                    painter.drawEllipse(img_x - point_size // 2, img_y - point_size // 2, 
                                     point_size, point_size)
                    points_drawn += 1
        else:
            # For sparse patterns, draw all points
            point_size = max(1, min(2, int(min(scale_x, scale_y) * 0.2)))  # Smaller points
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 50, 50, 200))  # Slightly transparent red
            
            points_drawn = 0
            for x, y in self._engraving_points:
                # Convert to image coordinates
                img_x = int((x - min_x) * scale_x)
                img_y = int((max_y - y) * scale_y)  # Flip Y
                
                # Draw point if in bounds
                if 0 <= img_x < preview_width and 0 <= img_y < preview_height:
                    painter.drawEllipse(img_x - point_size // 2, img_y - point_size // 2, 
                                     point_size, point_size)
                    points_drawn += 1
        
        painter.end()
        
        # Convert to pixmap
        self._preview_pixmap = QPixmap.fromImage(image)
        print(f"Generated preview pixmap: {preview_width}x{preview_height}, drew {lines_drawn:,} lines and {points_drawn:,} points (line_width={line_width})")
    
    def _fit_to_view(self):
        """Calculate scale and offset to fit engraving in view."""
        if not self._bounds:
            return
        
        min_x, max_x, min_y, max_y = self._bounds
        
        if max_x == min_x or max_y == min_y:
            return
        
        # Ensure widget has valid size
        widget_width = max(1, self.width())
        widget_height = max(1, self.height())
        
        width = max_x - min_x
        height = max_y - min_y
        
        # Calculate scale to fit with margin
        margin = 20
        view_width = widget_width - 2 * margin
        view_height = widget_height - 2 * margin
        
        if view_width <= 0 or view_height <= 0:
            return
        
        scale_x = view_width / width if width > 0 else 1.0
        scale_y = view_height / height if height > 0 else 1.0
        self._scale = min(scale_x, scale_y)
        
        # Center the engraving
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Calculate offsets to center the content
        # X: simple centering
        self._offset_x = widget_width / 2 - center_x * self._scale
        # Y: flip because screen Y increases downward, but laser Y increases upward
        # When we negate Y, we need to adjust the offset: offset = height/2 - (-center_y) * scale
        # This simplifies to: offset = height/2 + center_y * scale
        self._offset_y = widget_height / 2 + center_y * self._scale
    
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
        
        # Draw preview pixmap if available (much faster for all files)
        if self._preview_pixmap and not self._preview_pixmap.isNull():
            min_x, max_x, min_y, max_y = self._bounds
            width_mm = max_x - min_x
            height_mm = max_y - min_y
            
            if width_mm > 0 and height_mm > 0:
                # Calculate screen position - pixmap was generated with Y already flipped
                screen_x = min_x * self._scale + self._offset_x
                # For Y: pixmap has Y flipped (max_y at top), so we need to account for that
                # The pixmap's coordinate system: top is max_y, bottom is min_y (flipped)
                # Screen coordinate: we flip Y again, so -max_y is at top
                screen_y = -max_y * self._scale + self._offset_y  # Flip Y for screen
                screen_w = width_mm * self._scale
                screen_h = height_mm * self._scale
                
                # Draw the pixmap
                source_rect = QRectF(0, 0, self._preview_pixmap.width(), self._preview_pixmap.height())
                target_rect = QRectF(screen_x, screen_y, screen_w, screen_h)
                painter.drawPixmap(target_rect, self._preview_pixmap, source_rect)
        else:
            # Fallback: draw lines and points individually (slower, for small files)
            # Draw lines between consecutive points to show fill patterns properly
            painter.setPen(QPen(QColor(255, 100, 100), max(1.0, self._scale * 0.2)))  # Red for burn marks
            painter.setBrush(QBrush())  # No fill for lines
            
            if len(self._engraving_points) > 1:
                prev_x, prev_y = self._engraving_points[0]
                prev_screen_x = prev_x * self._scale + self._offset_x
                prev_screen_y = -prev_y * self._scale + self._offset_y
                
                for x, y in self._engraving_points[1:]:
                    screen_x = x * self._scale + self._offset_x
                    screen_y = -y * self._scale + self._offset_y
                    
                    # Draw line if at least one point is in viewport
                    if (0 <= screen_x <= self.width() and 0 <= screen_y <= self.height()) or \
                       (0 <= prev_screen_x <= self.width() and 0 <= prev_screen_y <= self.height()):
                        painter.drawLine(QPointF(prev_screen_x, prev_screen_y), 
                                       QPointF(screen_x, screen_y))
                    
                    prev_screen_x = screen_x
                    prev_screen_y = screen_y
            
            # Also draw points for very sparse patterns
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 100, 100, 180)))  # Semi-transparent red
            point_size = max(0.5, self._scale * 0.05)  # Smaller points
            
            for x, y in self._engraving_points:
                screen_x = x * self._scale + self._offset_x
                screen_y = -y * self._scale + self._offset_y
                
                # Only draw if in viewport
                if 0 <= screen_x <= self.width() and 0 <= screen_y <= self.height():
                    painter.drawEllipse(QPointF(screen_x, screen_y), point_size, point_size)
        
        # Draw bounds rectangle (flip Y)
        # Bounds are already calculated from points, so use them directly
        min_x, max_x, min_y, max_y = self._bounds
        rect_x = min_x * self._scale + self._offset_x
        # Flip Y: in laser coords, min_y is bottom, max_y is top
        # After negating Y: -max_y is at top of screen, -min_y is at bottom
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
        super().resizeEvent(event)
        if self._bounds and self.width() > 0 and self.height() > 0:
            self._fit_to_view()
            self.update()


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
