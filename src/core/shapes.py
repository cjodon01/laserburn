"""
LaserBurn Core Shapes Module

Defines the fundamental shape classes: Point, BoundingBox, and all shape types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from uuid import UUID, uuid4
import math


@dataclass
class Point:
    """A 2D point."""
    x: float
    y: float
    
    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)
    
    def distance_to(self, other: 'Point') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def rotate(self, angle: float, center: 'Point' = None) -> 'Point':
        """Rotate point around center by angle (radians)."""
        if center is None:
            center = Point(0, 0)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        dx = self.x - center.x
        dy = self.y - center.y
        return Point(
            center.x + dx * cos_a - dy * sin_a,
            center.y + dx * sin_a + dy * cos_a
        )


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
    
    @property
    def center(self) -> Point:
        return Point(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )
    
    def contains(self, point: Point) -> bool:
        """Check if point is inside bounding box."""
        return (self.min_x <= point.x <= self.max_x and
                self.min_y <= point.y <= self.max_y)
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if two bounding boxes overlap."""
        return not (self.max_x < other.min_x or
                   self.min_x > other.max_x or
                   self.max_y < other.min_y or
                   self.min_y > other.max_y)


@dataclass
class LaserSettings:
    """Laser parameters for a shape or layer."""
    power: float = 50.0          # Percentage (0-100)
    speed: float = 100.0         # mm/s
    passes: int = 1              # Number of passes
    z_offset: float = 0.0        # Focus offset in mm
    air_assist: bool = True      # Air assist on/off
    line_interval: float = 0.1   # For fill operations (mm)
    
    # Operation type
    operation: str = "cut"       # "cut", "engrave", "fill"
    
    # Fill pattern settings
    fill_enabled: bool = False   # Enable fill pattern
    fill_pattern: str = "horizontal"  # "horizontal", "vertical", "crosshatch", "diagonal"
    fill_angle: float = 0.0      # Fill angle in degrees (for diagonal patterns)


class Shape(ABC):
    """
    Abstract base class for all shapes.
    
    Every shape must implement:
    - get_paths(): Return list of paths for laser cutting
    - get_bounding_box(): Return axis-aligned bounding box
    - clone(): Create a deep copy
    - contains_point(): Check if point is inside shape
    """
    
    def __init__(self):
        self.id: UUID = uuid4()
        self.name: str = ""
        self.visible: bool = True
        self.locked: bool = False
        self.laser_settings: LaserSettings = LaserSettings()
        
        # Transform properties
        self.position: Point = Point(0, 0)
        self.rotation: float = 0.0  # radians
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
    
    @abstractmethod
    def get_paths(self) -> List[List[Point]]:
        """
        Return the shape as a list of paths.
        Each path is a list of points representing a polyline.
        Closed shapes should have first point == last point.
        """
        pass
    
    @abstractmethod
    def get_bounding_box(self) -> BoundingBox:
        """Return the axis-aligned bounding box."""
        pass
    
    @abstractmethod
    def clone(self) -> 'Shape':
        """Create a deep copy of this shape."""
        pass
    
    @abstractmethod
    def contains_point(self, point: Point) -> bool:
        """Check if point is inside/on the shape."""
        pass
    
    def apply_transform(self, points: List[Point]) -> List[Point]:
        """Apply position, rotation, and scale to points."""
        result = []
        for p in points:
            # Scale
            x = p.x * self.scale_x
            y = p.y * self.scale_y
            # Rotate
            cos_r = math.cos(self.rotation)
            sin_r = math.sin(self.rotation)
            rx = x * cos_r - y * sin_r
            ry = x * sin_r + y * cos_r
            # Translate
            result.append(Point(rx + self.position.x, ry + self.position.y))
        return result


