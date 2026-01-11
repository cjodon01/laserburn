"""
Cylinder Warping Module

Transforms images and generates power compensation for engraving 
on cylindrical surfaces without a rotary attachment.

The technique works by:
1. Pre-distorting the image to compensate for cylinder curvature
2. Adjusting laser power based on the oblique angle to maintain 
   consistent energy density across the curved surface

Mathematical basis:
- At angle θ from vertical (tangent point):
  - Arc length: s = R × θ
  - Flat projection: x = R × sin(θ)
  - Height drop: Δz = R × (1 - cos(θ))
  - Power compensation: 1 / cos(θ)
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional, List, Callable
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from ..core.shapes import Point


@dataclass
class CylinderParams:
    """
    Parameters for cylinder engraving.
    
    Attributes:
        diameter: Cylinder diameter in mm
        engrave_width: Width of engraving area in mm (arc length on surface)
        center_offset: Offset from top of cylinder in degrees (0 = top)
        max_angle: Maximum angle from center in degrees (limits usable area)
    """
    diameter: float
    engrave_width: float = 0.0  # 0 = auto from max_angle
    center_offset: float = 0.0
    max_angle: float = 45.0
    
    @property
    def radius(self) -> float:
        """Get cylinder radius."""
        return self.diameter / 2
    
    def __post_init__(self):
        """Set default engrave_width if not specified."""
        if self.engrave_width <= 0:
            # Default to usable width based on max_angle
            max_theta = math.radians(self.max_angle)
            self.engrave_width = 2 * self.radius * math.sin(max_theta)
    
    def validate(self) -> Tuple[bool, str]:
        """
        Validate parameters.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.diameter <= 0:
            return False, "Diameter must be positive"
        
        if self.max_angle <= 0 or self.max_angle >= 90:
            return False, "Max angle must be between 0 and 90 degrees"
        
        # Check if engrave width exceeds usable arc
        max_arc = 2 * self.radius * math.radians(self.max_angle)
        if self.engrave_width > max_arc * 1.1:  # Allow 10% margin
            return False, (
                f"Engrave width {self.engrave_width:.1f}mm exceeds "
                f"usable arc length {max_arc:.1f}mm at {self.max_angle}° angle"
            )
        
        return True, ""
    
    def get_usable_flat_width(self) -> float:
        """
        Get the maximum usable flat width based on max_angle.
        
        Returns:
            Maximum flat width in mm
        """
        max_theta = math.radians(self.max_angle)
        return 2 * self.radius * math.sin(max_theta)
    
    def get_power_at_edge(self) -> float:
        """
        Get the power multiplier needed at the maximum angle.
        
        Returns:
            Power multiplier (e.g., 1.41 for 45°)
        """
        max_theta = math.radians(self.max_angle)
        return 1.0 / math.cos(max_theta)
    
    def get_z_drop_at_edge(self) -> float:
        """
        Get the Z height drop at the maximum angle.
        
        Returns:
            Z drop in mm
        """
        max_theta = math.radians(self.max_angle)
        return self.radius * (1 - math.cos(max_theta))


