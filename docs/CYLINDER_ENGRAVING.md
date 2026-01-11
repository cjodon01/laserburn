# Cylinder Engraving Without Rotary

This document describes how to engrave on cylindrical surfaces without a rotary attachment by using image warping and dynamic power adjustment.

## Concept Overview

When a cylinder lays horizontally under the laser:
- The laser is focused at the top (tangent point)
- The surface curves away from the focal plane
- The laser hits at oblique angles away from center
- Image distortion and power compensation are needed

```
        Laser Beam
             |
             v
         =========  <- Focal plane
            ___
          /     \
         |   R   |   <- Cylinder (radius R)
         |   •   |   <- Center
          \_____/

    <-- usable area -->
```

## Mathematical Foundation

### Coordinate System

- **Design Space**: The flat design measured in arc length along the cylinder
- **Output Space**: The actual horizontal laser positions
- **R**: Cylinder radius
- **θ**: Angle from vertical (0 at tangent point)

### Key Equations

For a point at angle θ from the tangent point:

1. **Arc to Flat Projection**:
   ```
   arc_length = R × θ
   flat_x = R × sin(θ)
   ```

2. **Height Drop (Z offset)**:
   ```
   Δz = R × (1 - cos(θ))
   ```

3. **Image Stretch Factor** (arc/flat ratio):
   ```
   stretch = θ / sin(θ)    [for θ > 0]
   stretch = 1              [for θ = 0]
   ```

4. **Power Compensation Factor**:
   ```
   power_mult = 1 / cos(θ)
   
   Or in terms of x position:
   power_mult = 1 / sqrt(1 - (x/R)²)
   ```

5. **Inverse Mapping** (for image warping):
   ```
   Given output position x, find design position s:
   θ = arcsin(x / R)
   s = R × θ
   ```

## Implementation Guide

### Module: `src/image/cylinder_warp.py`