class Rectangle(Shape):
    """A rectangle shape."""
    
    def __init__(self, x: float, y: float, width: float, height: float,
                 corner_radius: float = 0.0):
        super().__init__()
        self.position = Point(x, y)
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
    
    def get_paths(self) -> List[List[Point]]:
        """Generate rectangle path, optionally with rounded corners."""
        if self.corner_radius <= 0:
            # Simple rectangle
            points = [
                Point(0, 0),
                Point(self.width, 0),
                Point(self.width, self.height),
                Point(0, self.height),
                Point(0, 0)  # Close the path
            ]
        else:
            # Rounded rectangle - generate arc segments
            r = min(self.corner_radius, self.width/2, self.height/2)
            points = []
            
            # Generate points for each corner arc
            segments_per_corner = 8
            for i in range(segments_per_corner + 1):
                angle = math.pi + (math.pi/2) * (i / segments_per_corner)
                points.append(Point(
                    r + r * math.cos(angle),
                    r + r * math.sin(angle)
                ))
            
            for i in range(segments_per_corner + 1):
                angle = math.pi * 1.5 + (math.pi/2) * (i / segments_per_corner)
                points.append(Point(
                    self.width - r + r * math.cos(angle),
                    r + r * math.sin(angle)
                ))
            
            for i in range(segments_per_corner + 1):
                angle = 0 + (math.pi/2) * (i / segments_per_corner)
                points.append(Point(
                    self.width - r + r * math.cos(angle),
                    self.height - r + r * math.sin(angle)
                ))
            
            for i in range(segments_per_corner + 1):
                angle = math.pi/2 + (math.pi/2) * (i / segments_per_corner)
                points.append(Point(
                    r + r * math.cos(angle),
                    self.height - r + r * math.sin(angle)
                ))
            
            points.append(points[0])  # Close path
        
        return [self.apply_transform(points)]
    
    def get_bounding_box(self) -> BoundingBox:
        paths = self.get_paths()
        all_points = [p for path in paths for p in path]
        if not all_points:
            return BoundingBox(0, 0, 0, 0)
        return BoundingBox(
            min_x=min(p.x for p in all_points),
            min_y=min(p.y for p in all_points),
            max_x=max(p.x for p in all_points),
            max_y=max(p.y for p in all_points)
        )
    
    def clone(self) -> 'Rectangle':
        r = Rectangle(self.position.x, self.position.y, 
                     self.width, self.height, self.corner_radius)
        r.rotation = self.rotation
        r.scale_x = self.scale_x
        r.scale_y = self.scale_y
        r.laser_settings = LaserSettings(**self.laser_settings.__dict__)
        return r
    
    def contains_point(self, point: Point) -> bool:
        bb = self.get_bounding_box()
        return bb.contains(point)


class Ellipse(Shape):
    """An ellipse shape."""
    
    def __init__(self, center_x: float, center_y: float, 
                 radius_x: float, radius_y: float):
        super().__init__()
        self.position = Point(center_x, center_y)
        self.radius_x = radius_x
        self.radius_y = radius_y
    
    def get_paths(self) -> List[List[Point]]:
        """Generate ellipse as a series of line segments."""
        segments = max(32, int(max(self.radius_x, self.radius_y) * 2))
        points = []
        
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            points.append(Point(
                self.radius_x * math.cos(angle),
                self.radius_y * math.sin(angle)
            ))
        
        return [self.apply_transform(points)]
    
    def get_bounding_box(self) -> BoundingBox:
        # For rotated ellipse, we need to compute actual bounds
        paths = self.get_paths()
        all_points = [p for path in paths for p in path]
        if not all_points:
            return BoundingBox(0, 0, 0, 0)
        return BoundingBox(
            min_x=min(p.x for p in all_points),
            min_y=min(p.y for p in all_points),
            max_x=max(p.x for p in all_points),
            max_y=max(p.y for p in all_points)
        )
    
    def clone(self) -> 'Ellipse':
        e = Ellipse(self.position.x, self.position.y,
                   self.radius_x, self.radius_y)
        e.rotation = self.rotation
        e.scale_x = self.scale_x
        e.scale_y = self.scale_y
        e.laser_settings = LaserSettings(**self.laser_settings.__dict__)
        return e
    
    def contains_point(self, point: Point) -> bool:
        # Transform point to local coordinates
        local = Point(point.x - self.position.x, point.y - self.position.y)
        # Check if inside ellipse equation
        return ((local.x / self.radius_x)**2 + 
                (local.y / self.radius_y)**2) <= 1


