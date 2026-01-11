# LaserBurn Development Guide - Part 2
## G-Code Generation, Laser Control, and Image Processing

---

## 7. Vector Graphics Engine

### 7.1 Boolean Operations with Clipper2

Boolean operations (union, difference, intersection) are essential for professional vector editing.

```python
# src/core/boolean_ops.py

"""
Boolean Operations using pyclipper (Clipper library).

Provides union, difference, intersection, and XOR operations
on polygons for shape manipulation.
"""

import pyclipper
from typing import List
from .shapes import Point, Path


# Clipper uses integer coordinates, so we scale floats
CLIPPER_SCALE = 1000000


def _to_clipper_path(points: List[Point]) -> List[tuple]:
    """Convert our points to Clipper format (scaled integers)."""
    return [(int(p.x * CLIPPER_SCALE), int(p.y * CLIPPER_SCALE)) 
            for p in points]


def _from_clipper_path(clipper_path: List[tuple]) -> List[Point]:
    """Convert Clipper path back to our points."""
    return [Point(p[0] / CLIPPER_SCALE, p[1] / CLIPPER_SCALE) 
            for p in clipper_path]


def boolean_union(paths_a: List[List[Point]], 
                  paths_b: List[List[Point]]) -> List[List[Point]]:
    """
    Compute union of two sets of paths.
    
    Args:
        paths_a: First set of closed paths
        paths_b: Second set of closed paths
    
    Returns:
        List of paths representing the union
    """
    pc = pyclipper.Pyclipper()
    
    for path in paths_a:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_SUBJECT, True)
    for path in paths_b:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_CLIP, True)
    
    solution = pc.Execute(pyclipper.CT_UNION, 
                          pyclipper.PFT_NONZERO, 
                          pyclipper.PFT_NONZERO)
    
    return [_from_clipper_path(path) for path in solution]


def boolean_difference(paths_a: List[List[Point]], 
                       paths_b: List[List[Point]]) -> List[List[Point]]:
    """
    Compute difference (A - B) of two sets of paths.
    
    Args:
        paths_a: Subject paths (shapes to cut from)
        paths_b: Clip paths (shapes to remove)
    
    Returns:
        List of paths representing A minus B
    """
    pc = pyclipper.Pyclipper()
    
    for path in paths_a:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_SUBJECT, True)
    for path in paths_b:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_CLIP, True)
    
    solution = pc.Execute(pyclipper.CT_DIFFERENCE,
                          pyclipper.PFT_NONZERO,
                          pyclipper.PFT_NONZERO)
    
    return [_from_clipper_path(path) for path in solution]


def boolean_intersection(paths_a: List[List[Point]], 
                         paths_b: List[List[Point]]) -> List[List[Point]]:
    """
    Compute intersection of two sets of paths.
    
    Args:
        paths_a: First set of closed paths
        paths_b: Second set of closed paths
    
    Returns:
        List of paths representing the intersection
    """
    pc = pyclipper.Pyclipper()
    
    for path in paths_a:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_SUBJECT, True)
    for path in paths_b:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_CLIP, True)
    
    solution = pc.Execute(pyclipper.CT_INTERSECTION,
                          pyclipper.PFT_NONZERO,
                          pyclipper.PFT_NONZERO)
    
    return [_from_clipper_path(path) for path in solution]


def boolean_xor(paths_a: List[List[Point]], 
                paths_b: List[List[Point]]) -> List[List[Point]]:
    """
    Compute XOR (exclusive or) of two sets of paths.
    
    Args:
        paths_a: First set of closed paths
        paths_b: Second set of closed paths
    
    Returns:
        List of paths representing the XOR
    """
    pc = pyclipper.Pyclipper()
    
    for path in paths_a:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_SUBJECT, True)
    for path in paths_b:
        pc.AddPath(_to_clipper_path(path), pyclipper.PT_CLIP, True)
    
    solution = pc.Execute(pyclipper.CT_XOR,
                          pyclipper.PFT_NONZERO,
                          pyclipper.PFT_NONZERO)
    
    return [_from_clipper_path(path) for path in solution]


def offset_paths(paths: List[List[Point]], 
                 offset: float,
                 join_type: str = 'round',
                 miter_limit: float = 2.0) -> List[List[Point]]:
    """
    Offset (inflate/deflate) paths by a distance.
    
    Args:
        paths: List of closed paths to offset
        offset: Positive = outward, Negative = inward (in mm)
        join_type: 'round', 'square', or 'miter'
        miter_limit: Limit for miter joins
    
    Returns:
        List of offset paths
    """
    join_types = {
        'round': pyclipper.JT_ROUND,
        'square': pyclipper.JT_SQUARE,
        'miter': pyclipper.JT_MITER
    }
    
    pco = pyclipper.PyclipperOffset()
    pco.MiterLimit = miter_limit
    
    for path in paths:
        pco.AddPath(_to_clipper_path(path), 
                    join_types.get(join_type, pyclipper.JT_ROUND),
                    pyclipper.ET_CLOSEDPOLYGON)
    
    solution = pco.Execute(offset * CLIPPER_SCALE)
    
    return [_from_clipper_path(path) for path in solution]


def simplify_paths(paths: List[List[Point]], 
                   tolerance: float = 0.1) -> List[List[Point]]:
    """
    Simplify paths by removing redundant points.
    
    Uses Douglas-Peucker algorithm.
    
    Args:
        paths: List of paths to simplify
        tolerance: Maximum deviation from original path (in mm)
    
    Returns:
        List of simplified paths
    """
    simplified = []
    
    for path in paths:
        clipper_path = _to_clipper_path(path)
        simple_path = pyclipper.SimplifyPolygon(clipper_path)
        
        for sp in simple_path:
            simplified.append(_from_clipper_path(sp))
    
    return simplified
```

### 7.2 Path Optimization

Optimize cut order to minimize travel time (Traveling Salesman Problem approximation).