```python
"""
Cylinder Warping Module

Transforms images for engraving on cylindrical surfaces without a rotary.
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class CylinderParams:
    """Parameters for cylinder engraving."""
    diameter: float          # Cylinder diameter in mm
    engrave_width: float     # Width of engraving area in mm (arc length)
    center_offset: float = 0 # Offset from top of cylinder (degrees)
    max_angle: float = 45.0  # Maximum angle from center (degrees)
    
    @property
    def radius(self) -> float:
        return self.diameter / 2
    
    def validate(self) -> Tuple[bool, str]:
        """Validate parameters."""
        if self.diameter <= 0:
            return False, "Diameter must be positive"
        
        max_arc = self.radius * math.radians(self.max_angle) * 2
        if self.engrave_width > max_arc:
            return False, f"Engrave width {self.engrave_width}mm exceeds usable arc {max_arc:.1f}mm"
        
        return True, ""


class CylinderWarper:
    """
    Transforms images for cylinder engraving.
    
    The warping compensates for the cylinder curvature so that
    the final engraving appears undistorted on the curved surface.
    """
    
    def __init__(self, params: CylinderParams):
        self.params = params
        self.R = params.radius
    
    def arc_to_flat(self, arc_length: float) -> float:
        """
        Convert arc length (design space) to flat projection (output space).
        
        Args:
            arc_length: Distance along the cylinder surface from center
            
        Returns:
            Horizontal position in flat output space
        """
        theta = arc_length / self.R
        return self.R * math.sin(theta)
    
    def flat_to_arc(self, flat_x: float) -> float:
        """
        Convert flat position (output space) to arc length (design space).
        
        This is the inverse mapping used for image warping.
        
        Args:
            flat_x: Horizontal position in output space
            
        Returns:
            Arc length position in design space
        """
        # Clamp to valid range
        x_clamped = max(-self.R, min(self.R, flat_x))
        theta = math.asin(x_clamped / self.R)
        return self.R * theta
    
    def get_stretch_factor(self, arc_length: float) -> float:
        """
        Get the horizontal stretch factor at a given arc position.
        
        Args:
            arc_length: Distance along cylinder surface from center
            
        Returns:
            Stretch factor (arc/flat ratio)
        """
        theta = arc_length / self.R
        if abs(theta) < 0.001:
            return 1.0
        return theta / math.sin(theta)
    
    def get_power_compensation(self, flat_x: float) -> float:
        """
        Get the power multiplier needed at a given flat position.
        
        The power needs to increase as the surface angles away from
        the laser to maintain consistent energy density.
        
        Args:
            flat_x: Horizontal position in output space
            
        Returns:
            Power multiplier (1.0 at center, >1.0 at edges)
        """
        x_ratio = flat_x / self.R
        # Clamp to prevent division by zero near edges
        x_ratio_clamped = max(-0.99, min(0.99, x_ratio))
        cos_theta = math.sqrt(1 - x_ratio_clamped ** 2)
        return 1.0 / cos_theta
    
    def get_z_offset(self, flat_x: float) -> float:
        """
        Get the Z offset (height drop) at a given flat position.
        
        Useful if the laser has Z control for focus compensation.
        
        Args:
            flat_x: Horizontal position in output space
            
        Returns:
            Z offset in mm (positive = surface is lower)
        """
        x_ratio = flat_x / self.R
        x_ratio_clamped = max(-1.0, min(1.0, x_ratio))
        cos_theta = math.sqrt(1 - x_ratio_clamped ** 2)
        return self.R * (1 - cos_theta)
    
    def warp_image(self, image: np.ndarray, 
                   output_width: Optional[int] = None) -> np.ndarray:
        """
        Warp an image for cylinder engraving.
        
        The input image represents the design in arc-length space.
        The output image is what should be sent to the laser.
        
        Args:
            image: Input image (numpy array, grayscale or RGB)
            output_width: Width of output image (default: same as input)
            
        Returns:
            Warped image ready for engraving
        """
        if image.ndim == 2:
            height, width = image.shape
            channels = 1
        else:
            height, width, channels = image.shape
        
        if output_width is None:
            output_width = width
        
        # Calculate the arc length range
        half_arc = self.params.engrave_width / 2
        
        # Calculate the corresponding flat range
        half_flat = self.arc_to_flat(half_arc)
        
        # Create output image
        if channels == 1:
            output = np.zeros((height, output_width), dtype=image.dtype)
        else:
            output = np.zeros((height, output_width, channels), dtype=image.dtype)
        
        # For each output pixel, find the corresponding input pixel
        for out_x in range(output_width):
            # Map output x to flat position
            flat_x = (out_x / (output_width - 1) - 0.5) * 2 * half_flat
            
            # Convert to arc position (design space)
            arc_x = self.flat_to_arc(flat_x)
            
            # Map to input pixel coordinate
            in_x = (arc_x / half_arc + 1) / 2 * (width - 1)
            
            # Bilinear interpolation
            x0 = int(in_x)
            x1 = min(x0 + 1, width - 1)
            t = in_x - x0
            
            if 0 <= x0 < width:
                if channels == 1:
                    output[:, out_x] = (
                        (1 - t) * image[:, x0] + t * image[:, x1]
                    ).astype(image.dtype)
                else:
                    output[:, out_x, :] = (
                        (1 - t) * image[:, x0, :] + t * image[:, x1, :]
                    ).astype(image.dtype)
        
        return output
    
    def generate_power_map(self, width: int, height: int,
                           base_power: float = 100.0,
                           max_power: float = 100.0) -> np.ndarray:
        """
        Generate a power compensation map.
        
        Args:
            width: Width of the power map
            height: Height of the power map
            base_power: Power at center (0-100%)
            max_power: Maximum allowed power (0-100%)
            
        Returns:
            2D array of power values (0-100%)
        """
        half_flat = self.arc_to_flat(self.params.engrave_width / 2)
        
        power_map = np.zeros((height, width))
        
        for x in range(width):
            flat_x = (x / (width - 1) - 0.5) * 2 * half_flat
            compensation = self.get_power_compensation(flat_x)
            power = min(base_power * compensation, max_power)
            power_map[:, x] = power
        
        return power_map
    
    def get_usable_width(self) -> float:
        """
        Get the maximum usable flat width based on max_angle.
        
        Returns:
            Maximum flat width in mm
        """
        max_theta = math.radians(self.params.max_angle)
        return 2 * self.R * math.sin(max_theta)


def create_cylinder_gcode_modifier(params: CylinderParams):
    """
    Create a G-code modifier function for cylinder power compensation.
    
    This can be used as a post-processor for generated G-code.
    
    Args:
        params: Cylinder parameters
        
    Returns:
        Function that modifies G-code lines for power compensation
    """
    warper = CylinderWarper(params)
    
    def modify_gcode(gcode_lines: list, 
                     design_center_x: float,
                     base_power: float) -> list:
        """
        Modify G-code for cylinder power compensation.
        
        Args:
            gcode_lines: List of G-code lines
            design_center_x: X coordinate of design center
            base_power: Base laser power (S value)
            
        Returns:
            Modified G-code lines
        """
        import re
        
        modified = []
        x_pattern = re.compile(r'X(-?\d+\.?\d*)')
        s_pattern = re.compile(r'S(\d+\.?\d*)')
        
        for line in gcode_lines:
            # Find X position
            x_match = x_pattern.search(line)
            s_match = s_pattern.search(line)
            
            if x_match and s_match:
                x_pos = float(x_match.group(1))
                flat_x = x_pos - design_center_x
                
                # Calculate power compensation
                compensation = warper.get_power_compensation(flat_x)
                new_power = min(base_power * compensation, 1000)  # S max
                
                # Replace S value
                line = s_pattern.sub(f'S{new_power:.0f}', line)
            
            modified.append(line)
        
        return modified
    
    return modify_gcode
```