class CylinderWarper:
    """
    Transforms images and paths for cylinder engraving.
    
    The warping compensates for the cylinder curvature so that
    the final engraving appears undistorted on the curved surface.
    
    Coordinate Systems:
    - Design Space: Flat design measured in arc length along cylinder
    - Output Space: Actual horizontal laser positions (flat projection)
    
    Example:
        >>> params = CylinderParams(diameter=50, max_angle=45)
        >>> warper = CylinderWarper(params)
        >>> 
        >>> # Warp a design point
        >>> arc_pos = 10.0  # 10mm along the arc from center
        >>> flat_pos = warper.arc_to_flat(arc_pos)
        >>> 
        >>> # Get power compensation
        >>> power_mult = warper.get_power_compensation(flat_pos)
    """
    
    def __init__(self, params: CylinderParams):
        """
        Initialize the cylinder warper.
        
        Args:
            params: Cylinder parameters
        """
        self.params = params
        self.R = params.radius
        
        # Validate parameters
        is_valid, error = params.validate()
        if not is_valid:
            raise ValueError(error)
    
    def arc_to_flat(self, arc_length: float) -> float:
        """
        Convert arc length (design space) to flat projection (output space).
        
        This is how a position on the design maps to the laser's X position.
        
        Args:
            arc_length: Distance along the cylinder surface from center (mm)
            
        Returns:
            Horizontal position in flat output space (mm)
        """
        theta = arc_length / self.R
        return self.R * math.sin(theta)
    
    def flat_to_arc(self, flat_x: float) -> float:
        """
        Convert flat position (output space) to arc length (design space).
        
        This is the inverse mapping used for image warping. Given where
        the laser will be, find what part of the design should be there.
        
        Args:
            flat_x: Horizontal position in output space (mm)
            
        Returns:
            Arc length position in design space (mm)
        """
        # Clamp to valid range to avoid math domain errors
        x_clamped = max(-self.R * 0.999, min(self.R * 0.999, flat_x))
        theta = math.asin(x_clamped / self.R)
        return self.R * theta
    
    def get_stretch_factor(self, arc_length: float) -> float:
        """
        Get the horizontal stretch factor at a given arc position.
        
        This tells you how much the design is stretched when projected
        to the flat output. Values > 1 mean the output is compressed
        relative to the design.
        
        Args:
            arc_length: Distance along cylinder surface from center (mm)
            
        Returns:
            Stretch factor (arc length / flat projection ratio)
        """
        theta = arc_length / self.R
        if abs(theta) < 0.001:
            return 1.0
        return theta / math.sin(theta)
    
    def get_power_compensation(self, flat_x: float) -> float:
        """
        Get the power multiplier needed at a given flat position.
        
        The power needs to increase as the surface angles away from
        the laser to maintain consistent energy density. This is
        because:
        1. The beam hits at an oblique angle, spreading the energy
        2. The spot becomes elliptical, covering more area
        
        Args:
            flat_x: Horizontal position in output space (mm)
            
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
        The surface drops away from the focal plane as you move
        from center.
        
        Args:
            flat_x: Horizontal position in output space (mm)
            
        Returns:
            Z offset in mm (positive = surface is lower than tangent)
        """
        x_ratio = flat_x / self.R
        x_ratio_clamped = max(-1.0, min(1.0, x_ratio))
        cos_theta = math.sqrt(1 - x_ratio_clamped ** 2)
        return self.R * (1 - cos_theta)
    
    def get_angle_at_position(self, flat_x: float) -> float:
        """
        Get the angle (in degrees) at a given flat position.
        
        Args:
            flat_x: Horizontal position in output space (mm)
            
        Returns:
            Angle in degrees from vertical (0 at center)
        """
        x_ratio = flat_x / self.R
        x_ratio_clamped = max(-1.0, min(1.0, x_ratio))
        return math.degrees(math.asin(x_ratio_clamped))
    
    def warp_point(self, design_x: float, design_y: float) -> Tuple[float, float]:
        """
        Warp a single point from design space to output space.
        
        Args:
            design_x: X position in design (arc length from center)
            design_y: Y position in design
            
        Returns:
            Tuple of (output_x, output_y) in output space
        """
        output_x = self.arc_to_flat(design_x)
        # Y doesn't change (assuming horizontal cylinder)
        return (output_x, design_y)
    
    def warp_path(self, path: List[Point], center_x: float = 0) -> List[Point]:
        """
        Warp a path from design space to output space.
        
        Args:
            path: List of Points in design coordinates
            center_x: X coordinate of the design center
            
        Returns:
            List of warped Points in output coordinates
        """
        warped = []
        for pt in path:
            # Convert to arc-centered coordinates
            arc_x = pt.x - center_x
            # Warp
            flat_x = self.arc_to_flat(arc_x)
            # Convert back to output coordinates
            warped.append(Point(flat_x + center_x, pt.y))
        return warped
    
    def generate_power_profile(self, num_steps: int = 100,
                                base_power: float = 100.0,
                                max_power: float = 100.0) -> List[Tuple[float, float]]:
        """
        Generate a power compensation profile across the usable width.
        
        Args:
            num_steps: Number of steps in the profile
            base_power: Power at center (0-100%)
            max_power: Maximum allowed power (0-100%)
            
        Returns:
            List of (x_position, power) tuples
        """
        half_width = self.params.get_usable_flat_width() / 2
        profile = []
        
        for i in range(num_steps):
            # Position from -half_width to +half_width
            x = (i / (num_steps - 1) - 0.5) * 2 * half_width
            compensation = self.get_power_compensation(x)
            power = min(base_power * compensation, max_power)
            profile.append((x, power))
        
        return profile
    
    if HAS_NUMPY:
        def warp_image(self, image: 'np.ndarray',
                       design_width_mm: Optional[float] = None) -> 'np.ndarray':
            """
            Warp an image for cylinder engraving.
            
            The input image represents the design in arc-length space.
            The output image is what should be sent to the laser.
            
            Args:
                image: Input image (numpy array, grayscale or RGB)
                design_width_mm: Width of design in mm. If None, uses engrave_width.
                
            Returns:
                Warped image ready for engraving
            """
            if image.ndim == 2:
                height, width = image.shape
                is_grayscale = True
            else:
                height, width, channels = image.shape
                is_grayscale = False
            
            if design_width_mm is None:
                design_width_mm = self.params.engrave_width
            
            # Calculate the arc and flat ranges
            half_arc = design_width_mm / 2
            half_flat = self.arc_to_flat(half_arc)
            
            # Create output image (same size as input)
            output = np.zeros_like(image)
            
            # For each output column, find the corresponding input column
            for out_x in range(width):
                # Map output pixel to flat position in mm
                flat_x = (out_x / (width - 1) - 0.5) * 2 * half_flat
                
                # Convert to arc position (design space)
                arc_x = self.flat_to_arc(flat_x)
                
                # Map to input pixel coordinate
                # arc_x is in mm, map to pixel space
                in_x = ((arc_x / half_arc) + 1) / 2 * (width - 1)
                
                # Bounds check
                if in_x < 0 or in_x >= width - 1:
                    continue
                
                # Bilinear interpolation
                x0 = int(in_x)
                x1 = min(x0 + 1, width - 1)
                t = in_x - x0
                
                if is_grayscale:
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
                               max_power: float = 100.0) -> 'np.ndarray':
            """
            Generate a 2D power compensation map.
            
            This can be used to modulate laser power during engraving.
            
            Args:
                width: Width of the power map in pixels
                height: Height of the power map in pixels
                base_power: Power at center (0-100%)
                max_power: Maximum allowed power (0-100%)
                
            Returns:
                2D array of power values (0-100%)
            """
            half_flat = self.params.get_usable_flat_width() / 2
            
            power_map = np.zeros((height, width))
            
            for x in range(width):
                # Map pixel to flat position
                flat_x = (x / (width - 1) - 0.5) * 2 * half_flat
                compensation = self.get_power_compensation(flat_x)
                power = min(base_power * compensation, max_power)
                power_map[:, x] = power
            
            return power_map