```python
# src/core/path_optimizer.py

"""
Path Optimization for Laser Cutting

Minimizes non-cutting travel distance by reordering paths
and optimizing start points.
"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .shapes import Point


@dataclass
class OptimizedPath:
    """A path with optimized direction and order."""
    points: List[Point]
    reversed: bool = False
    start_index: int = 0


def optimize_paths(paths: List[List[Point]], 
                   start_point: Point = None) -> List[List[Point]]:
    """
    Optimize path order to minimize travel distance.
    
    Uses nearest neighbor heuristic for TSP approximation.
    Also optimizes each path's start point and direction.
    
    Args:
        paths: List of paths to optimize
        start_point: Starting position (default: origin)
    
    Returns:
        Reordered and optimized paths
    """
    if not paths:
        return []
    
    if start_point is None:
        start_point = Point(0, 0)
    
    # Convert to optimized path objects
    opt_paths = [OptimizedPath(points=p.copy()) for p in paths]
    
    # Track which paths have been visited
    remaining = set(range(len(opt_paths)))
    ordered = []
    current_pos = start_point
    
    while remaining:
        # Find nearest path endpoint
        best_idx = None
        best_dist = float('inf')
        best_reversed = False
        
        for idx in remaining:
            path = opt_paths[idx]
            if not path.points:
                remaining.discard(idx)
                continue
            
            # Check distance to start and end of path
            start = path.points[0]
            end = path.points[-1]
            
            dist_to_start = current_pos.distance_to(start)
            dist_to_end = current_pos.distance_to(end)
            
            if dist_to_start < best_dist:
                best_dist = dist_to_start
                best_idx = idx
                best_reversed = False
            
            if dist_to_end < best_dist:
                best_dist = dist_to_end
                best_idx = idx
                best_reversed = True
        
        if best_idx is not None:
            path = opt_paths[best_idx]
            
            if best_reversed:
                path.points.reverse()
                path.reversed = True
            
            ordered.append(path.points)
            remaining.discard(best_idx)
            
            # Update current position
            if path.points:
                current_pos = path.points[-1]
    
    return ordered


def optimize_closed_path_start(path: List[Point], 
                               entry_point: Point) -> List[Point]:
    """
    Optimize the starting point of a closed path.
    
    For closed paths, we can start at any point. This finds
    the point closest to the entry_point to minimize travel.
    
    Args:
        path: Closed path (first point == last point expected)
        entry_point: The position we're coming from
    
    Returns:
        Rotated path starting at optimal point
    """
    if len(path) < 3:
        return path
    
    # Remove closing point if present
    is_closed = (path[0].x == path[-1].x and path[0].y == path[-1].y)
    working_path = path[:-1] if is_closed else path
    
    # Find closest point
    best_idx = 0
    best_dist = float('inf')
    
    for i, point in enumerate(working_path):
        dist = entry_point.distance_to(point)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    
    # Rotate path to start at best_idx
    rotated = working_path[best_idx:] + working_path[:best_idx]
    
    # Re-close if needed
    if is_closed:
        rotated.append(rotated[0])
    
    return rotated


def calculate_total_distance(paths: List[List[Point]], 
                            start_point: Point = None) -> Tuple[float, float]:
    """
    Calculate total cutting and travel distances.
    
    Args:
        paths: Ordered list of paths
        start_point: Starting position
    
    Returns:
        Tuple of (cutting_distance, travel_distance)
    """
    if start_point is None:
        start_point = Point(0, 0)
    
    cutting_dist = 0.0
    travel_dist = 0.0
    current_pos = start_point
    
    for path in paths:
        if not path:
            continue
        
        # Travel to path start
        travel_dist += current_pos.distance_to(path[0])
        
        # Cut along path
        for i in range(1, len(path)):
            cutting_dist += path[i-1].distance_to(path[i])
        
        # Update position
        current_pos = path[-1]
    
    return cutting_dist, travel_dist


def estimate_job_time(paths: List[List[Point]],
                      cut_speed: float,
                      travel_speed: float,
                      start_point: Point = None) -> float:
    """
    Estimate total job time in seconds.
    
    Args:
        paths: Ordered list of paths
        cut_speed: Cutting speed in mm/s
        travel_speed: Rapid travel speed in mm/s
        start_point: Starting position
    
    Returns:
        Estimated time in seconds
    """
    cutting_dist, travel_dist = calculate_total_distance(paths, start_point)
    
    cut_time = cutting_dist / cut_speed if cut_speed > 0 else 0
    travel_time = travel_dist / travel_speed if travel_speed > 0 else 0
    
    return cut_time + travel_time
```

---

## 8. G-Code Generation

### 8.1 G-Code Fundamentals

G-code is the standard language for controlling CNC machines including laser cutters.

**Essential G-code Commands for Laser:**

| Command | Description | Example |
|---------|-------------|---------|
| `G0` | Rapid move (laser off) | `G0 X10 Y20` |
| `G1` | Linear move (laser on) | `G1 X30 Y40 F1000` |
| `G2` | Clockwise arc | `G2 X10 Y10 I5 J0` |
| `G3` | Counter-clockwise arc | `G3 X10 Y10 I5 J0` |
| `G20` | Set units to inches | `G20` |
| `G21` | Set units to mm | `G21` |
| `G90` | Absolute positioning | `G90` |
| `G91` | Relative positioning | `G91` |
| `M3` | Laser on (constant power) | `M3 S255` |
| `M4` | Laser on (dynamic power) | `M4 S255` |
| `M5` | Laser off | `M5` |
| `S` | Set laser power (0-255 or 0-1000) | `S128` |
| `F` | Set feed rate (speed) | `F1000` |

### 8.2 G-Code Generator Implementation