### Module: `src/ui/dialogs/cylinder_dialog.py`

```python
"""
Cylinder Engraving Dialog

UI for configuring cylinder engraving parameters.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDoubleSpinBox, QLabel, QPushButton, QGroupBox,
    QCheckBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor
from typing import Optional


class CylinderPreviewWidget(QWidget):
    """Widget showing cylinder cross-section preview."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.diameter = 50.0
        self.max_angle = 45.0
        self.setMinimumSize(200, 150)
    
    def set_params(self, diameter: float, max_angle: float):
        self.diameter = diameter
        self.max_angle = max_angle
        self.update()
    
    def paintEvent(self, event):
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
        import math
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cylinder Engraving Settings")
        self.setMinimumWidth(400)
        self._init_ui()
    
    def _init_ui(self):
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
        self.diameter_spin.valueChanged.connect(self._update_preview)
        params_layout.addRow("Diameter:", self.diameter_spin)
        
        self.max_angle_spin = QDoubleSpinBox()
        self.max_angle_spin.setRange(10, 80)
        self.max_angle_spin.setValue(45)
        self.max_angle_spin.setSuffix("°")
        self.max_angle_spin.valueChanged.connect(self._update_preview)
        params_layout.addRow("Max Angle:", self.max_angle_spin)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Calculated values
        calc_group = QGroupBox("Calculated Values")
        calc_layout = QFormLayout()
        
        self.usable_width_label = QLabel()
        calc_layout.addRow("Usable Width:", self.usable_width_label)
        
        self.power_at_edge_label = QLabel()
        calc_layout.addRow("Power at Edge:", self.power_at_edge_label)
        
        self.z_drop_label = QLabel()
        calc_layout.addRow("Z Drop at Edge:", self.z_drop_label)
        
        calc_group.setLayout(calc_layout)
        layout.addWidget(calc_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.warp_image_check = QCheckBox("Warp image for cylinder")
        self.warp_image_check.setChecked(True)
        options_layout.addWidget(self.warp_image_check)
        
        self.power_comp_check = QCheckBox("Apply power compensation")
        self.power_comp_check.setChecked(True)
        options_layout.addWidget(self.power_comp_check)
        
        self.z_comp_check = QCheckBox("Apply Z compensation (if available)")
        self.z_comp_check.setChecked(False)
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
    
    def _update_preview(self):
        self.preview.set_params(
            self.diameter_spin.value(),
            self.max_angle_spin.value()
        )
        self._update_calculations()
    
    def _update_calculations(self):
        import math
        
        r = self.diameter_spin.value() / 2
        theta = math.radians(self.max_angle_spin.value())
        
        # Usable width
        usable_width = 2 * r * math.sin(theta)
        self.usable_width_label.setText(f"{usable_width:.1f} mm")
        
        # Power at edge
        power_mult = 1 / math.cos(theta)
        self.power_at_edge_label.setText(f"{power_mult:.2f}× ({power_mult * 100:.0f}%)")
        
        # Z drop
        z_drop = r * (1 - math.cos(theta))
        self.z_drop_label.setText(f"{z_drop:.2f} mm")
    
    def get_params(self):
        """Get the cylinder parameters."""
        from ..image.cylinder_warp import CylinderParams
        return CylinderParams(
            diameter=self.diameter_spin.value(),
            engrave_width=2 * self.diameter_spin.value() / 2 * 
                         math.sin(math.radians(self.max_angle_spin.value())),
            max_angle=self.max_angle_spin.value()
        )
```

