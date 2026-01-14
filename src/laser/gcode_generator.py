"""
G-Code Generator for LaserBurn

Converts vector paths to G-code for GRBL and compatible controllers.
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import math

from ..core.shapes import Point, Shape, LaserSettings, ImageShape
from ..core.document import Document
from ..core.layer import Layer
from .path_optimizer import optimize_paths

# Import dithering for image processing
try:
    from ..image.dithering import ImageDitherer, DitheringMethod, adjust_brightness_contrast
    HAS_DITHERING = True
except ImportError:
    HAS_DITHERING = False


class LaserMode(Enum):
    """Laser control mode."""
    CONSTANT = "M3"  # Constant power mode (recommended for consistent power)
    DYNAMIC = "M4"   # Dynamic power (scales with speed - can cause inconsistent power)


class StartFrom(Enum):
    """Where to start the job from."""
    HOME = "home"              # Start from machine home (0,0,0) - absolute coordinates
    CURRENT_POSITION = "current"  # Start from current position - relative coordinates


class JobOrigin(Enum):
    """Which point of the design corresponds to the start point."""
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    MIDDLE_LEFT = "middle-left"
    CENTER = "center"
    MIDDLE_RIGHT = "middle-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"


@dataclass
class GCodeSettings:
    """Settings for G-code generation."""
    
    # Units and positioning
    use_mm: bool = True              # G21 vs G20
    absolute_coords: bool = True      # G90 vs G91
    
    # Laser settings
    max_power: int = 1000             # Max S value - MUST match GRBL $30 setting (default: 1000)
    laser_mode: LaserMode = LaserMode.CONSTANT  # Use constant power for consistent results
    
    # Speed settings
    rapid_speed: float = 6000.0      # mm/min for G0 moves
    default_cut_speed: float = 1000.0  # mm/min for G1 moves
    
    # Machine settings
    origin: str = "bottom-left"      # Origin position (deprecated - use job_origin)
    home_on_start: bool = False      # Home machine at start
    return_to_origin: bool = True    # Return to origin at end
    
    # Start point and origin settings
    start_from: StartFrom = StartFrom.HOME  # Where to start the job from
    job_origin: JobOrigin = JobOrigin.CENTER  # Which point of design corresponds to start point
    
    # Machine work area limits (in mm)
    # These define the physical limits of the laser bed
    work_area_x: float = 400.0       # Maximum X travel (mm) - default 400mm
    work_area_y: float = 400.0       # Maximum Y travel (mm) - default 400mm
    work_area_z: float = 50.0        # Maximum Z travel (mm)
    min_x: float = 0.0               # Minimum X (usually 0)
    min_y: float = 0.0               # Minimum Y (usually 0)
    min_z: float = 0.0               # Minimum Z (usually 0)
    
    # Safety
    laser_off_delay: float = 0.0     # Delay after M5 (ms)
    
    # Optimization
    optimize_paths: bool = True      # Reorder paths
    min_power: float = 0.0           # Min power for traversal
    
    def validate_coordinate(self, x: float, y: float, z: float = 0.0) -> tuple[bool, str]:
        """
        Validate if coordinates are within machine limits.
        
        Returns:
            (is_valid, error_message)
        """
        if x < self.min_x or x > self.work_area_x:
            return False, f"X coordinate {x:.2f}mm is outside work area ({self.min_x:.2f} - {self.work_area_x:.2f}mm)"
        if y < self.min_y or y > self.work_area_y:
            return False, f"Y coordinate {y:.2f}mm is outside work area ({self.min_y:.2f} - {self.work_area_y:.2f}mm)"
        if z < self.min_z or z > self.work_area_z:
            return False, f"Z coordinate {z:.2f}mm is outside work area ({self.min_z:.2f} - {self.work_area_z:.2f}mm)"
        return True, ""
    
    def get_max_coordinates(self) -> tuple[float, float, float]:
        """Get maximum valid coordinates."""
        return (self.work_area_x, self.work_area_y, self.work_area_z)


class GCodeGenerator:
    """Generate G-code from LaserBurn documents."""
    
    def __init__(self, settings: GCodeSettings = None):
        self.settings = settings or GCodeSettings()
        self._gcode_lines: List[str] = []
        self._current_x: float = 0.0
        self._current_y: float = 0.0
        self._laser_on: bool = False
        self._current_power: int = 0
        self._current_speed: float = 0.0
    
    def generate(self, document: Document) -> tuple[str, list[str]]:
        """
        Generate G-code for an entire document.
        
        Returns:
            (gcode_string, warnings_list)
        """
        self._reset_state()
        self._gcode_lines = []
        warnings = []
        
        # Check document dimensions against machine limits
        if document.width > self.settings.work_area_x:
            warnings.append(f"Document width ({document.width:.2f}mm) exceeds machine X limit ({self.settings.work_area_x:.2f}mm)")
        if document.height > self.settings.work_area_y:
            warnings.append(f"Document height ({document.height:.2f}mm) exceeds machine Y limit ({self.settings.work_area_y:.2f}mm)")
        
        # Count total visible shapes for debugging
        total_shapes = 0
        for layer in document.layers:
            if layer.visible:
                for shape in layer.shapes:
                    if shape.visible:
                        total_shapes += 1
        
        # Check all shapes' bounding boxes
        for layer in document.layers:
            if not layer.visible:
                continue
            for shape in layer.shapes:
                if not shape.visible:
                    continue
                try:
                    bbox = shape.get_bounding_box()
                    if bbox.max_x > self.settings.work_area_x:
                        warnings.append(f"Shape '{shape.name}' extends beyond X limit (max: {bbox.max_x:.2f}mm, limit: {self.settings.work_area_x:.2f}mm)")
                    if bbox.max_y > self.settings.work_area_y:
                        warnings.append(f"Shape '{shape.name}' extends beyond Y limit (max: {bbox.max_y:.2f}mm, limit: {self.settings.work_area_y:.2f}mm)")
                except Exception as e:
                    warnings.append(f"Could not get bounding box for shape: {e}")
        
        # Store document dimensions for coordinate transformation
        self._current_document_height = document.height
        self._current_document_width = document.width
        
        # Calculate job origin offset (which point of design should be at start position)
        self._job_origin_offset_x, self._job_origin_offset_y = self._calculate_job_origin_offset(document)
        
        # Header
        self._add_header(document)
        
        # Process layers in cut order
        sorted_layers = sorted(document.layers, key=lambda l: l.cut_order)
        
        for layer in sorted_layers:
            if not layer.visible:
                continue
            
            self._process_layer(layer)
        
        # Footer
        self._add_footer()
        
        return '\n'.join(self._gcode_lines), warnings
    
    def _reset_state(self):
        """Reset generator state."""
        self._current_x = 0.0
        self._current_y = 0.0
        self._laser_on = False
        self._current_power = 0
        self._current_speed = 0.0
        self._job_origin_offset_x = 0.0
        self._job_origin_offset_y = 0.0
        self._use_relative_mode = False  # Set in _add_header based on start_from mode
    
    def _calculate_job_origin_offset(self, document: Document) -> tuple[float, float]:
        """
        Calculate offset based on job_origin setting.
        
        Returns:
            (offset_x, offset_y) - offset to apply IN LASER COORDINATES so the selected 
            job origin point is at (0,0) in laser space.
            
        Note: These offsets are applied AFTER the canvas-to-laser coordinate transformation.
        Note: For HOME mode, no offset is applied - design stays at document position.
        """
        # For HOME mode, don't apply any offset
        # Design should be at its actual document position
        if self.settings.start_from == StartFrom.HOME:
            return 0.0, 0.0
        
        # Get design bounds
        bounds = document.get_design_bounds()
        if not bounds or (bounds.max_x == bounds.min_x and bounds.max_y == bounds.min_y):
            # Empty or single point design
            return 0.0, 0.0
        
        design_width = bounds.max_x - bounds.min_x
        design_height = bounds.max_y - bounds.min_y
        
        # First, find the canvas coordinates of the selected job origin point
        # Canvas coordinates: origin is top-left, X increases right, Y increases down
        if self.settings.job_origin == JobOrigin.TOP_LEFT:
            canvas_x = bounds.min_x
            canvas_y = bounds.min_y
        elif self.settings.job_origin == JobOrigin.TOP_CENTER:
            canvas_x = bounds.min_x + design_width / 2.0
            canvas_y = bounds.min_y
        elif self.settings.job_origin == JobOrigin.TOP_RIGHT:
            canvas_x = bounds.max_x
            canvas_y = bounds.min_y
        elif self.settings.job_origin == JobOrigin.MIDDLE_LEFT:
            canvas_x = bounds.min_x
            canvas_y = bounds.min_y + design_height / 2.0
        elif self.settings.job_origin == JobOrigin.CENTER:
            canvas_x = bounds.min_x + design_width / 2.0
            canvas_y = bounds.min_y + design_height / 2.0
        elif self.settings.job_origin == JobOrigin.MIDDLE_RIGHT:
            canvas_x = bounds.max_x
            canvas_y = bounds.min_y + design_height / 2.0
        elif self.settings.job_origin == JobOrigin.BOTTOM_LEFT:
            canvas_x = bounds.min_x
            canvas_y = bounds.max_y
        elif self.settings.job_origin == JobOrigin.BOTTOM_CENTER:
            canvas_x = bounds.min_x + design_width / 2.0
            canvas_y = bounds.max_y
        elif self.settings.job_origin == JobOrigin.BOTTOM_RIGHT:
            canvas_x = bounds.max_x
            canvas_y = bounds.max_y
        else:
            # Default to center
            canvas_x = bounds.min_x + design_width / 2.0
            canvas_y = bounds.min_y + design_height / 2.0
        
        # Now transform this point to laser coordinates (Y-flip)
        # Laser coordinates: origin is bottom-left, X increases right, Y increases up
        # laser_x = canvas_x
        # laser_y = document_height - canvas_y
        laser_x = canvas_x
        laser_y = document.height - canvas_y
        
        # The offset is the NEGATIVE of this position (to move it to origin)
        # This offset will be applied AFTER the Y-flip in _canvas_to_laser
        return -laser_x, -laser_y
    
    def _add_header(self, document: Document):
        """Add G-code header/preamble."""
        self._emit("; LaserBurn G-Code Output")
        self._emit(f"; Document: {document.name}")
        self._emit(f"; Size: {document.width}mm x {document.height}mm")
        self._emit(f"; Start From: {self.settings.start_from.value}")
        self._emit(f"; Job Origin: {self.settings.job_origin.value}")
        
        # Get design bounds for header info
        bounds = document.get_design_bounds()
        if bounds:
            # Calculate actual transformed bounds (in laser coordinates with offset applied)
            # Bottom-left in canvas: (min_x, max_y), top-right in canvas: (max_x, min_y)
            # Transform to laser coords then apply offset
            bl_laser_x = bounds.min_x + self._job_origin_offset_x
            bl_laser_y = (document.height - bounds.max_y) + self._job_origin_offset_y
            tr_laser_x = bounds.max_x + self._job_origin_offset_x
            tr_laser_y = (document.height - bounds.min_y) + self._job_origin_offset_y
            self._emit(f"; Bounds: X{bl_laser_x:.2f} Y{bl_laser_y:.2f} to X{tr_laser_x:.2f} Y{tr_laser_y:.2f}")
        self._emit("")
        
        # Standard G-code setup (like LightBurn: G00 G17 G40 G21 G54)
        self._emit("G00 G17 G40 G21 G54")
        
        # For User Origin and Current Position, use RELATIVE mode (G91)
        # This is how LightBurn handles these modes - all coordinates are relative
        # to the current position, which is at the selected job origin point
        if self.settings.start_from == StartFrom.CURRENT_POSITION:
            self._emit("G91 ; Relative positioning (current position/user origin mode)")
            self._use_relative_mode = True
        else:
            # Home mode uses absolute coordinates
            if self.settings.absolute_coords:
                self._emit("G90 ; Absolute positioning")
            else:
                self._emit("G91 ; Relative positioning")
            self._use_relative_mode = not self.settings.absolute_coords
            
            # Home if requested
            if self.settings.home_on_start:
                self._emit("$H ; Home machine")
        
        # Laser mode and rapid speed
        self._emit(f"{self.settings.laser_mode.value} ; Laser mode")
        self._emit(f"G0 F{self.settings.rapid_speed} ; Set rapid speed")
        self._emit("")
    
    def _add_footer(self):
        """Add G-code footer/cleanup."""
        self._emit("")
        self._emit("; End of job")
        self._laser_off()
        
        if self.settings.return_to_origin:
            if self._use_relative_mode:
                # In relative mode, return to origin means moving back to (0,0)
                # which is our starting point (job origin)
                dx = -self._current_x
                dy = -self._current_y
                if abs(dx) > 0.0001 or abs(dy) > 0.0001:
                    self._emit(f"G0 X{dx:.3f} Y{dy:.3f} ; Return to origin")
            else:
                self._emit("G0 X0 Y0 ; Return to origin")
        
        self._emit("M5 ; Ensure laser off")
        self._emit("M2 ; End program")
    
    def _process_layer(self, layer: Layer):
        """Process all shapes in a layer."""
        self._emit(f"; Layer: {layer.name}")
        
        # Get layer settings
        layer_settings = layer.laser_settings if layer.use_layer_settings else None
        
        # Collect all paths from layer
        all_paths = []
        path_settings = []
        fill_paths = []  # For fill patterns
        fill_settings = []  # Settings for fill paths
        
        for shape in layer.shapes:
            if not shape.visible:
                continue
            
            try:
                # Get settings for this shape
                if layer.use_layer_settings:
                    settings = layer.laser_settings
                else:
                    settings = shape.laser_settings
                
                # Handle ImageShape specially - generate scanlines
                if isinstance(shape, ImageShape):
                    self._process_image_shape(shape, settings)
                    continue
                
                paths = shape.get_paths()
                # Filter out empty paths
                valid_paths = [p for p in paths if p and len(p) > 0]
                
                if not valid_paths:
                    # Text shapes might return empty paths if text is empty or font issue
                    # Skip silently or log a warning
                    continue
                
                # Check if fill is enabled
                if settings.fill_enabled:
                    # Generate fill patterns for closed paths
                    for path in valid_paths:
                        if len(path) >= 3:  # Need at least 3 points for a closed shape
                            # Check if path is closed (first and last points are same or close)
                            is_closed = (abs(path[0].x - path[-1].x) < 0.01 and 
                                       abs(path[0].y - path[-1].y) < 0.01)
                            
                            if is_closed:
                                # Generate fill pattern
                                fill_lines = self._generate_fill_pattern(path, settings)
                                fill_paths.extend(fill_lines)
                                fill_settings.extend([settings] * len(fill_lines))
                            else:
                                # Not closed - add as outline
                                all_paths.append(path)
                                path_settings.append(settings)
                        else:
                            # Too few points - add as outline
                            all_paths.append(path)
                            path_settings.append(settings)
                else:
                    # No fill - add as outline paths
                    for path in valid_paths:
                        all_paths.append(path)
                        path_settings.append(settings)
            except Exception as e:
                # Log error but continue processing other shapes
                print(f"Error processing shape {shape.name if hasattr(shape, 'name') else 'unknown'}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Process outlines first
        if all_paths:
            # Optimize path order if enabled
            if self.settings.optimize_paths:
                start = Point(self._current_x, self._current_y)
                all_paths = optimize_paths(all_paths, start)
            
            # Cut each outline path
            for i, path in enumerate(all_paths):
                settings = path_settings[min(i, len(path_settings)-1)]
                self._cut_path(path, settings)
        
        # Process fill patterns
        if fill_paths:
            self._emit("; Fill patterns")
            # Optimize fill path order if enabled
            if self.settings.optimize_paths:
                start = Point(self._current_x, self._current_y)
                fill_paths = optimize_paths(fill_paths, start)
            
            # Cut each fill line
            for i, fill_line in enumerate(fill_paths):
                settings = fill_settings[min(i, len(fill_settings)-1)]
                self._cut_path(fill_line, settings)
        
        self._emit("")
    
    def _process_image_shape(self, image_shape: ImageShape, settings: LaserSettings):
        """
        Process an ImageShape by generating scanlines for engraving.
        
        This converts the image to scanlines at the specified DPI,
        applying dithering to convert grayscale to on/off laser pulses.
        """
        if image_shape.image_data is None:
            return
        
        self._emit(f"; Image: {image_shape.filepath}")
        
        import numpy as np
        
        # Get image data and dimensions
        img = image_shape.image_data.copy()
        img_height, img_width = img.shape
        
        # Get output dimensions in mm (accounting for scale)
        out_width_mm = image_shape.width * abs(image_shape.scale_x)
        out_height_mm = image_shape.height * abs(image_shape.scale_y)
        
        # Calculate DPI and line spacing
        dpi = image_shape.dpi
        mm_per_inch = 25.4
        line_spacing_mm = mm_per_inch / dpi  # Distance between scan lines
        
        # Calculate number of scanlines
        num_lines = int(out_height_mm / line_spacing_mm)
        
        # Calculate power value
        power = int((settings.power / 100.0) * self.settings.max_power)
        speed = settings.speed * 60  # Convert mm/s to mm/min
        
        # Get alpha channel for transparency handling
        alpha_channel = getattr(image_shape, 'alpha_channel', None)
        
        # Apply brightness/contrast adjustments before dithering
        # Transparent pixels are not adjusted (preserved as-is)
        if HAS_DITHERING:
            brightness = getattr(image_shape, 'brightness', 0.0)
            contrast = getattr(image_shape, 'contrast', 1.0)
            
            if brightness != 0 or contrast != 1.0:
                img = adjust_brightness_contrast(img, brightness, contrast, alpha_channel)
        
        # Apply invert if enabled
        # Transparent pixels are not inverted (they remain transparent)
        if getattr(image_shape, 'invert', False):
            if alpha_channel is not None:
                # Only invert non-transparent pixels
                mask = alpha_channel >= 255
                img[mask] = 255 - img[mask]
            else:
                # No transparency - invert all pixels
                img = 255 - img
        
        # Apply dithering to convert grayscale to binary
        if HAS_DITHERING:
            dither_mode = getattr(image_shape, 'dither_mode', 'floyd_steinberg')
            if dither_mode == 'floyd_steinberg':
                method = DitheringMethod.FLOYD_STEINBERG
            elif dither_mode == 'jarvis':
                method = DitheringMethod.JARVIS_JUDICE_NINKE
            elif dither_mode == 'stucki':
                method = DitheringMethod.STUCKI
            elif dither_mode == 'atkinson':
                method = DitheringMethod.ATKINSON
            elif dither_mode == 'bayer' or dither_mode == 'bayer_4x4':
                method = DitheringMethod.BAYER_4x4
            elif dither_mode == 'bayer_2x2':
                method = DitheringMethod.BAYER_2x2
            elif dither_mode == 'bayer_8x8':
                method = DitheringMethod.BAYER_8x8
            elif dither_mode == 'none':
                method = DitheringMethod.NONE
            else:
                method = DitheringMethod.FLOYD_STEINBERG
            
            ditherer = ImageDitherer(method)
            binary_img = ditherer.dither(img, image_shape.threshold, alpha_channel)
        else:
            # Simple threshold if dithering not available
            binary_img = np.where(img >= image_shape.threshold, 255, 0).astype(np.uint8)
        
        # Transform image position from canvas coordinates to laser coordinates
        # Get document dimensions (should be set by generate() method)
        document_height = getattr(self, '_current_document_height', 400.0)  # Default fallback
        document_width = getattr(self, '_current_document_width', 400.0)  # Default fallback
        
        # Check if image is rotated (if so, we need to transform scanlines)
        has_rotation = abs(image_shape.rotation) > 0.001  # More than ~0.06 degrees
        
        # Calculate pixel-to-mm conversion
        px_to_mm = out_width_mm / img_width
        
        # Get image position in canvas coordinates
        # ImageShape.position is the top-left corner in canvas coordinates
        # Canvas: origin at top-left, Y increases downward
        img_top_left_x = image_shape.position.x
        img_top_left_y = image_shape.position.y
        img_bottom_y = img_top_left_y + out_height_mm  # Bottom edge in canvas coords
        
        # Use M4 (dynamic power mode) for image engraving (like LightBurn)
        self._emit("M4 ; Dynamic power mode for image engraving")
        
        # Now set the engraving feed rate
        self._emit(f"G1 F{speed:.0f} ; Set feed rate")
        
        # Image scanlines are always done in relative mode internally
        # If we're not already in relative mode, switch to it
        if not self._use_relative_mode:
            self._emit("G91 ; Relative mode for image scanlines")
        
        # Generate scanlines (bidirectional for efficiency)
        # Scanlines go from bottom to top in canvas coordinates
        for line_idx in range(num_lines):
            # Canvas Y position for this scanline
            # Start from bottom and work upward
            canvas_y = img_bottom_y - (line_idx * line_spacing_mm)
            
            # Calculate which row of image pixels to sample
            # Image rows are stored top to bottom, but we're scanning bottom to top
            img_row = int(((num_lines - 1 - line_idx) / num_lines) * img_height)
            if img_row >= img_height:
                img_row = img_height - 1
            if img_row < 0:
                img_row = 0
            
            # Get pixel row
            row_data = binary_img[img_row]
            
            # Determine scan direction (bidirectional)
            reverse = (line_idx % 2 == 1)
            
            # Build runs of consecutive pixels with same state
            # A run is (start_px, end_px, is_on) where is_on means engrave
            runs = []
            in_run = False
            run_start = 0
            current_state = False
            
            # Iterate through pixels in scan direction
            pixel_range = range(img_width - 1, -1, -1) if reverse else range(img_width)
            
            for px in pixel_range:
                pixel_on = row_data[px] == 0  # 0 = black = engrave
                
                if pixel_on != current_state:
                    # State changed
                    if in_run:
                        # Close previous run
                        runs.append((run_start, px, current_state))
                    # Start new run
                    run_start = px
                    current_state = pixel_on
                    in_run = True
                elif not in_run:
                    # Start first run
                    run_start = px
                    current_state = pixel_on
                    in_run = True
            
            # Close final run
            if in_run:
                final_px = 0 if reverse else img_width
                runs.append((run_start, final_px, current_state))
            
            # Skip empty lines
            if not runs:
                # Still need to move Y for next scanline
                if line_idx < num_lines - 1:
                    self._emit(f"G1 Y{line_spacing_mm:.3f} ; Move to next scanline")
                continue
            
            # If image is rotated, transform scanline points
            if has_rotation:
                # Transform each run from local to canvas coordinates
                scanline_segments = []
                for run_start_px, run_end_px, is_on in runs:
                    # Convert pixel coordinates to local mm coordinates
                    if reverse:
                        local_x_start = (img_width - run_start_px) * px_to_mm
                        local_x_end = (img_width - run_end_px) * px_to_mm
                    else:
                        local_x_start = run_start_px * px_to_mm
                        local_x_end = run_end_px * px_to_mm
                    
                    # Local Y: 0 = top, height = bottom
                    local_y = out_height_mm - (line_idx * line_spacing_mm)
                    
                    # Create points in local coordinate system
                    p1_local = Point(local_x_start, local_y)
                    p2_local = Point(local_x_end, local_y)
                    
                    # Transform from local to canvas coordinates
                    transformed_points = image_shape.apply_transform([p1_local, p2_local])
                    p1_canvas = transformed_points[0]
                    p2_canvas = transformed_points[1]
                    
                    scanline_segments.append((p1_canvas, p2_canvas, is_on))
                
                # Convert to laser coordinates and emit
                if scanline_segments:
                    first_seg = scanline_segments[0]
                    start_point = first_seg[0] if not reverse else first_seg[1]
                    laser_start = self._canvas_to_laser(start_point, document_height, document_width)
                    
                    # Move to start
                    if abs(laser_start.x - self._current_x) > 0.001 or abs(laser_start.y - self._current_y) > 0.001:
                        dx = laser_start.x - self._current_x
                        dy = laser_start.y - self._current_y
                        self._emit(f"G0 X{dx:.3f} Y{dy:.3f} ; Move to scanline start")
                        self._current_x = laser_start.x
                        self._current_y = laser_start.y
                    
                    # Emit each segment
                    for p1_canvas, p2_canvas, is_on in scanline_segments:
                        p1_laser = self._canvas_to_laser(p1_canvas, document_height, document_width)
                        p2_laser = self._canvas_to_laser(p2_canvas, document_height, document_width)
                        
                        # Move to segment start if needed
                        if abs(p1_laser.x - self._current_x) > 0.001 or abs(p1_laser.y - self._current_y) > 0.001:
                            dx = p1_laser.x - self._current_x
                            dy = p1_laser.y - self._current_y
                            self._emit(f"G0 X{dx:.3f} Y{dy:.3f} ; Move to segment start")
                            self._current_x = p1_laser.x
                            self._current_y = p1_laser.y
                        
                        # Emit the engraving move
                        dx = p2_laser.x - self._current_x
                        dy = p2_laser.y - self._current_y
                        s_value = power if is_on else 0
                        if abs(dx) > 0.001 or abs(dy) > 0.001:
                            self._emit(f"G1 X{dx:.3f} Y{dy:.3f} S{s_value}")
                        self._current_x = p2_laser.x
                        self._current_y = p2_laser.y
            else:
                # No rotation - simple horizontal scanlines in canvas coordinates
                # Convert canvas Y to laser Y for positioning
                laser_y = self._canvas_to_laser(Point(img_top_left_x, canvas_y), document_height, document_width).y
                
                # Calculate X position for start of this scanline
                if line_idx == 0:
                    # First scanline: move to start position
                    if reverse:
                        # Start at right edge
                        canvas_x_start = img_top_left_x + out_width_mm
                    else:
                        # Start at left edge
                        canvas_x_start = img_top_left_x
                    
                    # Convert to laser coordinates
                    laser_start = self._canvas_to_laser(Point(canvas_x_start, canvas_y), document_height, document_width)
                    dx = laser_start.x - self._current_x
                    dy = laser_start.y - self._current_y
                    if abs(dx) > 0.001 or abs(dy) > 0.001:
                        self._emit(f"G0 X{dx:.3f} Y{dy:.3f} ; Move to scanline start")
                    self._current_x = laser_start.x
                    self._current_y = laser_start.y
                else:
                    # Subsequent scanlines: need to move X to start and Y up
                    prev_reverse = ((line_idx - 1) % 2 == 1)
                    
                    if reverse:
                        # This line is reverse: need to be at right end
                        if prev_reverse:
                            # Last line was also reverse: ended at left, move to right
                            x_move = out_width_mm
                        else:
                            # Last line was forward: ended at right, already there
                            x_move = 0
                    else:
                        # This line is forward: need to be at left end
                        if prev_reverse:
                            # Last line was reverse: ended at left, already there
                            x_move = 0
                        else:
                            # Last line was forward: ended at right, move back to left
                            x_move = -out_width_mm
                    
                    # Move Y up and X to start position
                    if abs(x_move) > 0.001:
                        self._emit(f"G1 X{x_move:.3f} Y{line_spacing_mm:.3f} ; Move to next scanline")
                    else:
                        self._emit(f"G1 Y{line_spacing_mm:.3f} ; Move to next scanline")
                    self._current_x += x_move
                    self._current_y += line_spacing_mm
                
                # Generate scanline segments (all in relative mode)
                for run_start_px, run_end_px, is_on in runs:
                    if reverse:
                        # Going left: move is negative
                        move_mm = (run_end_px - run_start_px) * px_to_mm
                    else:
                        # Going right: move is positive
                        move_mm = (run_end_px - run_start_px) * px_to_mm
                    
                    # Only emit non-zero moves
                    if abs(move_mm) > 0.001:
                        s_value = power if is_on else 0
                        self._emit(f"G1 X{move_mm:.3f} S{s_value}")
                        self._current_x += move_mm
        
        # Switch back to absolute mode ONLY if we weren't in relative mode to begin with
        # (for current position mode, we stay in relative mode)
        if not self._use_relative_mode:
            self._emit("G90 ; Back to absolute mode")
        
        # Turn off laser and restore M3 mode
        self._emit("M5 ; Laser off")
        self._emit("M3 ; Restore constant power mode")
        
        self._emit(f"; End of image")
    
    def _canvas_to_laser(self, canvas_point: Point, document_height: float, document_width: float) -> Point:
        """
        Transform canvas coordinates to laser coordinates.
        
        Canvas coordinate system: origin at top-left, X increases right, Y increases down
        Laser coordinate system: origin at bottom-left, X increases right, Y increases up
        
        The transformation:
        1. First, flip Y axis: laser_y = document_height - canvas_y
        2. Then, apply job origin offset (calculated in laser space) to shift the 
           selected point of the design to (0,0)
        
        With User Origin or Current Position mode:
        - G92 sets the current laser position as (0,0,0)
        - All coordinates are relative to this origin
        - The job_origin offset ensures the selected point of the design is at (0,0)
        """
        # Step 1: Transform canvas to laser coordinates (flip Y axis only)
        # Canvas X → Laser X (same direction)
        # Canvas Y → Laser Y (inverted: canvas down = laser up)
        laser_x_raw = canvas_point.x
        laser_y_raw = document_height - canvas_point.y
        
        # Step 2: Apply job origin offset (calculated in laser space)
        # This shifts coordinates so the selected job origin point is at (0,0)
        laser_x = laser_x_raw + self._job_origin_offset_x
        laser_y = laser_y_raw + self._job_origin_offset_y
        
        return Point(laser_x, laser_y)
    
    def _generate_fill_pattern(self, closed_path: List[Point], settings: LaserSettings) -> List[List[Point]]:
        """
        Generate fill pattern lines for a closed path.
        
        Args:
            closed_path: Closed path (polygon) to fill
            settings: Laser settings with fill parameters
        
        Returns:
            List of line segments for filling
        """
        if len(closed_path) < 3:
            return []
        
        # Get bounding box
        min_x = min(p.x for p in closed_path)
        max_x = max(p.x for p in closed_path)
        min_y = min(p.y for p in closed_path)
        max_y = max(p.y for p in closed_path)
        
        fill_lines = []
        pattern = settings.fill_pattern
        spacing = settings.line_interval
        angle = math.radians(settings.fill_angle)
        
        if pattern == "horizontal":
            fill_lines = self._generate_horizontal_fill(closed_path, min_y, max_y, spacing)
        elif pattern == "vertical":
            fill_lines = self._generate_vertical_fill(closed_path, min_x, max_x, spacing)
        elif pattern == "crosshatch":
            # Generate both horizontal and vertical
            h_lines = self._generate_horizontal_fill(closed_path, min_y, max_y, spacing)
            v_lines = self._generate_vertical_fill(closed_path, min_x, max_x, spacing)
            fill_lines = h_lines + v_lines
        elif pattern == "diagonal":
            fill_lines = self._generate_diagonal_fill(closed_path, min_x, max_x, min_y, max_y, spacing, angle)
        else:
            # Default to horizontal
            fill_lines = self._generate_horizontal_fill(closed_path, min_y, max_y, spacing)
        
        return fill_lines
    
    def _generate_horizontal_fill(self, path: List[Point], min_y: float, max_y: float, spacing: float) -> List[List[Point]]:
        """Generate horizontal fill lines."""
        fill_lines = []
        y = min_y
        line_num = 0
        
        while y <= max_y:
            intersections = self._find_line_intersections(path, y, horizontal=True)
            intersections.sort()
            
            # Pair up intersections (in-out pattern)
            for i in range(0, len(intersections) - 1, 2):
                if i + 1 < len(intersections):
                    x1 = intersections[i]
                    x2 = intersections[i + 1]
                    
                    # Alternate direction for efficiency
                    if line_num % 2 == 1:
                        fill_lines.append([Point(x2, y), Point(x1, y)])
                    else:
                        fill_lines.append([Point(x1, y), Point(x2, y)])
            
            y += spacing
            line_num += 1
        
        return fill_lines
    
    def _generate_vertical_fill(self, path: List[Point], min_x: float, max_x: float, spacing: float) -> List[List[Point]]:
        """Generate vertical fill lines."""
        fill_lines = []
        x = min_x
        line_num = 0
        
        while x <= max_x:
            intersections = self._find_line_intersections(path, x, horizontal=False)
            intersections.sort()
            
            # Pair up intersections (in-out pattern)
            for i in range(0, len(intersections) - 1, 2):
                if i + 1 < len(intersections):
                    y1 = intersections[i]
                    y2 = intersections[i + 1]
                    
                    # Alternate direction for efficiency
                    if line_num % 2 == 1:
                        fill_lines.append([Point(x, y2), Point(x, y1)])
                    else:
                        fill_lines.append([Point(x, y1), Point(x, y2)])
            
            x += spacing
            line_num += 1
        
        return fill_lines
    
    def _generate_diagonal_fill(self, path: List[Point], min_x: float, max_x: float, 
                                 min_y: float, max_y: float, spacing: float, angle: float) -> List[List[Point]]:
        """Generate diagonal fill lines."""
        # For diagonal, we'll use a simplified approach
        # Rotate the bounding box and use horizontal scanlines
        fill_lines = []
        
        # Calculate rotated bounding box
        center = Point((min_x + max_x) / 2, (min_y + max_y) / 2)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # For now, use horizontal lines with spacing adjusted for angle
        # A more sophisticated implementation would rotate the scanline
        diag_spacing = spacing / abs(cos_a) if abs(cos_a) > 0.001 else spacing / abs(sin_a) if abs(sin_a) > 0.001 else spacing
        
        y = min_y
        while y <= max_y:
            # Use horizontal scanlines (simplified diagonal)
            intersections = self._find_line_intersections(path, y, horizontal=True)
            intersections.sort()
            
            for i in range(0, len(intersections) - 1, 2):
                if i + 1 < len(intersections):
                    x1 = intersections[i]
                    x2 = intersections[i + 1]
                    # For diagonal, rotate the line endpoints around center
                    p1 = Point(x1, y).rotate(angle, center)
                    p2 = Point(x2, y).rotate(angle, center)
                    fill_lines.append([p1, p2])
            
            y += diag_spacing
        
        return fill_lines
    
    def _find_line_intersections(self, path: List[Point], value: float, horizontal: bool = True) -> List[float]:
        """
        Find intersections of a scanline with a closed path.
        
        Args:
            path: Closed path
            value: Y coordinate (if horizontal) or X coordinate (if vertical)
            horizontal: True for horizontal scanline, False for vertical
        
        Returns:
            List of intersection coordinates (X if horizontal, Y if vertical)
        """
        intersections = []
        
        # Close the path if needed
        closed_path = list(path)
        if len(closed_path) > 0:
            if (abs(closed_path[0].x - closed_path[-1].x) > 0.01 or 
                abs(closed_path[0].y - closed_path[-1].y) > 0.01):
                closed_path.append(closed_path[0])
        
        # Check each edge
        for i in range(len(closed_path) - 1):
            p1 = closed_path[i]
            p2 = closed_path[i + 1]
            
            if horizontal:
                # Check if edge crosses this Y
                if (p1.y <= value <= p2.y) or (p2.y <= value <= p1.y):
                    if abs(p1.y - p2.y) > 0.001:  # Avoid division by zero
                        t = (value - p1.y) / (p2.y - p1.y)
                        x = p1.x + t * (p2.x - p1.x)
                        intersections.append(x)
            else:
                # Check if edge crosses this X
                if (p1.x <= value <= p2.x) or (p2.x <= value <= p1.x):
                    if abs(p1.x - p2.x) > 0.001:  # Avoid division by zero
                        t = (value - p1.x) / (p2.x - p1.x)
                        y = p1.y + t * (p2.y - p1.y)
                        intersections.append(y)
        
        return intersections
    
    def _cut_path(self, path: List[Point], settings: LaserSettings):
        """Generate G-code for a single path."""
        if not path or len(path) < 2:
            return
        
        # Calculate power value - use rounding for better accuracy
        power_percent = max(0.0, min(100.0, settings.power))  # Clamp to 0-100
        power = int(round((power_percent / 100.0) * self.settings.max_power))
        power = max(0, min(self.settings.max_power, power))  # Clamp to valid range
        speed = settings.speed * 60  # Convert mm/s to mm/min
        
        # Transform canvas coordinates to laser coordinates
        document_height = getattr(self, '_current_document_height', 400.0)  # Default fallback
        document_width = getattr(self, '_current_document_width', 400.0)  # Default fallback
        
        # Move to start point (laser off)
        start = path[0]
        laser_start = self._canvas_to_laser(start, document_height, document_width)
        if laser_start.x != self._current_x or laser_start.y != self._current_y:
            self._rapid_move(laser_start.x, laser_start.y)
        
        # Turn on laser and cut
        self._laser_on_with_power(power)
        self._set_speed(speed)
        
        # Cut along path (transform coordinates)
        for point in path[1:]:
            laser_point = self._canvas_to_laser(point, document_height, document_width)
            self._linear_move(laser_point.x, laser_point.y)
        
        # Multiple passes
        if settings.passes > 1:
            for pass_num in range(1, settings.passes):
                self._emit(f"; Pass {pass_num + 1}")
                # Reverse direction for alternating passes
                for point in reversed(path[:-1]):
                    laser_point = self._canvas_to_laser(point, document_height, document_width)
                    self._linear_move(laser_point.x, laser_point.y)
                for point in path[1:]:
                    laser_point = self._canvas_to_laser(point, document_height, document_width)
                    self._linear_move(laser_point.x, laser_point.y)
        
        # Laser off after path
        self._laser_off()
    
    def _emit(self, line: str):
        """Add a line to the output."""
        self._gcode_lines.append(line)
    
    def _rapid_move(self, x: float, y: float):
        """Generate rapid move (G0)."""
        if x == self._current_x and y == self._current_y:
            return
        
        # In relative mode, we don't validate against absolute machine limits
        # because coordinates are relative to current position
        if not self._use_relative_mode:
            # Validate coordinates against machine limits (absolute mode only)
            is_valid, error_msg = self.settings.validate_coordinate(x, y, 0.0)
            if not is_valid:
                self._emit(f"; WARNING: {error_msg}")
                self._emit(f"; Skipping move to X{x:.3f} Y{y:.3f} (outside work area)")
                return
        
        if self._use_relative_mode:
            # Output delta from current position
            dx = x - self._current_x
            dy = y - self._current_y
            cmd = "G0"
            if abs(dx) > 0.0001:
                cmd += f" X{dx:.3f}"
            if abs(dy) > 0.0001:
                cmd += f" Y{dy:.3f}"
        else:
            # Output absolute coordinates
            cmd = "G0"
            if x != self._current_x:
                cmd += f" X{x:.3f}"
            if y != self._current_y:
                cmd += f" Y{y:.3f}"
        
        self._emit(cmd)
        self._current_x = x
        self._current_y = y
    
    def _linear_move(self, x: float, y: float):
        """Generate linear move (G1)."""
        if x == self._current_x and y == self._current_y:
            return
        
        # In relative mode, we don't validate against absolute machine limits
        if not self._use_relative_mode:
            # Validate coordinates against machine limits (absolute mode only)
            is_valid, error_msg = self.settings.validate_coordinate(x, y, 0.0)
            if not is_valid:
                self._emit(f"; WARNING: {error_msg}")
                self._emit(f"; Skipping move to X{x:.3f} Y{y:.3f} (outside work area)")
                return
        
        if self._use_relative_mode:
            # Output delta from current position
            dx = x - self._current_x
            dy = y - self._current_y
            cmd = "G1"
            if abs(dx) > 0.0001:
                cmd += f" X{dx:.3f}"
            if abs(dy) > 0.0001:
                cmd += f" Y{dy:.3f}"
        else:
            # Output absolute coordinates
            cmd = "G1"
            if x != self._current_x:
                cmd += f" X{x:.3f}"
            if y != self._current_y:
                cmd += f" Y{y:.3f}"
        
        # Include S value in G1 commands to ensure power is maintained
        # This is especially important for M4 (dynamic) mode, but doesn't hurt for M3
        if self._laser_on and self._current_power > 0:
            cmd += f" S{self._current_power}"
        
        self._emit(cmd)
        self._current_x = x
        self._current_y = y
    
    def _laser_on_with_power(self, power: int):
        """Turn laser on with specified power."""
        mode = self.settings.laser_mode.value
        if not self._laser_on or power != self._current_power:
            self._emit(f"{mode} S{power}")
            self._laser_on = True
            self._current_power = power
    
    def _laser_off(self):
        """Turn laser off."""
        if self._laser_on:
            self._emit("M5")
            self._laser_on = False
            self._current_power = 0
    
    def _set_speed(self, speed: float):
        """Set feed rate."""
        if speed != self._current_speed:
            self._emit(f"G1 F{speed:.0f}")
            self._current_speed = speed
    
    def generate_frame(self, document: Document) -> tuple[str, list[str]]:
        """
        Generate G-code to frame (outline) the design without enabling laser.
        
        This traces only the outer perimeter (bounding box) of all visible shapes
        using G0 rapid moves only. No laser commands (M3/M4/M5) are included.
        
        Returns:
            (gcode_string, warnings_list)
        """
        self._reset_state()
        self._gcode_lines = []
        warnings = []
        
        # Store document dimensions for coordinate transformation
        self._current_document_height = document.height
        self._current_document_width = document.width
        
        # Calculate job origin offset (so frame matches where job will engrave)
        self._job_origin_offset_x, self._job_origin_offset_y = self._calculate_job_origin_offset(document)
        
        # Calculate the bounding box of all visible shapes (in canvas coordinates)
        design_bounds = document.get_design_bounds()
        
        if not design_bounds:
            warnings.append("No visible shapes found to frame")
            return '\n'.join(self._gcode_lines), warnings
        
        # Transform bounding box corners to laser coordinates
        bottom_left_canvas = Point(design_bounds.min_x, design_bounds.max_y)  # Canvas bottom-left
        bottom_right_canvas = Point(design_bounds.max_x, design_bounds.max_y)  # Canvas bottom-right
        top_left_canvas = Point(design_bounds.min_x, design_bounds.min_y)  # Canvas top-left
        top_right_canvas = Point(design_bounds.max_x, design_bounds.min_y)  # Canvas top-right
        
        bottom_left_laser = self._canvas_to_laser(bottom_left_canvas, document.height, document.width)
        bottom_right_laser = self._canvas_to_laser(bottom_right_canvas, document.height, document.width)
        top_left_laser = self._canvas_to_laser(top_left_canvas, document.height, document.width)
        top_right_laser = self._canvas_to_laser(top_right_canvas, document.height, document.width)
        
        # Check design bounds against machine limits (using laser coordinates)
        laser_width = max(bottom_right_laser.x - bottom_left_laser.x, top_right_laser.x - top_left_laser.x)
        laser_height = max(top_left_laser.y - bottom_left_laser.y, top_right_laser.y - bottom_right_laser.y)
        if laser_width > self.settings.work_area_x:
            warnings.append(f"Design width ({laser_width:.2f}mm) exceeds machine X limit ({self.settings.work_area_x:.2f}mm)")
        if laser_height > self.settings.work_area_y:
            warnings.append(f"Design height ({laser_height:.2f}mm) exceeds machine Y limit ({self.settings.work_area_y:.2f}mm)")
        
        # Header (no laser commands)
        self._emit("; LaserBurn Frame G-Code")
        self._emit(f"; Document: {document.name}")
        self._emit(f"; Design bounds (laser coords): {laser_width:.2f}mm x {laser_height:.2f}mm")
        self._emit(f"; Position: X{bottom_left_laser.x:.2f} Y{bottom_left_laser.y:.2f}")
        self._emit(f"; Start From: {self.settings.start_from.value}")
        self._emit(f"; Job Origin: {self.settings.job_origin.value}")
        self._emit("; Frame mode - laser will NOT be enabled")
        self._emit("")
        
        # Standard G-code setup
        self._emit("G00 G17 G40 G21 G54")
        
        # For User Origin and Current Position, use RELATIVE mode (G91)
        # This matches how the main generate() works
        if self.settings.start_from == StartFrom.CURRENT_POSITION:
            self._emit("G91 ; Relative positioning (current position/user origin mode)")
            self._use_relative_mode = True
        else:
            # Home mode uses absolute coordinates
            if self.settings.absolute_coords:
                self._emit("G90 ; Absolute positioning")
            else:
                self._emit("G91 ; Relative positioning")
            self._use_relative_mode = not self.settings.absolute_coords
            
            # Home if requested
            if self.settings.home_on_start:
                self._emit("$H ; Home machine")
        
        # Set rapid speed
        self._emit(f"G0 F{self.settings.rapid_speed} ; Set rapid speed")
        self._emit("")
        
        # Frame the bounding box rectangle (4 corners in laser coordinates)
        # Start at bottom-left (in laser coords)
        self._rapid_move(bottom_left_laser.x, bottom_left_laser.y)
        # Move to bottom-right
        self._rapid_move(bottom_right_laser.x, bottom_right_laser.y)
        # Move to top-right
        self._rapid_move(top_right_laser.x, top_right_laser.y)
        # Move to top-left
        self._rapid_move(top_left_laser.x, top_left_laser.y)
        # Close the rectangle by returning to start
        self._rapid_move(bottom_left_laser.x, bottom_left_laser.y)
        
        # Return to origin if requested
        if self.settings.return_to_origin:
            self._emit("")
            self._emit("; Return to origin")
            self._rapid_move(0, 0)
        
        self._emit("")
        self._emit("; End of frame")
        
        return '\n'.join(self._gcode_lines), warnings
    
    def save_to_file(self, gcode: str, filepath: str):
        """Save G-code to a file."""
        with open(filepath, 'w') as f:
            f.write(gcode)