```python
# src/laser/gcode_generator.py

"""
G-Code Generator for LaserBurn

Converts vector paths to G-code for GRBL and compatible controllers.
Supports both line-by-line cutting and fill/engrave operations.
"""

from typing import List, Optional, TextIO
from dataclasses import dataclass
from enum import Enum
import math

from ..core.shapes import Point, Shape, LaserSettings
from ..core.document import Document
from ..core.layer import Layer
from .path_optimizer import optimize_paths


class LaserMode(Enum):
    """Laser control mode."""
    CONSTANT = "M3"  # Constant power mode
    DYNAMIC = "M4"   # Dynamic power (scales with speed)


@dataclass
class GCodeSettings:
    """Settings for G-code generation."""
    
    # Units and positioning
    use_mm: bool = True              # G21 vs G20
    absolute_coords: bool = True      # G90 vs G91
    
    # Laser settings
    max_power: int = 1000            # Max S value (255 for 8-bit, 1000 for GRBL 1.1+)
    laser_mode: LaserMode = LaserMode.DYNAMIC
    
    # Speed settings
    rapid_speed: float = 6000.0      # mm/min for G0 moves
    default_cut_speed: float = 1000.0  # mm/min for G1 moves
    
    # Machine settings
    origin: str = "bottom-left"      # Origin position
    home_on_start: bool = False      # Home machine at start
    return_to_origin: bool = True    # Return to origin at end
    
    # Safety
    laser_off_delay: float = 0.0     # Delay after M5 (ms)
    
    # Optimization
    optimize_paths: bool = True      # Reorder paths
    min_power: float = 0.0           # Min power for traversal


class GCodeGenerator:
    """
    Generate G-code from LaserBurn documents.
    
    Usage:
        generator = GCodeGenerator(settings)
        gcode = generator.generate(document)
        generator.save_to_file(gcode, "output.gcode")
    """
    
    def __init__(self, settings: GCodeSettings = None):
        self.settings = settings or GCodeSettings()
        self._gcode_lines: List[str] = []
        self._current_x: float = 0.0
        self._current_y: float = 0.0
        self._laser_on: bool = False
        self._current_power: int = 0
        self._current_speed: float = 0.0
    
    def generate(self, document: Document) -> str:
        """
        Generate G-code for an entire document.
        
        Args:
            document: The LaserBurn document to convert
        
        Returns:
            Complete G-code as a string
        """
        self._gcode_lines = []
        self._reset_state()
        
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
        
        return '\n'.join(self._gcode_lines)
    
    def generate_preview(self, shapes: List[Shape]) -> str:
        """
        Generate G-code preview for selected shapes.
        
        Useful for showing what will be cut without full document.
        """
        self._gcode_lines = []
        self._reset_state()
        
        paths = []
        settings = []
        
        for shape in shapes:
            shape_paths = shape.get_paths()
            for path in shape_paths:
                paths.append(path)
                settings.append(shape.laser_settings)
        
        if self.settings.optimize_paths:
            # Note: optimization would need to track settings
            paths = optimize_paths(paths)
        
        for i, path in enumerate(paths):
            laser_settings = settings[min(i, len(settings)-1)]
            self._cut_path(path, laser_settings)
        
        return '\n'.join(self._gcode_lines)
    
    def _reset_state(self):
        """Reset generator state."""
        self._current_x = 0.0
        self._current_y = 0.0
        self._laser_on = False
        self._current_power = 0
        self._current_speed = 0.0
    
    def _add_header(self, document: Document):
        """Add G-code header/preamble."""
        self._emit("; LaserBurn G-Code Output")
        self._emit(f"; Document: {document.name}")
        self._emit(f"; Size: {document.width}mm x {document.height}mm")
        self._emit("")
        
        # Units
        if self.settings.use_mm:
            self._emit("G21 ; Set units to mm")
        else:
            self._emit("G20 ; Set units to inches")
        
        # Positioning mode
        if self.settings.absolute_coords:
            self._emit("G90 ; Absolute positioning")
        else:
            self._emit("G91 ; Relative positioning")
        
        # Home if requested
        if self.settings.home_on_start:
            self._emit("$H ; Home machine")
        
        # Laser off to start
        self._emit("M5 ; Laser off")
        self._emit(f"G0 F{self.settings.rapid_speed} ; Set rapid speed")
        self._emit("")
    
    def _add_footer(self):
        """Add G-code footer/cleanup."""
        self._emit("")
        self._emit("; End of job")
        self._laser_off()
        
        if self.settings.return_to_origin:
            self._emit("G0 X0 Y0 ; Return to origin")
        
        self._emit("M5 ; Ensure laser off")
        self._emit("M2 ; End program")
    
    def _process_layer(self, layer: Layer):
        """Process all shapes in a layer."""
        self._emit(f"; Layer: {layer.name}")
        
        # Collect all paths from layer
        all_paths = []
        path_settings = []
        
        for shape in layer.shapes:
            if not shape.visible:
                continue
            
            paths = shape.get_paths()
            for path in paths:
                all_paths.append(path)
                # Use layer settings if enabled, else shape settings
                if layer.use_layer_settings:
                    path_settings.append(layer.laser_settings)
                else:
                    path_settings.append(shape.laser_settings)
        
        # Optimize path order
        if self.settings.optimize_paths and all_paths:
            start = Point(self._current_x, self._current_y)
            all_paths = optimize_paths(all_paths, start)
        
        # Cut each path
        for i, path in enumerate(all_paths):
            settings = path_settings[min(i, len(path_settings)-1)]
            self._cut_path(path, settings)
        
        self._emit("")
    
    def _cut_path(self, path: List[Point], settings: LaserSettings):
        """Generate G-code for a single path."""
        if not path or len(path) < 2:
            return
        
        # Calculate power value
        power = int((settings.power / 100.0) * self.settings.max_power)
        speed = settings.speed * 60  # Convert mm/s to mm/min
        
        # Move to start point (laser off)
        start = path[0]
        if start.x != self._current_x or start.y != self._current_y:
            self._rapid_move(start.x, start.y)
        
        # Turn on laser and cut
        self._laser_on_with_power(power)
        self._set_speed(speed)
        
        # Cut along path
        for point in path[1:]:
            self._linear_move(point.x, point.y)
        
        # Multiple passes
        if settings.passes > 1:
            for pass_num in range(1, settings.passes):
                self._emit(f"; Pass {pass_num + 1}")
                # Reverse direction for alternating passes (optional)
                for point in reversed(path[:-1]):
                    self._linear_move(point.x, point.y)
                for point in path[1:]:
                    self._linear_move(point.x, point.y)
        
        # Laser off after path
        self._laser_off()
    
    def _emit(self, line: str):
        """Add a line to the output."""
        self._gcode_lines.append(line)
    
    def _rapid_move(self, x: float, y: float):
        """Generate rapid move (G0)."""
        if x == self._current_x and y == self._current_y:
            return
        
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
        
        cmd = "G1"
        if x != self._current_x:
            cmd += f" X{x:.3f}"
        if y != self._current_y:
            cmd += f" Y{y:.3f}"
        
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
    
    def save_to_file(self, gcode: str, filepath: str):
        """Save G-code to a file."""
        with open(filepath, 'w') as f:
            f.write(gcode)


class FillGenerator:
    """
    Generate fill patterns for engraving solid areas.
    
    Supports multiple fill patterns:
    - Horizontal lines
    - Vertical lines
    - Crosshatch
    - Diagonal
    """
    
    def __init__(self, line_spacing: float = 0.1):
        """
        Args:
            line_spacing: Distance between fill lines in mm
        """
        self.line_spacing = line_spacing
    
    def generate_horizontal_fill(self, 
                                  paths: List[List[Point]],
                                  bidirectional: bool = True) -> List[List[Point]]:
        """
        Generate horizontal fill lines for closed paths.
        
        Args:
            paths: Closed paths defining the fill area
            bidirectional: Alternate direction for efficiency
        
        Returns:
            List of line segments for filling
        """
        if not paths:
            return []
        
        # Find bounding box
        all_points = [p for path in paths for p in path]
        min_y = min(p.y for p in all_points)
        max_y = max(p.y for p in all_points)
        min_x = min(p.x for p in all_points)
        max_x = max(p.x for p in all_points)
        
        fill_lines = []
        y = min_y
        line_num = 0
        
        while y <= max_y:
            # Find intersections with all paths at this Y level
            intersections = []
            
            for path in paths:
                for i in range(len(path) - 1):
                    p1, p2 = path[i], path[i + 1]
                    
                    # Check if line crosses this Y
                    if (p1.y <= y <= p2.y) or (p2.y <= y <= p1.y):
                        if p1.y != p2.y:
                            # Calculate X intersection
                            t = (y - p1.y) / (p2.y - p1.y)
                            x = p1.x + t * (p2.x - p1.x)
                            intersections.append(x)
            
            # Sort intersections and create line segments
            intersections.sort()
            
            # Pair up intersections (in-out pattern)
            for i in range(0, len(intersections) - 1, 2):
                x1 = intersections[i]
                x2 = intersections[i + 1]
                
                # Alternate direction for bidirectional fill
                if bidirectional and line_num % 2 == 1:
                    fill_lines.append([Point(x2, y), Point(x1, y)])
                else:
                    fill_lines.append([Point(x1, y), Point(x2, y)])
            
            y += self.line_spacing
            line_num += 1
        
        return fill_lines
    
    def generate_crosshatch_fill(self,
                                  paths: List[List[Point]]) -> List[List[Point]]:
        """Generate crosshatch (horizontal + vertical) fill."""
        horizontal = self.generate_horizontal_fill(paths)
        
        # Rotate paths 90 degrees, generate fill, rotate back
        rotated_paths = []
        for path in paths:
            rotated_paths.append([Point(-p.y, p.x) for p in path])
        
        vertical_rotated = self.generate_horizontal_fill(rotated_paths)
        
        # Rotate back
        vertical = []
        for line in vertical_rotated:
            vertical.append([Point(p.y, -p.x) for p in line])
        
        return horizontal + vertical
```