## G-Code Integration

### Power Modulation During Engraving

When generating G-code for cylinder engraving, the power (S value) should be adjusted based on position:

```python
def generate_cylinder_gcode(paths, params: CylinderParams, 
                            base_power: float, speed: float) -> str:
    """
    Generate G-code with cylinder power compensation.
    """
    from .cylinder_warp import CylinderWarper
    
    warper = CylinderWarper(params)
    gcode_lines = [
        "; Cylinder engraving mode",
        f"; Diameter: {params.diameter}mm",
        f"; Max angle: {params.max_angle}°",
        "G21 ; mm",
        "G90 ; absolute",
        "M3 S0 ; laser on, zero power",
    ]
    
    design_center_x = 0  # Center of design
    
    for path in paths:
        if not path:
            continue
        
        # Move to start
        start = path[0]
        gcode_lines.append(f"G0 X{start.x:.3f} Y{start.y:.3f}")
        
        for point in path[1:]:
            # Calculate power compensation
            flat_x = point.x - design_center_x
            compensation = warper.get_power_compensation(flat_x)
            adjusted_power = min(base_power * compensation, 1000)
            
            # Optional: Z compensation
            z_offset = warper.get_z_offset(flat_x)
            
            gcode_lines.append(
                f"G1 X{point.x:.3f} Y{point.y:.3f} S{adjusted_power:.0f} F{speed:.0f}"
            )
    
    gcode_lines.append("M5 ; laser off")
    return '\n'.join(gcode_lines)
```

## Usage Workflow

1. **Setup**:
   - Measure cylinder diameter accurately
   - Position cylinder with tangent point under laser focus
   - Secure cylinder to prevent rolling

2. **In LaserBurn**:
   - Open image/design to engrave
   - Go to **Edit → Cylinder Engraving**
   - Enter cylinder diameter
   - Set maximum angle (45° recommended)
   - Enable warping and power compensation

3. **Preview**:
   - Review the warped preview
   - Check power compensation values
   - Adjust if needed

4. **Engrave**:
   - Generate G-code (automatically compensated)
   - Run the job

## Limitations

1. **Depth of Field**: The laser will defocus at edges. Use smaller max angles for precision work.

2. **Power Limits**: At 60°, power needs to double. Ensure your laser can handle the peak power.

3. **Edge Quality**: Quality degrades past 45°. For full wrap, use multiple passes with rotation.

4. **Material Thickness**: Very thick materials may need additional compensation.

## Examples

### Small Cylinder (Pen, 10mm diameter)
- Max angle: 30° (conservative)
- Usable width: 5mm
- Power at edge: 1.15×

### Medium Cylinder (Bottle, 75mm diameter)  
- Max angle: 45° (standard)
- Usable width: 53mm
- Power at edge: 1.41×

### Large Cylinder (Tumbler, 90mm diameter)
- Max angle: 60° (aggressive)
- Usable width: 78mm
- Power at edge: 2.0×

## Testing Procedure

1. Create a test grid pattern
2. Engrave on a test cylinder (same material/diameter)
3. Check:
   - Line straightness (warping)
   - Consistent darkness (power)
   - Edge sharpness (focus)
4. Adjust parameters if needed

## Future Enhancements

- [ ] Real-time preview with 3D cylinder visualization
- [ ] Automatic diameter detection using camera
- [ ] Multi-pass mode for full-wrap engraving
- [ ] Focus compensation for Z-axis equipped lasers
- [ ] Material-specific power curves