# Path segment types
@dataclass
class PathSegment(ABC):
    @abstractmethod
    def clone(self) -> 'PathSegment':
        pass

@dataclass
class MoveToSegment(PathSegment):
    point: Point
    def clone(self) -> 'MoveToSegment':
        return MoveToSegment(Point(self.point.x, self.point.y))

@dataclass
class LineToSegment(PathSegment):
    point: Point
    def clone(self) -> 'LineToSegment':
        return LineToSegment(Point(self.point.x, self.point.y))

@dataclass
class CubicBezierSegment(PathSegment):
    cp1: Point
    cp2: Point
    end_point: Point
    def clone(self) -> 'CubicBezierSegment':
        return CubicBezierSegment(
            Point(self.cp1.x, self.cp1.y),
            Point(self.cp2.x, self.cp2.y),
            Point(self.end_point.x, self.end_point.y)
        )

@dataclass
class QuadraticBezierSegment(PathSegment):
    control_point: Point
    end_point: Point
    def clone(self) -> 'QuadraticBezierSegment':
        return QuadraticBezierSegment(
            Point(self.control_point.x, self.control_point.y),
            Point(self.end_point.x, self.end_point.y)
        )


def flatten_cubic_bezier(p0: Point, p1: Point, p2: Point, p3: Point,
                         tolerance: float = 0.01) -> List[Point]:
    """
    Flatten a cubic bezier curve to line segments using recursive subdivision.
    
    Uses the de Casteljau algorithm with flatness test.
    """
    def is_flat(p0: Point, p1: Point, p2: Point, p3: Point, tol: float) -> bool:
        """Check if curve is flat enough to approximate with a line."""
        # Distance from control points to line p0-p3
        ux = 3*p1.x - 2*p0.x - p3.x
        uy = 3*p1.y - 2*p0.y - p3.y
        vx = 3*p2.x - 2*p3.x - p0.x
        vy = 3*p2.y - 2*p3.y - p0.y
        return max(ux*ux, vx*vx) + max(uy*uy, vy*vy) <= 16 * tol * tol
    
    def subdivide(p0: Point, p1: Point, p2: Point, p3: Point,
                  tol: float, points: List[Point]) -> None:
        if is_flat(p0, p1, p2, p3, tol):
            points.append(p3)
        else:
            # de Casteljau subdivision at t=0.5
            q0 = Point((p0.x + p1.x) / 2, (p0.y + p1.y) / 2)
            q1 = Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)
            q2 = Point((p2.x + p3.x) / 2, (p2.y + p3.y) / 2)
            r0 = Point((q0.x + q1.x) / 2, (q0.y + q1.y) / 2)
            r1 = Point((q1.x + q2.x) / 2, (q1.y + q2.y) / 2)
            s = Point((r0.x + r1.x) / 2, (r0.y + r1.y) / 2)
            
            subdivide(p0, q0, r0, s, tol, points)
            subdivide(s, r1, q2, p3, tol, points)
    
    points = [p0]
    subdivide(p0, p1, p2, p3, tolerance, points)
    return points


def flatten_quadratic_bezier(p0: Point, p1: Point, p2: Point,
                             tolerance: float = 0.01) -> List[Point]:
    """Flatten a quadratic bezier curve to line segments."""
    # Convert to cubic and use cubic flattening
    # Quadratic: P(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
    # Cubic equivalent control points:
    cp1 = Point(p0.x + 2/3 * (p1.x - p0.x), p0.y + 2/3 * (p1.y - p0.y))
    cp2 = Point(p2.x + 2/3 * (p1.x - p2.x), p2.y + 2/3 * (p1.y - p2.y))
    return flatten_cubic_bezier(p0, cp1, cp2, p2, tolerance)


def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
    """
    Check if a point is inside a polygon using ray casting.
    """
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        if ((polygon[i].y > point.y) != (polygon[j].y > point.y) and
            point.x < (polygon[j].x - polygon[i].x) * 
            (point.y - polygon[i].y) / (polygon[j].y - polygon[i].y) + 
            polygon[i].x):
            inside = not inside
        j = i
    
    return inside