def apply_cylinder_compensation_to_gcode(
    gcode_lines: List[str],
    params: CylinderParams,
    design_center_x: float = 0,
    base_power: float = 255,
    include_z: bool = False
) -> List[str]:
    """
    Post-process G-code to add cylinder power compensation.
    
    Modifies S (power) values based on X position to compensate
    for the cylinder curvature.
    
    Args:
        gcode_lines: Original G-code lines
        params: Cylinder parameters
        design_center_x: X coordinate of design center
        base_power: Base laser power (S value at center)
        include_z: Whether to add Z compensation commands
        
    Returns:
        Modified G-code lines with power compensation
    """
    import re
    
    warper = CylinderWarper(params)
    modified = []
    
    # Patterns for parsing G-code
    x_pattern = re.compile(r'X(-?\d+\.?\d*)')
    s_pattern = re.compile(r'S(\d+\.?\d*)')
    
    # Add header comments
    modified.append("; === Cylinder Compensation Applied ===")
    modified.append(f"; Diameter: {params.diameter}mm")
    modified.append(f"; Max angle: {params.max_angle}°")
    modified.append(f"; Base power: S{base_power}")
    modified.append("; =====================================")
    
    current_x = 0
    
    for line in gcode_lines:
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith(';'):
            modified.append(line)
            continue
        
        # Find X position
        x_match = x_pattern.search(line)
        if x_match:
            current_x = float(x_match.group(1))
        
        # Find and modify S value
        s_match = s_pattern.search(line)
        if s_match and x_match:
            flat_x = current_x - design_center_x
            
            # Calculate power compensation
            compensation = warper.get_power_compensation(flat_x)
            original_power = float(s_match.group(1))
            new_power = min(original_power * compensation, 1000)  # Clamp to max
            
            # Replace S value
            modified_line = s_pattern.sub(f'S{new_power:.0f}', line)
            
            # Optionally add Z compensation
            if include_z and 'G1' in line:
                z_offset = warper.get_z_offset(flat_x)
                modified_line = modified_line.rstrip() + f' Z{-z_offset:.3f}'
            
            modified.append(modified_line)
        else:
            modified.append(line)
    
    return modified