---

## 9. Laser Controller Communication

### 9.1 Serial Communication Base Class

```python
# src/laser/controller.py

"""
Base classes for laser controller communication.

Provides abstract interface that all controller implementations
must follow, enabling support for multiple controller types.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, List
import serial
import serial.tools.list_ports
import threading
import queue
import time


class ConnectionState(Enum):
    """Controller connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    BUSY = "busy"
    ERROR = "error"
    ALARM = "alarm"


class JobState(Enum):
    """Job execution states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class ControllerStatus:
    """Current status of the laser controller."""
    state: ConnectionState = ConnectionState.DISCONNECTED
    job_state: JobState = JobState.IDLE
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    progress: float = 0.0  # 0-100%
    buffer_space: int = 0
    error_message: str = ""
    is_homed: bool = False


class LaserController(ABC):
    """
    Abstract base class for laser controllers.
    
    Implementations must provide:
    - connect/disconnect
    - send_command
    - home
    - jog
    - start_job/pause_job/stop_job
    - get_status
    """
    
    def __init__(self):
        self.status = ControllerStatus()
        self._status_callbacks: List[Callable[[ControllerStatus], None]] = []
        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._command_queue: queue.Queue = queue.Queue()
        self._running = False
    
    @abstractmethod
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """
        Connect to the controller.
        
        Args:
            port: Serial port (e.g., 'COM3', '/dev/ttyUSB0')
            baudrate: Communication speed
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the controller."""
        pass
    
    @abstractmethod
    def send_command(self, command: str, wait_for_ok: bool = True) -> str:
        """
        Send a command to the controller.
        
        Args:
            command: Command string (e.g., 'G0 X10')
            wait_for_ok: Wait for acknowledgment
        
        Returns:
            Response from controller
        """
        pass
    
    @abstractmethod
    def home(self, axes: str = "XY") -> bool:
        """
        Home the specified axes.
        
        Args:
            axes: Axes to home (e.g., 'XY', 'Z', 'XYZ')
        
        Returns:
            True if homing started successfully
        """
        pass
    
    @abstractmethod
    def jog(self, x: float = 0, y: float = 0, z: float = 0,
            speed: float = 1000, relative: bool = True) -> bool:
        """
        Jog the laser head.
        
        Args:
            x, y, z: Movement distances/positions
            speed: Movement speed in mm/min
            relative: True for relative movement
        
        Returns:
            True if jog command sent successfully
        """
        pass
    
    @abstractmethod
    def start_job(self, gcode: str) -> bool:
        """
        Start executing a G-code job.
        
        Args:
            gcode: Complete G-code program
        
        Returns:
            True if job started successfully
        """
        pass
    
    @abstractmethod
    def pause_job(self) -> bool:
        """Pause the current job."""
        pass
    
    @abstractmethod
    def resume_job(self) -> bool:
        """Resume a paused job."""
        pass
    
    @abstractmethod
    def stop_job(self) -> bool:
        """Stop and cancel the current job."""
        pass
    
    @abstractmethod
    def get_status(self) -> ControllerStatus:
        """Get current controller status."""
        pass
    
    def add_status_callback(self, callback: Callable[[ControllerStatus], None]):
        """Register callback for status updates."""
        self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[ControllerStatus], None]):
        """Remove a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status(self):
        """Notify all callbacks of status change."""
        for callback in self._status_callbacks:
            try:
                callback(self.status)
            except Exception as e:
                print(f"Status callback error: {e}")
    
    @staticmethod
    def list_ports() -> List[dict]:
        """List available serial ports."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'port': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports
```

