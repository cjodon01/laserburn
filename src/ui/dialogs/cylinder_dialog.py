"""
Cylinder Engraving Dialog

UI for configuring cylinder engraving parameters.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDoubleSpinBox, QLabel, QPushButton, QGroupBox,
    QCheckBox, QDialogButtonBox, QWidget, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
from typing import Optional
import math

from ...image.cylinder_warp import CylinderParams, CylinderWarper


class CylinderPreviewWidget(QWidget):
    """Widget showing cylinder cross-section preview."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.diameter = 50.0
        self.max_angle = 45.0
        self.setMinimumSize(200, 150)
    
    def set_params(self, diameter: float, max_angle: float):
        """Update preview with new parameters."""
        self.diameter = diameter
        self.max_angle = max_angle
        self.update()
    
    def paintEvent(self, event):
        """Paint the cylinder preview."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h - 20  # Center at bottom
        
        # Scale to fit
        scale = min(w, h - 40) / (self.diameter * 1.2)
        r = self.diameter / 2 * scale
        
        # Draw cylinder cross-section
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))
        
        # Draw usable arc
        theta = math.radians(self.max_angle)
        
        painter.setPen(QPen(QColor(0, 150, 0), 3))
        # Draw arc from -theta to +theta
        start_angle = int((90 - self.max_angle) * 16)
        span_angle = int(self.max_angle * 2 * 16)
        painter.drawArc(int(cx - r), int(cy - r), int(2 * r), int(2 * r),
                       start_angle, span_angle)
        
        # Draw laser beam indicator
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawLine(cx, 10, cx, int(cy - r))
        
        # Labels
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(10, 20, f"Ø{self.diameter:.1f}mm")
        painter.drawText(10, 35, f"±{self.max_angle:.0f}°")


class WarpedDesignPreviewWidget(QWidget):
    """Widget showing how the design will be warped for cylinder engraving.
    
    This shows a side-by-side comparison of original vs warped shapes,
    demonstrating how the cylinder curvature affects the design.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.params: Optional[CylinderParams] = None
        self.warper: Optional[CylinderWarper] = None
        self.setMinimumSize(300, 200)
    
    def set_params(self, params: CylinderParams):
        """Update preview with new parameters."""
        self.params = params
        try:
            self.warper = CylinderWarper(params)
        except ValueError:
            self.warper = None
        self.update()
    
    def paintEvent(self, event):
        """Paint the warped design preview showing before/after comparison."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # Dark background
        painter.fillRect(0, 0, w, h, QColor(40, 40, 40))
        
        if not self.params or not self.warper:
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(w // 2 - 60, h // 2, "Configure parameters above")
            return
        
        # Layout: left side = original, right side = warped
        margin = 15
        section_w = (w - 3 * margin) // 2
        section_h = h - 2 * margin - 40  # Leave room for labels
        
        # Calculate usable width in mm
        usable_width = self.params.get_usable_flat_width()
        if usable_width <= 0:
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(w // 2 - 40, h // 2, "Invalid parameters")
            return
        
        # Scale to fit
        scale = min(section_w, section_h) / usable_width * 0.8
        
        # Section positions
        left_cx = margin + section_w // 2
        right_cx = margin * 2 + section_w + section_w // 2
        cy = margin + 30 + section_h // 2
        
        # Draw section labels
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(left_cx - 50, margin + 15, "Original Design")
        painter.drawText(right_cx - 70, margin + 15, "Warped for Cylinder")
        
        # Draw section backgrounds
        painter.fillRect(margin, margin + 25, section_w, section_h, QColor(50, 50, 50))
        painter.fillRect(margin * 2 + section_w, margin + 25, section_w, section_h, QColor(50, 50, 50))
        
        # Draw example shapes in ORIGINAL section (left)
        self._draw_original_shapes(painter, left_cx, cy, scale, usable_width)
        
        # Draw example shapes in WARPED section (right)
        self._draw_warped_shapes(painter, right_cx, cy, scale, usable_width)
        
        # Draw info at bottom
        painter.setPen(QColor(150, 150, 150))
        info_y = h - 15
        painter.drawText(10, info_y, 
            f"Ø{self.params.diameter:.0f}mm  |  ±{self.params.max_angle:.0f}°  |  "
            f"Width: {usable_width:.1f}mm  |  Edge power: {self.params.get_power_at_edge():.2f}×")
    
    def _draw_original_shapes(self, painter: QPainter, cx: float, cy: float, 
                               scale: float, usable_width: float):
        """Draw original (uniform) example shapes."""
        # Draw grid
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        grid_size = usable_width / 6
        for i in range(-3, 4):
            x = cx + i * grid_size * scale
            painter.drawLine(int(x), int(cy - usable_width * scale / 2), 
                           int(x), int(cy + usable_width * scale / 2))
        for i in range(-3, 4):
            y = cy + i * grid_size * scale
            painter.drawLine(int(cx - usable_width * scale / 2), int(y),
                           int(cx + usable_width * scale / 2), int(y))
        
        # Draw center line
        painter.setPen(QPen(QColor(255, 100, 100), 1))
        painter.drawLine(int(cx), int(cy - usable_width * scale / 2),
                        int(cx), int(cy + usable_width * scale / 2))
        
        # Draw example rectangle
        rect_w = usable_width * 0.5 * scale
        rect_h = usable_width * 0.3 * scale
        painter.setPen(QPen(QColor(100, 200, 255), 2))
        painter.drawRect(int(cx - rect_w / 2), int(cy - rect_h / 2), int(rect_w), int(rect_h))
        
        # Draw example circle
        circle_r = usable_width * 0.15 * scale
        painter.setPen(QPen(QColor(100, 255, 100), 2))
        painter.drawEllipse(int(cx - circle_r), int(cy - circle_r), 
                           int(circle_r * 2), int(circle_r * 2))
        
        # Draw text example (as lines)
        painter.setPen(QPen(QColor(255, 200, 100), 2))
        text_w = usable_width * 0.4 * scale
        text_y = cy + usable_width * 0.25 * scale
        # Simple "ABC" approximation with lines
        painter.drawLine(int(cx - text_w/2), int(text_y + 10), 
                        int(cx - text_w/2 + 10), int(text_y - 10))
        painter.drawLine(int(cx - text_w/2 + 10), int(text_y - 10),
                        int(cx - text_w/2 + 20), int(text_y + 10))
    
    def _draw_warped_shapes(self, painter: QPainter, cx: float, cy: float,
                            scale: float, usable_width: float):
        """Draw warped example shapes showing cylinder distortion."""
        if not self.warper:
            return
        
        half_width = usable_width / 2
        
        # Helper to warp X coordinate
        def warp_x(design_x_mm):
            output_x = self.warper.arc_to_flat(design_x_mm)
            return cx + output_x * scale
        
        # Draw warped grid
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        grid_size = usable_width / 6
        for i in range(-3, 4):
            design_x = i * grid_size
            screen_x = warp_x(design_x)
            painter.drawLine(int(screen_x), int(cy - usable_width * scale / 2),
                           int(screen_x), int(cy + usable_width * scale / 2))
        for i in range(-3, 4):
            y = cy + i * grid_size * scale
            painter.drawLine(int(warp_x(-half_width)), int(y),
                           int(warp_x(half_width)), int(y))
        
        # Draw center line (stays at center)
        painter.setPen(QPen(QColor(255, 100, 100), 1))
        painter.drawLine(int(cx), int(cy - usable_width * scale / 2),
                        int(cx), int(cy + usable_width * scale / 2))
        
        # Draw warped rectangle (compressed toward center)
        rect_w_mm = usable_width * 0.5
        rect_h = usable_width * 0.3 * scale
        painter.setPen(QPen(QColor(100, 200, 255), 2))
        
        left_x = warp_x(-rect_w_mm / 2)
        right_x = warp_x(rect_w_mm / 2)
        painter.drawRect(int(left_x), int(cy - rect_h / 2), 
                        int(right_x - left_x), int(rect_h))
        
        # Draw warped circle (becomes ellipse, compressed horizontally)
        circle_r_mm = usable_width * 0.15
        painter.setPen(QPen(QColor(100, 255, 100), 2))
        
        # Sample points around circle and warp them
        num_points = 32
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            design_x = circle_r_mm * math.cos(angle)
            design_y = circle_r_mm * math.sin(angle)
            screen_x = warp_x(design_x)
            screen_y = cy + design_y * scale
            points.append((int(screen_x), int(screen_y)))
        
        # Draw warped circle as connected lines
        for i in range(num_points):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % num_points]
            painter.drawLine(x1, y1, x2, y2)
        
        # Draw warped text example
        painter.setPen(QPen(QColor(255, 200, 100), 2))
        text_y = cy + usable_width * 0.25 * scale
        # Simple "ABC" approximation with warped lines
        x1 = warp_x(-usable_width * 0.2)
        x2 = warp_x(-usable_width * 0.15)
        x3 = warp_x(-usable_width * 0.1)
        painter.drawLine(int(x1), int(text_y + 10), int(x2), int(text_y - 10))
        painter.drawLine(int(x2), int(text_y - 10), int(x3), int(text_y + 10))


class CylinderDialog(QDialog):
    """Dialog for cylinder engraving settings."""
    
    def __init__(self, parent=None, initial_params: Optional[CylinderParams] = None):
        super().__init__(parent)
        self.setWindowTitle("Cylinder Engraving Settings")
        self.setMinimumWidth(450)
        self._init_ui()
        
        if initial_params:
            self._load_params(initial_params)
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        
        # Preview tabs
        preview_tabs = QTabWidget()
        
        # Cylinder cross-section preview
        self.preview = CylinderPreviewWidget()
        preview_tabs.addTab(self.preview, "Cylinder View")
        
        # Warped design preview
        self.warped_preview = WarpedDesignPreviewWidget()
        preview_tabs.addTab(self.warped_preview, "Warped Design")
        
        layout.addWidget(preview_tabs)
        
        # Cylinder parameters
        params_group = QGroupBox("Cylinder Parameters")
        params_layout = QFormLayout()
        
        self.diameter_spin = QDoubleSpinBox()
        self.diameter_spin.setRange(1, 1000)
        self.diameter_spin.setValue(50)
        self.diameter_spin.setSuffix(" mm")
        self.diameter_spin.setDecimals(1)
        self.diameter_spin.valueChanged.connect(self._update_preview)
        params_layout.addRow("Diameter:", self.diameter_spin)
        
        self.max_angle_spin = QDoubleSpinBox()
        self.max_angle_spin.setRange(10, 80)
        self.max_angle_spin.setValue(45)
        self.max_angle_spin.setSuffix("°")
        self.max_angle_spin.setDecimals(0)
        self.max_angle_spin.valueChanged.connect(self._update_preview)
        params_layout.addRow("Max Angle:", self.max_angle_spin)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Calculated values
        calc_group = QGroupBox("Calculated Values")
        calc_layout = QFormLayout()
        
        self.usable_width_label = QLabel("0.0 mm")
        calc_layout.addRow("Usable Width:", self.usable_width_label)
        
        self.power_at_edge_label = QLabel("1.00× (100%)")
        calc_layout.addRow("Power at Edge:", self.power_at_edge_label)
        
        self.z_drop_label = QLabel("0.00 mm")
        calc_layout.addRow("Z Drop at Edge:", self.z_drop_label)
        
        calc_group.setLayout(calc_layout)
        layout.addWidget(calc_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.warp_image_check = QCheckBox("Warp image for cylinder curvature")
        self.warp_image_check.setChecked(True)
        self.warp_image_check.setToolTip(
            "Pre-distort the image so it appears correct on the curved surface"
        )
        options_layout.addWidget(self.warp_image_check)
        
        self.power_comp_check = QCheckBox("Apply power compensation")
        self.power_comp_check.setChecked(True)
        self.power_comp_check.setToolTip(
            "Automatically adjust laser power based on surface angle"
        )
        options_layout.addWidget(self.power_comp_check)
        
        self.z_comp_check = QCheckBox("Apply Z compensation (if available)")
        self.z_comp_check.setChecked(False)
        self.z_comp_check.setToolTip(
            "Adjust Z-axis to maintain focus (requires Z-axis control)"
        )
        options_layout.addWidget(self.z_comp_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self._update_preview()
        self._update_calculations()
    
    def _load_params(self, params: CylinderParams):
        """Load parameters into the dialog."""
        self.diameter_spin.setValue(params.diameter)
        self.max_angle_spin.setValue(params.max_angle)
        self._update_preview()
    
    def _update_preview(self):
        """Update the preview widgets."""
        params = self.get_params()
        self.preview.set_params(
            self.diameter_spin.value(),
            self.max_angle_spin.value()
        )
        self.warped_preview.set_params(params)
        self._update_calculations()
    
    def _update_calculations(self):
        """Update calculated value labels."""
        r = self.diameter_spin.value() / 2
        theta = math.radians(self.max_angle_spin.value())
        
        # Usable width
        usable_width = 2 * r * math.sin(theta)
        self.usable_width_label.setText(f"{usable_width:.1f} mm")
        
        # Power at edge
        power_mult = 1 / math.cos(theta)
        self.power_at_edge_label.setText(
            f"{power_mult:.2f}× ({power_mult * 100:.0f}%)"
        )
        
        # Z drop
        z_drop = r * (1 - math.cos(theta))
        self.z_drop_label.setText(f"{z_drop:.2f} mm")
    
    def get_params(self) -> CylinderParams:
        """Get the cylinder parameters from the dialog."""
        return CylinderParams(
            diameter=self.diameter_spin.value(),
            max_angle=self.max_angle_spin.value()
        )
    
    def should_warp_image(self) -> bool:
        """Check if image warping is enabled."""
        return self.warp_image_check.isChecked()
    
    def should_compensate_power(self) -> bool:
        """Check if power compensation is enabled."""
        return self.power_comp_check.isChecked()
    
    def should_compensate_z(self) -> bool:
        """Check if Z compensation is enabled."""
        return self.z_comp_check.isChecked()


