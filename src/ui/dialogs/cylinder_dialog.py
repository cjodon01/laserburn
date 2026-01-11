"""
Cylinder Engraving Dialog

UI for configuring cylinder engraving parameters.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDoubleSpinBox, QLabel, QPushButton, QGroupBox,
    QCheckBox, QDialogButtonBox, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor
from typing import Optional
import math

from ...image.cylinder_warp import CylinderParams


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
        
        # Preview
        self.preview = CylinderPreviewWidget()
        layout.addWidget(self.preview)
        
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
        """Update the preview widget."""
        self.preview.set_params(
            self.diameter_spin.value(),
            self.max_angle_spin.value()
        )
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