### 9.2 GRBL Controller Implementation

```python
# src/laser/grbl.py

"""
GRBL Controller Implementation

Supports GRBL 1.1 and compatible firmware (including laser-specific builds).
"""

import re
import time
import threading
from typing import Optional
from .controller import (
    LaserController, ControllerStatus, ConnectionState, JobState
)
import serial


class GRBLController(LaserController):
    """
    GRBL controller implementation.
    
    Supports:
    - GRBL 1.1+
    - GRBL-LPC
    - FluidNC (GRBL compatible mode)
    """
    
    # GRBL status parsing regex
    STATUS_REGEX = re.compile(
        r'<(\w+)\|MPos:(-?\d+\.?\d*),(-?\d+\.?\d*),(-?\d+\.?\d*)'
        r'(?:\|Bf:(\d+),(\d+))?'
        r'(?:\|FS:(\d+),(\d+))?'
    )
    
    # GRBL real-time commands (no newline needed)
    CMD_STATUS = b'?'
    CMD_SOFT_RESET = b'\x18'
    CMD_FEED_HOLD = b'!'
    CMD_CYCLE_START = b'~'
    
    def __init__(self):
        super().__init__()
        self._buffer_size = 128  # GRBL serial buffer size
        self._buffer_count = 0
        self._gcode_lines: list = []
        self._current_line: int = 0
        self._response_event = threading.Event()
        self._last_response = ""
    
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """Connect to GRBL controller."""
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1.0,
                write_timeout=1.0
            )
            
            self.status.state = ConnectionState.CONNECTING
            self._notify_status()
            
            # Wait for GRBL startup message
            time.sleep(2)
            
            # Clear any startup messages
            while self._serial.in_waiting:
                self._serial.readline()
            
            # Start reader thread
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop)
            self._reader_thread.daemon = True
            self._reader_thread.start()
            
            # Query status to confirm connection
            self._send_realtime(self.CMD_STATUS)
            time.sleep(0.1)
            
            self.status.state = ConnectionState.CONNECTED
            self._notify_status()
            
            return True
            
        except serial.SerialException as e:
            self.status.state = ConnectionState.ERROR
            self.status.error_message = str(e)
            self._notify_status()
            return False
    
    def disconnect(self):
        """Disconnect from GRBL controller."""
        self._running = False
        
        if self._reader_thread:
            self._reader_thread.join(timeout=2.0)
            self._reader_thread = None
        
        if self._serial and self._serial.is_open:
            self._serial.close()
        
        self._serial = None
        self.status.state = ConnectionState.DISCONNECTED
        self._notify_status()
    
    def send_command(self, command: str, wait_for_ok: bool = True) -> str:
        """Send a G-code command to GRBL."""
        if not self._serial or not self._serial.is_open:
            return "ERROR: Not connected"
        
        # Ensure command ends with newline
        if not command.endswith('\n'):
            command += '\n'
        
        self._response_event.clear()
        self._serial.write(command.encode())
        
        if wait_for_ok:
            # Wait for response (ok or error)
            self._response_event.wait(timeout=10.0)
            return self._last_response
        
        return "ok"
    
    def home(self, axes: str = "XY") -> bool:
        """Home the machine."""
        response = self.send_command("$H")
        return "ok" in response.lower()
    
    def jog(self, x: float = 0, y: float = 0, z: float = 0,
            speed: float = 1000, relative: bool = True) -> bool:
        """Jog the laser head."""
        # GRBL jog command format
        mode = "G91" if relative else "G90"
        cmd = f"$J={mode} "
        
        if x != 0:
            cmd += f"X{x:.3f} "
        if y != 0:
            cmd += f"Y{y:.3f} "
        if z != 0:
            cmd += f"Z{z:.3f} "
        
        cmd += f"F{speed:.0f}"
        
        response = self.send_command(cmd)
        return "ok" in response.lower()
    
    def start_job(self, gcode: str) -> bool:
        """Start executing G-code."""
        if self.status.job_state == JobState.RUNNING:
            return False
        
        # Parse G-code into lines
        self._gcode_lines = [
            line.strip() for line in gcode.split('\n')
            if line.strip() and not line.strip().startswith(';')
        ]
        self._current_line = 0
        self._buffer_count = 0
        
        self.status.job_state = JobState.RUNNING
        self.status.progress = 0.0
        self._notify_status()
        
        # Start sending in a separate thread
        sender_thread = threading.Thread(target=self._send_job)
        sender_thread.daemon = True
        sender_thread.start()
        
        return True
    
    def pause_job(self) -> bool:
        """Pause the current job (feed hold)."""
        if self.status.job_state != JobState.RUNNING:
            return False
        
        self._send_realtime(self.CMD_FEED_HOLD)
        self.status.job_state = JobState.PAUSED
        self._notify_status()
        return True
    
    def resume_job(self) -> bool:
        """Resume a paused job."""
        if self.status.job_state != JobState.PAUSED:
            return False
        
        self._send_realtime(self.CMD_CYCLE_START)
        self.status.job_state = JobState.RUNNING
        self._notify_status()
        return True
    
    def stop_job(self) -> bool:
        """Stop and cancel the current job."""
        # Soft reset
        self._send_realtime(self.CMD_SOFT_RESET)
        
        self._gcode_lines = []
        self._current_line = 0
        
        self.status.job_state = JobState.CANCELLED
        self._notify_status()
        
        # Wait for reset to complete
        time.sleep(0.5)
        
        self.status.job_state = JobState.IDLE
        self._notify_status()
        
        return True
    
    def get_status(self) -> ControllerStatus:
        """Query current status."""
        self._send_realtime(self.CMD_STATUS)
        time.sleep(0.1)  # Wait for status response
        return self.status
    
    def _send_realtime(self, cmd: bytes):
        """Send a real-time command (no newline)."""
        if self._serial and self._serial.is_open:
            self._serial.write(cmd)
    
    def _read_loop(self):
        """Background thread for reading serial responses."""
        while self._running and self._serial:
            try:
                if self._serial.in_waiting:
                    line = self._serial.readline().decode('utf-8', errors='ignore').strip()
                    self._process_response(line)
            except Exception as e:
                if self._running:
                    print(f"Read error: {e}")
            time.sleep(0.01)
    
    def _process_response(self, line: str):
        """Process a response line from GRBL."""
        if not line:
            return
        
        # Status report
        if line.startswith('<'):
            self._parse_status(line)
        
        # Command acknowledgment
        elif line == 'ok':
            self._buffer_count -= 1
            self._last_response = line
            self._response_event.set()
        
        # Error
        elif line.startswith('error:'):
            self._last_response = line
            self._response_event.set()
            self.status.error_message = line
            self._notify_status()
        
        # Alarm
        elif line.startswith('ALARM:'):
            self.status.state = ConnectionState.ALARM
            self.status.error_message = line
            self.status.job_state = JobState.ERROR
            self._notify_status()
        
        # Welcome/startup message
        elif 'Grbl' in line:
            self.status.state = ConnectionState.CONNECTED
            self._notify_status()
    
    def _parse_status(self, line: str):
        """Parse GRBL status report."""
        match = self.STATUS_REGEX.match(line)
        if match:
            state = match.group(1)
            self.status.position_x = float(match.group(2))
            self.status.position_y = float(match.group(3))
            self.status.position_z = float(match.group(4))
            
            if match.group(5):  # Buffer info
                self.status.buffer_space = int(match.group(5))
            
            # Map GRBL state to our state
            state_map = {
                'Idle': ConnectionState.CONNECTED,
                'Run': ConnectionState.BUSY,
                'Hold': ConnectionState.CONNECTED,
                'Jog': ConnectionState.BUSY,
                'Alarm': ConnectionState.ALARM,
                'Check': ConnectionState.CONNECTED,
                'Home': ConnectionState.BUSY,
            }
            
            if 'Home' in state:
                self.status.is_homed = True
            
            self.status.state = state_map.get(state, ConnectionState.CONNECTED)
            self._notify_status()
    
    def _send_job(self):
        """Send job G-code with flow control."""
        while (self._current_line < len(self._gcode_lines) and 
               self.status.job_state == JobState.RUNNING):
            
            # Check buffer space
            if self._buffer_count >= 5:  # Keep some buffer room
                time.sleep(0.01)
                continue
            
            line = self._gcode_lines[self._current_line]
            
            # Send line
            self._serial.write((line + '\n').encode())
            self._buffer_count += 1
            self._current_line += 1
            
            # Update progress
            self.status.progress = (self._current_line / len(self._gcode_lines)) * 100
            self._notify_status()
        
        # Wait for completion
        while self._buffer_count > 0 and self.status.job_state == JobState.RUNNING:
            time.sleep(0.1)
        
        if self.status.job_state == JobState.RUNNING:
            self.status.job_state = JobState.COMPLETED
            self.status.progress = 100.0
            self._notify_status()
```