class Text(Shape):
    """
    A text shape that can be converted to paths for laser cutting.
    
    Text is stored as content and font properties, then converted
    to paths when needed for rendering or G-code generation.
    """
    
    def __init__(self, x: float, y: float, text: str, 
                 font_family: str = "Arial", font_size: float = 12.0,
                 bold: bool = False, italic: bool = False):
        """
        Create a text shape.
        
        Args:
            x: X position (left baseline)
            y: Y position (baseline)
            text: Text content
            font_family: Font family name
            font_size: Font size in points
            bold: Whether text is bold
            italic: Whether text is italic
        """
        super().__init__()
        self.position = Point(x, y)
        self.text = text
        self.font_family = font_family
        self.font_size = font_size
        self.bold = bold
        self.italic = italic
        
        # Cached path representation (computed on demand)
        self._cached_paths: Optional[List[List[Point]]] = None
    
    def get_paths(self) -> List[List[Point]]:
        """
        Convert text to paths.
        
        This uses Qt's font rendering to convert text outlines to paths.
        The text is rendered as a QPainterPath, then converted to our Point format.
        """
        # Check if text is empty
        if not self.text or not self.text.strip():
            return []
        
        # If cached, apply transforms to each path
        if self._cached_paths is not None:
            result = []
            for path_points in self._cached_paths:
                if path_points and len(path_points) > 0:
                    transformed = self.apply_transform(path_points)
                    if transformed and len(transformed) > 0:
                        result.append(transformed)
            return result if result else []
        
        # Import Qt here to avoid circular dependencies
        from PyQt6.QtGui import QFont, QPainterPath, QFontMetrics
        from PyQt6.QtCore import Qt
        
        # Create font
        font = QFont(self.font_family, int(self.font_size))
        font.setBold(self.bold)
        font.setItalic(self.italic)
        
        # Create path from text
        path = QPainterPath()
        path.addText(0, 0, font, self.text)
        
        # Convert QPainterPath to our path format
        self._cached_paths = self._qpath_to_paths(path)
        
        # Apply transforms to each path
        result = []
        for path_points in self._cached_paths:
            if path_points and len(path_points) > 0:
                transformed = self.apply_transform(path_points)
                if transformed and len(transformed) > 0:
                    result.append(transformed)
        return result if result else []
    
    def _qpath_to_paths(self, qpath) -> List[List[Point]]:
        """Convert QPainterPath to list of point lists."""
        # Use toSubpathPolygons to get simplified paths
        # This converts curves to polygons
        from PyQt6.QtGui import QTransform
        
        paths = []
        polygons = qpath.toSubpathPolygons(QTransform())
        
        for polygon in polygons:
            if polygon.size() < 2:
                continue
            path_points = []
            for i in range(polygon.size()):
                pt = polygon.at(i)
                path_points.append(Point(pt.x(), pt.y()))
            if path_points:
                paths.append(path_points)
        
        return paths if paths else [[]]
    
    def get_bounding_box(self) -> BoundingBox:
        """Get bounding box of text."""
        paths = self.get_paths()
        all_points = [p for path in paths for p in path]
        if not all_points:
            return BoundingBox(0, 0, 0, 0)
        return BoundingBox(
            min_x=min(p.x for p in all_points),
            min_y=min(p.y for p in all_points),
            max_x=max(p.x for p in all_points),
            max_y=max(p.y for p in all_points)
        )
    
    def clone(self) -> 'Text':
        """Create a deep copy."""
        t = Text(
            self.position.x, self.position.y,
            self.text,
            self.font_family, self.font_size,
            self.bold, self.italic
        )
        t.rotation = self.rotation
        t.scale_x = self.scale_x
        t.scale_y = self.scale_y
        t.laser_settings = LaserSettings(**self.laser_settings.__dict__)
        return t
    
    def contains_point(self, point: Point) -> bool:
        """Check if point is inside text bounding box."""
        bb = self.get_bounding_box()
        return bb.contains(point)
    
    def invalidate_cache(self):
        """Invalidate cached paths (call when text properties change)."""
        self._cached_paths = None