---

## 10. Image Processing Pipeline

### 10.1 Dithering Algorithms

```python
# src/image/dithering.py

"""
Image Dithering Algorithms for Laser Engraving

Converts grayscale images to binary (black/white) patterns
suitable for laser engraving.
"""

import numpy as np
from enum import Enum
from typing import Tuple
from PIL import Image


class DitherMethod(Enum):
    """Available dithering methods."""
    THRESHOLD = "threshold"
    FLOYD_STEINBERG = "floyd_steinberg"
    JARVIS_JUDICE_NINKE = "jarvis"
    STUCKI = "stucki"
    ATKINSON = "atkinson"
    ORDERED_BAYER = "ordered_bayer"
    HALFTONE = "halftone"


def apply_dithering(image: Image.Image, 
                    method: DitherMethod = DitherMethod.FLOYD_STEINBERG,
                    threshold: int = 128) -> Image.Image:
    """
    Apply dithering to an image.
    
    Args:
        image: PIL Image (will be converted to grayscale)
        method: Dithering algorithm to use
        threshold: Threshold for simple threshold dithering
    
    Returns:
        Binary (1-bit) PIL Image
    """
    # Convert to grayscale if needed
    if image.mode != 'L':
        image = image.convert('L')
    
    # Convert to numpy array for processing
    img_array = np.array(image, dtype=np.float32)
    
    if method == DitherMethod.THRESHOLD:
        result = threshold_dither(img_array, threshold)
    elif method == DitherMethod.FLOYD_STEINBERG:
        result = floyd_steinberg_dither(img_array)
    elif method == DitherMethod.JARVIS_JUDICE_NINKE:
        result = jarvis_dither(img_array)
    elif method == DitherMethod.STUCKI:
        result = stucki_dither(img_array)
    elif method == DitherMethod.ATKINSON:
        result = atkinson_dither(img_array)
    elif method == DitherMethod.ORDERED_BAYER:
        result = bayer_dither(img_array)
    elif method == DitherMethod.HALFTONE:
        result = halftone_dither(img_array)
    else:
        result = threshold_dither(img_array, threshold)
    
    # Convert back to PIL Image
    return Image.fromarray(result.astype(np.uint8) * 255, mode='L').convert('1')


def threshold_dither(img: np.ndarray, threshold: int = 128) -> np.ndarray:
    """Simple threshold dithering."""
    return (img >= threshold).astype(np.uint8)


def floyd_steinberg_dither(img: np.ndarray) -> np.ndarray:
    """
    Floyd-Steinberg error diffusion dithering.
    
    Error distribution pattern:
        * 7/16
    3/16 5/16 1/16
    
    This is the most common dithering algorithm, producing
    good quality with moderate processing time.
    """
    h, w = img.shape
    result = np.zeros_like(img)
    
    for y in range(h):
        for x in range(w):
            old_pixel = img[y, x]
            new_pixel = 255 if old_pixel >= 128 else 0
            result[y, x] = new_pixel
            error = old_pixel - new_pixel
            
            # Distribute error to neighbors
            if x + 1 < w:
                img[y, x + 1] += error * 7 / 16
            if y + 1 < h:
                if x > 0:
                    img[y + 1, x - 1] += error * 3 / 16
                img[y + 1, x] += error * 5 / 16
                if x + 1 < w:
                    img[y + 1, x + 1] += error * 1 / 16
    
    return (result > 0).astype(np.uint8)


def jarvis_dither(img: np.ndarray) -> np.ndarray:
    """
    Jarvis-Judice-Ninke error diffusion dithering.
    
    Error distribution pattern:
            * 7/48 5/48
    3/48 5/48 7/48 5/48 3/48
    1/48 3/48 5/48 3/48 1/48
    
    Produces smoother results than Floyd-Steinberg but slower.
    """
    h, w = img.shape
    result = np.zeros_like(img)
    
    kernel = [
        (0, 1, 7), (0, 2, 5),
        (1, -2, 3), (1, -1, 5), (1, 0, 7), (1, 1, 5), (1, 2, 3),
        (2, -2, 1), (2, -1, 3), (2, 0, 5), (2, 1, 3), (2, 2, 1)
    ]
    divisor = 48
    
    for y in range(h):
        for x in range(w):
            old_pixel = img[y, x]
            new_pixel = 255 if old_pixel >= 128 else 0
            result[y, x] = new_pixel
            error = old_pixel - new_pixel
            
            for dy, dx, weight in kernel:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += error * weight / divisor
    
    return (result > 0).astype(np.uint8)


def stucki_dither(img: np.ndarray) -> np.ndarray:
    """
    Stucki error diffusion dithering.
    
    Similar to Jarvis but with different weights.
    Good balance of quality and performance.
    """
    h, w = img.shape
    result = np.zeros_like(img)
    
    kernel = [
        (0, 1, 8), (0, 2, 4),
        (1, -2, 2), (1, -1, 4), (1, 0, 8), (1, 1, 4), (1, 2, 2),
        (2, -2, 1), (2, -1, 2), (2, 0, 4), (2, 1, 2), (2, 2, 1)
    ]
    divisor = 42
    
    for y in range(h):
        for x in range(w):
            old_pixel = img[y, x]
            new_pixel = 255 if old_pixel >= 128 else 0
            result[y, x] = new_pixel
            error = old_pixel - new_pixel
            
            for dy, dx, weight in kernel:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += error * weight / divisor
    
    return (result > 0).astype(np.uint8)


def atkinson_dither(img: np.ndarray) -> np.ndarray:
    """
    Atkinson dithering (made famous by original Macintosh).
    
    Only distributes 3/4 of the error, creating lighter images
    with more contrast. Good for photos.
    """
    h, w = img.shape
    result = np.zeros_like(img)
    
    kernel = [
        (0, 1, 1), (0, 2, 1),
        (1, -1, 1), (1, 0, 1), (1, 1, 1),
        (2, 0, 1)
    ]
    divisor = 8  # Only 6/8 = 3/4 of error distributed
    
    for y in range(h):
        for x in range(w):
            old_pixel = img[y, x]
            new_pixel = 255 if old_pixel >= 128 else 0
            result[y, x] = new_pixel
            error = old_pixel - new_pixel
            
            for dy, dx, weight in kernel:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += error * weight / divisor
    
    return (result > 0).astype(np.uint8)


def bayer_dither(img: np.ndarray, matrix_size: int = 4) -> np.ndarray:
    """
    Ordered Bayer matrix dithering.
    
    Uses a threshold matrix that creates regular patterns.
    Fast and good for graphics/illustrations.
    
    Args:
        img: Input grayscale image
        matrix_size: Size of Bayer matrix (2, 4, or 8)
    """
    # Bayer matrices
    bayer_2 = np.array([
        [0, 2],
        [3, 1]
    ]) / 4.0
    
    bayer_4 = np.array([
        [0, 8, 2, 10],
        [12, 4, 14, 6],
        [3, 11, 1, 9],
        [15, 7, 13, 5]
    ]) / 16.0
    
    bayer_8 = np.array([
        [0, 32, 8, 40, 2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38],
        [60, 28, 52, 20, 62, 30, 54, 22],
        [3, 35, 11, 43, 1, 33, 9, 41],
        [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47, 7, 39, 13, 45, 5, 37],
        [63, 31, 55, 23, 61, 29, 53, 21]
    ]) / 64.0
    
    matrices = {2: bayer_2, 4: bayer_4, 8: bayer_8}
    matrix = matrices.get(matrix_size, bayer_4)
    
    h, w = img.shape
    m_h, m_w = matrix.shape
    
    # Tile the matrix across the image
    threshold = np.tile(matrix, (h // m_h + 1, w // m_w + 1))[:h, :w]
    
    # Apply threshold
    result = (img / 255.0 > threshold).astype(np.uint8)
    
    return result


def halftone_dither(img: np.ndarray, dot_size: int = 4) -> np.ndarray:
    """
    Halftone dithering (simulates newspaper printing).
    
    Creates circular dots of varying sizes based on intensity.
    """
    h, w = img.shape
    result = np.zeros_like(img)
    
    # Process in blocks
    for y in range(0, h, dot_size):
        for x in range(0, w, dot_size):
            # Get average intensity of block
            block = img[y:min(y+dot_size, h), x:min(x+dot_size, w)]
            avg = np.mean(block)
            
            # Calculate dot radius based on intensity
            # Higher intensity = smaller dot (more white)
            radius = int((1 - avg / 255) * (dot_size / 2))
            
            # Draw circular dot
            center_y, center_x = dot_size // 2, dot_size // 2
            for dy in range(dot_size):
                for dx in range(dot_size):
                    if y + dy < h and x + dx < w:
                        dist = np.sqrt((dy - center_y)**2 + (dx - center_x)**2)
                        result[y + dy, x + dx] = 0 if dist <= radius else 1
    
    return result


def image_to_scanlines(image: Image.Image, 
                       dpi: float = 254,
                       bidirectional: bool = True) -> list:
    """
    Convert a dithered image to laser scanlines.
    
    Args:
        image: Binary (1-bit) dithered image
        dpi: Dots per inch (determines line spacing)
        bidirectional: Alternate scan direction
    
    Returns:
        List of scanlines, each containing (y, [(x_start, x_end), ...])
    """
    if image.mode != '1':
        image = image.convert('1')
    
    img_array = np.array(image)
    h, w = img_array.shape
    
    # Calculate mm per pixel
    mm_per_pixel = 25.4 / dpi
    
    scanlines = []
    
    for y in range(h):
        row = img_array[y]
        y_mm = y * mm_per_pixel
        
        # Find runs of black pixels
        runs = []
        in_run = False
        run_start = 0
        
        # Reverse every other row for bidirectional
        if bidirectional and y % 2 == 1:
            row = row[::-1]
        
        for x in range(w):
            is_black = row[x] == 0
            
            if is_black and not in_run:
                run_start = x
                in_run = True
            elif not is_black and in_run:
                runs.append((run_start * mm_per_pixel, x * mm_per_pixel))
                in_run = False
        
        if in_run:
            runs.append((run_start * mm_per_pixel, w * mm_per_pixel))
        
        # Reverse runs for reversed rows
        if bidirectional and y % 2 == 1:
            runs = [(w * mm_per_pixel - end, w * mm_per_pixel - start) 
                    for start, end in runs]
            runs.reverse()
        
        if runs:
            scanlines.append((y_mm, runs))
    
    return scanlines
```

### 10.2 Image Tracing (Vectorization)

```python
# src/image/tracing.py

"""
Image Tracing - Convert Raster Images to Vector Paths

Uses potrace algorithm for high-quality vectorization.
"""

import numpy as np
from PIL import Image
from typing import List, Optional
import subprocess
import tempfile
import os

from ..core.shapes import Path, Point


def trace_image(image: Image.Image,
                threshold: int = 128,
                turdsize: int = 2,
                alphamax: float = 1.0,
                opticurve: bool = True) -> List[Path]:
    """
    Trace a raster image to vector paths.
    
    Args:
        image: PIL Image to trace
        threshold: Black/white threshold (0-255)
        turdsize: Suppress speckles of this size and smaller
        alphamax: Corner threshold (0=sharp, 1.334=smooth)
        opticurve: Optimize curves
    
    Returns:
        List of Path objects
    """
    # Try using potrace if available
    try:
        return _trace_with_potrace(image, threshold, turdsize, alphamax, opticurve)
    except Exception:
        # Fallback to simple contour tracing
        return _trace_simple(image, threshold)


def _trace_with_potrace(image: Image.Image,
                        threshold: int,
                        turdsize: int,
                        alphamax: float,
                        opticurve: bool) -> List[Path]:
    """Trace using external potrace command."""
    # Convert to bitmap
    if image.mode != '1':
        gray = image.convert('L')
        bw = gray.point(lambda x: 0 if x < threshold else 255, '1')
    else:
        bw = image
    
    # Save as temporary BMP
    with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as tmp_bmp:
        bw.save(tmp_bmp.name)
        bmp_path = tmp_bmp.name
    
    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp_svg:
        svg_path = tmp_svg.name
    
    try:
        # Run potrace
        cmd = [
            'potrace',
            '-s',  # SVG output
            '-t', str(turdsize),
            '-a', str(alphamax),
            '-o', svg_path,
            bmp_path
        ]
        
        if opticurve:
            cmd.insert(1, '-O')
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Parse SVG output
        from ..io.svg_parser import SVGParser
        parser = SVGParser()
        doc = parser.parse_file(svg_path)
        
        # Extract paths
        paths = []
        for layer in doc.layers:
            for shape in layer.shapes:
                if isinstance(shape, Path):
                    paths.append(shape)
        
        return paths
        
    finally:
        # Cleanup
        os.unlink(bmp_path)
        if os.path.exists(svg_path):
            os.unlink(svg_path)


def _trace_simple(image: Image.Image, threshold: int = 128) -> List[Path]:
    """
    Simple contour tracing without external dependencies.
    
    Uses a basic marching squares algorithm.
    """
    # Convert to binary
    if image.mode != 'L':
        image = image.convert('L')
    
    img = np.array(image)
    binary = (img < threshold).astype(np.uint8)
    
    h, w = binary.shape
    paths = []
    
    # Find contours using basic algorithm
    visited = np.zeros_like(binary, dtype=bool)
    
    # Direction vectors (clockwise: right, down, left, up)
    dx = [1, 0, -1, 0]
    dy = [0, 1, 0, -1]
    
    for start_y in range(h - 1):
        for start_x in range(w - 1):
            # Find edge pixel (black next to white)
            if binary[start_y, start_x] == 1 and not visited[start_y, start_x]:
                # Check if this is an edge
                is_edge = False
                for d in range(4):
                    ny, nx = start_y + dy[d], start_x + dx[d]
                    if 0 <= ny < h and 0 <= nx < w and binary[ny, nx] == 0:
                        is_edge = True
                        break
                
                if is_edge:
                    # Trace contour
                    contour = _trace_contour(binary, visited, start_x, start_y)
                    if len(contour) >= 3:
                        path = Path()
                        path.move_to(contour[0][0], contour[0][1])
                        for x, y in contour[1:]:
                            path.line_to(x, y)
                        path.close()
                        paths.append(path)
    
    return paths


def _trace_contour(binary: np.ndarray, 
                   visited: np.ndarray,
                   start_x: int, 
                   start_y: int) -> List[tuple]:
    """Trace a single contour starting from given point."""
    h, w = binary.shape
    contour = []
    
    x, y = start_x, start_y
    direction = 0  # Start going right
    
    # Direction vectors
    dx = [1, 0, -1, 0]
    dy = [0, 1, 0, -1]
    
    max_steps = h * w * 4  # Safety limit
    steps = 0
    
    while steps < max_steps:
        contour.append((x, y))
        visited[y, x] = True
        
        # Try to turn right, then straight, then left, then back
        for turn in [-1, 0, 1, 2]:
            new_dir = (direction + turn) % 4
            nx, ny = x + dx[new_dir], y + dy[new_dir]
            
            if 0 <= nx < w and 0 <= ny < h and binary[ny, nx] == 1:
                x, y = nx, ny
                direction = new_dir
                break
        else:
            # Can't continue
            break
        
        # Check if back to start
        if x == start_x and y == start_y:
            break
        
        steps += 1
    
    return contour
```

---

*Continued in Part 3: [DEVELOPMENT_GUIDE_PART3.md](DEVELOPMENT_GUIDE_PART3.md)*