class Path(Shape):
    """
    A path consisting of line segments and curves.
    This is the most flexible shape type.
    """
    
    def __init__(self):
        super().__init__()
        self.segments: List[PathSegment] = []
        self.closed: bool = False
    
    def move_to(self, x: float, y: float) -> 'Path':
        """Start a new subpath at the given point."""
        self.segments.append(MoveToSegment(Point(x, y)))
        return self
    
    def line_to(self, x: float, y: float) -> 'Path':
        """Draw a line to the given point."""
        self.segments.append(LineToSegment(Point(x, y)))
        return self
    
    def cubic_to(self, cp1x: float, cp1y: float, 
                 cp2x: float, cp2y: float,
                 x: float, y: float) -> 'Path':
        """Draw a cubic bezier curve."""
        self.segments.append(CubicBezierSegment(
            Point(cp1x, cp1y), Point(cp2x, cp2y), Point(x, y)
        ))
        return self
    
    def quadratic_to(self, cpx: float, cpy: float,
                     x: float, y: float) -> 'Path':
        """Draw a quadratic bezier curve."""
        self.segments.append(QuadraticBezierSegment(
            Point(cpx, cpy), Point(x, y)
        ))
        return self
    
    def close(self) -> 'Path':
        """Close the current subpath."""
        self.closed = True
        return self
    
    def get_paths(self) -> List[List[Point]]:
        """Flatten curves to line segments."""
        all_paths = []
        current_path = []
        current = None  # Don't initialize to (0,0) - wait for MoveTo
        path_start = None
        
        for seg in self.segments:
            if isinstance(seg, MoveToSegment):
                # If we have a current path, save it and start a new one
                if current_path and current is not None:
                    # Close path if needed
                    if self.closed and len(current_path) > 0 and path_start is not None:
                        # Only close if not already at start point
                        if current_path[0].x != current.x or current_path[0].y != current.y:
                            current_path.append(Point(current_path[0].x, current_path[0].y))
                    all_paths.append(current_path)
                # Start new subpath
                current_path = []
                current = seg.point
                path_start = current
                current_path.append(current)
            elif isinstance(seg, LineToSegment):
                if current is None:
                    # If no MoveTo yet, skip this segment
                    continue
                current = seg.point
                current_path.append(current)
            elif isinstance(seg, CubicBezierSegment):
                if current is None:
                    # If no MoveTo yet, skip this segment
                    continue
                # Flatten cubic bezier to line segments with higher quality
                bezier_points = flatten_cubic_bezier(
                    current, seg.cp1, seg.cp2, seg.end_point, tolerance=0.01
                )
                current_path.extend(bezier_points[1:])  # Skip first (current)
                current = seg.end_point
            elif isinstance(seg, QuadraticBezierSegment):
                if current is None:
                    # If no MoveTo yet, skip this segment
                    continue
                # Flatten quadratic bezier to line segments with higher quality
                bezier_points = flatten_quadratic_bezier(
                    current, seg.control_point, seg.end_point, tolerance=0.01
                )
                current_path.extend(bezier_points[1:])
                current = seg.end_point
        
        # Add the last path (only if it has points and current is set)
        if current_path and current is not None:
            # Close path if needed
            if self.closed and len(current_path) > 0 and path_start is not None:
                # Only close if not already at start point
                if current_path[0].x != current.x or current_path[0].y != current.y:
                    current_path.append(Point(current_path[0].x, current_path[0].y))
            all_paths.append(current_path)
        
        # Apply transforms to all paths
        result = []
        for path_points in all_paths:
            if path_points and len(path_points) > 0:
                transformed = self.apply_transform(path_points)
                if transformed:
                    result.append(transformed)
        
        return result if result else [[]]
    
    def get_bounding_box(self) -> BoundingBox:
        paths = self.get_paths()
        all_points = [p for path in paths for p in path]
        if not all_points:
            return BoundingBox(0, 0, 0, 0)
        return BoundingBox(
            min_x=min(p.x for p in all_points),
            min_y=min(p.y for p in all_points),
            max_x=max(p.x for p in all_points),
            max_y=max(p.y for p in all_points)
        )
    
    def clone(self) -> 'Path':
        p = Path()
        p.segments = [seg.clone() for seg in self.segments]
        p.closed = self.closed
        p.position = Point(self.position.x, self.position.y)
        p.rotation = self.rotation
        p.scale_x = self.scale_x
        p.scale_y = self.scale_y
        p.laser_settings = LaserSettings(**self.laser_settings.__dict__)
        return p
    
    def contains_point(self, point: Point) -> bool:
        # Use ray casting algorithm for closed paths
        if not self.closed:
            return False
        paths = self.get_paths()
        if not paths:
            return False
        return point_in_polygon(point, paths[0])


class ImageShape(Shape):
    """
    An image shape for raster engraving.
    
    Stores the image data directly - no conversion to vectors.
    G-code generation handles converting to scanlines.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float,
                 image_data=None, filepath: str = ""):
        """
        Initialize an image shape.
        
        Args:
            x: X position (mm)
            y: Y position (mm)
            width: Display width (mm)
            height: Display height (mm)
            image_data: Grayscale numpy array (0-255, uint8) or None
            filepath: Original file path for reference
        """
        super().__init__()
        self.position = Point(x, y)
        self.width = width
        self.height = height
        self.image_data = image_data  # Grayscale numpy array
        self.alpha_channel = None  # Alpha channel (transparency mask) - None means no transparency
        self.filepath = filepath
        
        # Image engraving settings
        self.dpi = 254.0  # Engraving resolution (dots per inch)
        self.invert = False  # Invert image (swap black/white)
        self.threshold = 128  # For simple threshold mode
        self.dither_mode = "floyd_steinberg"  # Dithering algorithm
        self.brightness = 0.0  # Brightness adjustment (-100 to 100)
        self.contrast = 1.0  # Contrast multiplier (0.0 to 3.0, 1.0 = normal)
        self.skip_white = True  # Skip white pixels entirely (like LightBurn) - faster engraving
        self.white_threshold = 250  # Pixels >= this value are considered "white" and skipped
        
        # Set default laser settings for engraving
        self.laser_settings.operation = "image"
        self.laser_settings.power = 50.0
        self.laser_settings.speed = 100.0
    
    @property
    def image_width_px(self) -> int:
        """Get image width in pixels."""
        if self.image_data is not None:
            return self.image_data.shape[1]
        return 0
    
    @property
    def image_height_px(self) -> int:
        """Get image height in pixels."""
        if self.image_data is not None:
            return self.image_data.shape[0]
        return 0
    
    def get_paths(self) -> List[List[Point]]:
        """Return bounding rectangle path for display, with full transform support."""
        # Define rectangle in local coordinates (0,0 to width,height)
        # apply_transform() will handle scale, rotation, and position
        points = [
            Point(0, 0),
            Point(self.width, 0),
            Point(self.width, self.height),
            Point(0, self.height),
            Point(0, 0)  # Close the path
        ]
        return [self.apply_transform(points)]
    
    def get_bounding_box(self) -> BoundingBox:
        """Return bounding box from transformed paths (handles scale and rotation)."""
        paths = self.get_paths()
        all_points = [p for path in paths for p in path]
        if not all_points:
            return BoundingBox(0, 0, 0, 0)
        return BoundingBox(
            min_x=min(p.x for p in all_points),
            min_y=min(p.y for p in all_points),
            max_x=max(p.x for p in all_points),
            max_y=max(p.y for p in all_points)
        )
    
    def clone(self) -> 'ImageShape':
        img = ImageShape(
            self.position.x, self.position.y,
            self.width, self.height,
            self.image_data.copy() if self.image_data is not None else None,
            self.filepath
        )
        img.rotation = self.rotation
        img.scale_x = self.scale_x
        img.scale_y = self.scale_y
        img.dpi = self.dpi
        img.invert = self.invert
        img.threshold = self.threshold
        img.dither_mode = self.dither_mode
        img.brightness = self.brightness
        img.contrast = self.contrast
        img.skip_white = self.skip_white
        img.white_threshold = self.white_threshold
        img.alpha_channel = self.alpha_channel.copy() if self.alpha_channel is not None else None
        img.laser_settings = LaserSettings(**self.laser_settings.__dict__)
        return img
    
    def contains_point(self, point: Point) -> bool:
        bb = self.get_bounding_box()
        return bb.contains(point)

