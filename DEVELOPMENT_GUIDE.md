# LaserBurn Development Guide
## Complete Build Documentation for Laser Engraving Software

**Version:** 1.0  
**Target:** Feature parity with LightBurn  
**Audience:** Junior Developers  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Development Environment Setup](#3-development-environment-setup)
4. [Project Architecture](#4-project-architecture)
5. [Core Module Implementation](#5-core-module-implementation)
6. [File Format Support](#6-file-format-support)
7. [Vector Graphics Engine](#7-vector-graphics-engine)
8. [G-Code Generation](#8-g-code-generation)
9. [Laser Controller Communication](#9-laser-controller-communication)
10. [Image Processing Pipeline](#10-image-processing-pipeline)
11. [User Interface Development](#11-user-interface-development)
12. [Material Library System](#12-material-library-system)
13. [Camera Integration](#13-camera-integration)
14. [Testing Strategy](#14-testing-strategy)
15. [Deployment](#15-deployment)

---

## 1. Project Overview

### 1.1 What We're Building

LaserBurn is a cross-platform laser engraving and cutting software that allows users to:
- Design and edit vector graphics
- Import various file formats (SVG, DXF, AI, PDF, images)
- Control laser cutters/engravers directly
- Manage material presets for consistent results
- Use cameras for precise alignment

### 1.2 Core Features to Implement

| Feature Category | Specific Features |
|-----------------|-------------------|
| **File Support** | SVG, DXF, AI, PDF, PLT, PNG, JPG, GIF, BMP import/export |
| **Design Tools** | Lines, rectangles, ellipses, polygons, stars, text, bezier curves |
| **Editing Tools** | Node editing, boolean operations, offsetting, welding, grouping |
| **Laser Settings** | Power, speed, passes, frequency, air assist, Z-offset |
| **Controllers** | GRBL, Marlin, Smoothieware, Ruida, Trocen, TopWisdom |
| **Image Processing** | Dithering, tracing, brightness/contrast, grayscale modes |
| **Optimization** | Path optimization, cut ordering, tabs/bridges |
| **Camera** | Alignment, calibration, overlay positioning |

### 1.3 Target Platforms

- Windows 10/11 (primary)
- macOS 10.14+
- Linux (Ubuntu 20.04+, Fedora 35+)

---

## 2. Technology Stack

### 2.1 Recommended Stack (C++ with Qt)

```
Language:        C++17 or later
Framework:       Qt 6.x (LTS)
Build System:    CMake 3.21+
Graphics:        Qt Graphics View Framework + OpenGL
Serial:          Qt Serial Port
Image Processing: OpenCV 4.x
Vector Operations: Clipper2 library
File Parsing:    Custom parsers + third-party libraries
Database:        SQLite (via Qt SQL)
Testing:         Google Test + Qt Test
```

### 2.2 Alternative Stack (Python with PyQt)

```
Language:        Python 3.10+
Framework:       PyQt6 or PySide6
Graphics:        QGraphicsView + PyOpenGL
Serial:          pyserial
Image Processing: OpenCV-Python, Pillow, NumPy
Vector Operations: pyclipper
File Parsing:    svgpathtools, ezdxf
Database:        SQLite3
Testing:         pytest + pytest-qt
```

### 2.3 Why These Choices?

**Qt Framework Benefits:**
- Cross-platform with native look and feel
- Excellent graphics view framework for vector editing
- Built-in serial port support
- Extensive documentation
- Commercial-friendly licensing (LGPL)

**C++ vs Python:**
- C++: Better performance for real-time graphics, smaller binaries
- Python: Faster development, easier prototyping, more accessible for juniors

> **Recommendation:** Start with Python/PyQt for rapid prototyping, then migrate performance-critical sections to C++ if needed.

---

## 3. Development Environment Setup

### 3.1 Windows Setup

#### Step 1: Install Prerequisites

```powershell
# Install Chocolatey package manager (run as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install development tools
choco install git cmake python310 visualstudio2022community -y

# Install Qt (download from qt.io or use aqtinstall)
pip install aqtinstall
aqt install-qt windows desktop 6.6.0 win64_msvc2019_64
```

#### Step 2: Install Python Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install core dependencies
pip install PyQt6 PyQt6-WebEngine pyserial opencv-python numpy pillow pyclipper ezdxf svgpathtools scipy
pip install pytest pytest-qt black flake8 mypy
```

#### Step 3: Clone and Setup Project

```powershell
git clone https://github.com/your-org/laserburn.git
cd laserburn
pip install -e .
```

### 3.2 Project Directory Structure

```
laserburn/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── document.py            # Document model
│   │   ├── layer.py               # Layer management
│   │   ├── shapes.py              # Shape primitives
│   │   ├── path.py                # Vector path operations
│   │   └── transform.py           # Transformation matrix
│   ├── graphics/
│   │   ├── __init__.py
│   │   ├── canvas.py              # Main drawing canvas
│   │   ├── items.py               # Graphics items
│   │   ├── tools.py               # Drawing tools
│   │   └── selection.py           # Selection handling
│   ├── io/
│   │   ├── __init__.py
│   │   ├── svg_parser.py          # SVG import/export
│   │   ├── dxf_parser.py          # DXF import/export
│   │   ├── image_import.py        # Raster image import
│   │   └── project_file.py        # Native project format
│   ├── laser/
│   │   ├── __init__.py
│   │   ├── gcode_generator.py     # G-code generation
│   │   ├── controller.py          # Controller base class
│   │   ├── grbl.py                # GRBL controller
│   │   ├── ruida.py               # Ruida controller
│   │   └── job_manager.py         # Job queue management
│   ├── image/
│   │   ├── __init__.py
│   │   ├── dithering.py           # Dithering algorithms
│   │   ├── tracing.py             # Image to vector tracing
│   │   └── adjustments.py         # Brightness, contrast, etc.
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── mainwindow.py          # Main application window
│   │   ├── toolbar.py             # Tool bars
│   │   ├── panels/
│   │   │   ├── layers_panel.py
│   │   │   ├── properties_panel.py
│   │   │   ├── laser_panel.py
│   │   │   └── materials_panel.py
│   │   └── dialogs/
│   │       ├── settings_dialog.py
│   │       ├── device_dialog.py
│   │       └── material_dialog.py
│   ├── materials/
│   │   ├── __init__.py
│   │   ├── database.py            # Material database
│   │   └── presets.py             # Default presets
│   └── camera/
│       ├── __init__.py
│       ├── capture.py             # Camera capture
│       ├── calibration.py         # Camera calibration
│       └── overlay.py             # Design overlay
├── resources/
│   ├── icons/                     # UI icons
│   ├── fonts/                     # Bundled fonts
│   ├── materials.db               # Default materials database
│   └── styles/                    # Qt stylesheets
├── tests/
│   ├── __init__.py
│   ├── test_core/
│   ├── test_graphics/
│   ├── test_io/
│   ├── test_laser/
│   └── test_image/
├── docs/
│   ├── api/
│   ├── user_guide/
│   └── developer/
├── scripts/
│   ├── build.py
│   └── package.py
├── requirements.txt
├── setup.py
├── pyproject.toml
└── README.md
```

---

## 4. Project Architecture

### 4.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  Main Window│ │   Toolbars  │ │   Panels    │ │   Dialogs   │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        GRAPHICS LAYER                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │   Canvas    │ │    Tools    │ │  Selection  │ │  Rendering  │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CORE LAYER                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  Document   │ │   Layers    │ │   Shapes    │ │    Paths    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    I/O LAYER    │    │   LASER LAYER   │    │   IMAGE LAYER   │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │SVG Parser │  │    │  │  G-Code   │  │    │  │ Dithering │  │
│  │DXF Parser │  │    │  │ Generator │  │    │  │  Tracing  │  │
│  │Image Load │  │    │  │Controller │  │    │  │ Adjustments│  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ HARDWARE LAYER  │
                    │  Serial/USB/Net │
                    │   GRBL/Ruida    │
                    └─────────────────┘
```

### 4.2 Design Patterns to Use

| Pattern | Where to Use | Purpose |
|---------|-------------|---------|
| **MVC/MVP** | Overall application | Separate UI from business logic |
| **Command Pattern** | All user actions | Enable undo/redo functionality |
| **Factory Pattern** | Shape creation, Tool creation | Flexible object instantiation |
| **Observer Pattern** | Document changes, Selection | Update UI on data changes |
| **Strategy Pattern** | Dithering algorithms, Controllers | Interchangeable algorithms |
| **Singleton Pattern** | Settings, Material database | Global access to shared resources |

### 4.3 Core Classes Overview

```python
# src/core/document.py - Document Model

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4

@dataclass
class Document:
    """
    The root document containing all design data.
    
    A Document contains multiple Layers, each Layer contains Shapes.
    This is the central data structure that gets saved/loaded.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = "Untitled"
    width: float = 300.0      # mm
    height: float = 200.0     # mm
    layers: List['Layer'] = field(default_factory=list)
    
    # Laser settings
    device_profile: Optional[str] = None
    origin: str = "bottom-left"  # or "top-left"
    
    # Metadata
    created_at: str = ""
    modified_at: str = ""
    
    def add_layer(self, layer: 'Layer') -> None:
        """Add a layer to the document."""
        self.layers.append(layer)
        
    def get_all_shapes(self) -> List['Shape']:
        """Flatten all shapes from all layers."""
        shapes = []
        for layer in self.layers:
            shapes.extend(layer.shapes)
        return shapes
```

---

## 5. Core Module Implementation

### 5.1 Shape System

All shapes derive from a base `Shape` class. This provides consistent handling.

```python
# src/core/shapes.py

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


class Shape(ABC):
    """
    Abstract base class for all shapes.
    
    Every shape must implement:
    - get_paths(): Return list of paths for laser cutting
    - get_bounding_box(): Return axis-aligned bounding box
    - clone(): Create a deep copy
    - to_dict() / from_dict(): Serialization
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


class Path(Shape):
    """
    A path consisting of line segments and curves.
    This is the most flexible shape type.
    """
    
    def __init__(self):
        super().__init__()
        self.segments: List['PathSegment'] = []
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
        points = []
        current = Point(0, 0)
        
        for seg in self.segments:
            if isinstance(seg, MoveToSegment):
                if points:
                    # Start new subpath
                    pass
                current = seg.point
                points.append(current)
            elif isinstance(seg, LineToSegment):
                current = seg.point
                points.append(current)
            elif isinstance(seg, CubicBezierSegment):
                # Flatten cubic bezier to line segments
                bezier_points = flatten_cubic_bezier(
                    current, seg.cp1, seg.cp2, seg.end_point
                )
                points.extend(bezier_points[1:])  # Skip first (current)
                current = seg.end_point
            elif isinstance(seg, QuadraticBezierSegment):
                # Flatten quadratic bezier to line segments
                bezier_points = flatten_quadratic_bezier(
                    current, seg.control_point, seg.end_point
                )
                points.extend(bezier_points[1:])
                current = seg.end_point
        
        if self.closed and points:
            points.append(points[0])
        
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
                         tolerance: float = 0.1) -> List[Point]:
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
                             tolerance: float = 0.1) -> List[Point]:
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
```

### 5.2 Layer System

```python
# src/core/layer.py

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4
from .shapes import Shape, LaserSettings

@dataclass
class Layer:
    """
    A layer containing shapes with shared laser settings.
    
    Layers allow organizing shapes and applying different
    laser parameters to different groups of shapes.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = "Layer"
    visible: bool = True
    locked: bool = False
    
    # Layer-level laser settings (override shape settings if set)
    laser_settings: LaserSettings = field(default_factory=LaserSettings)
    use_layer_settings: bool = True
    
    # Visual properties
    color: str = "#0000FF"  # Display color in UI
    
    # Shapes in this layer
    shapes: List[Shape] = field(default_factory=list)
    
    # Cut order
    cut_order: int = 0  # Lower numbers cut first
    
    def add_shape(self, shape: Shape) -> None:
        """Add a shape to this layer."""
        self.shapes.append(shape)
    
    def remove_shape(self, shape: Shape) -> None:
        """Remove a shape from this layer."""
        if shape in self.shapes:
            self.shapes.remove(shape)
    
    def get_shape_by_id(self, shape_id: UUID) -> Optional[Shape]:
        """Find a shape by its ID."""
        for shape in self.shapes:
            if shape.id == shape_id:
                return shape
        return None
    
    def move_shape_up(self, shape: Shape) -> None:
        """Move shape up in the z-order."""
        idx = self.shapes.index(shape)
        if idx < len(self.shapes) - 1:
            self.shapes[idx], self.shapes[idx + 1] = \
                self.shapes[idx + 1], self.shapes[idx]
    
    def move_shape_down(self, shape: Shape) -> None:
        """Move shape down in the z-order."""
        idx = self.shapes.index(shape)
        if idx > 0:
            self.shapes[idx], self.shapes[idx - 1] = \
                self.shapes[idx - 1], self.shapes[idx]
```

---

## 6. File Format Support

### 6.1 SVG Parser Implementation

```python
# src/io/svg_parser.py

"""
SVG Parser for LaserBurn

Supports:
- Basic shapes: rect, circle, ellipse, line, polyline, polygon
- Paths with all commands (M, L, H, V, C, S, Q, T, A, Z)
- Groups and transforms
- Styles (stroke, fill)
"""

import re
import math
from xml.etree import ElementTree as ET
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from ..core.shapes import (
    Shape, Path, Rectangle, Ellipse, Point,
    MoveToSegment, LineToSegment, CubicBezierSegment, QuadraticBezierSegment
)
from ..core.document import Document
from ..core.layer import Layer


class SVGParser:
    """Parse SVG files into LaserBurn documents."""
    
    # SVG namespace
    SVG_NS = '{http://www.w3.org/2000/svg}'
    
    def __init__(self):
        self.document: Optional[Document] = None
        self.current_transform: List[float] = [1, 0, 0, 1, 0, 0]  # Identity matrix
    
    def parse_file(self, filepath: str) -> Document:
        """Parse an SVG file and return a Document."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        return self.parse_svg(root)
    
    def parse_string(self, svg_string: str) -> Document:
        """Parse an SVG string and return a Document."""
        root = ET.fromstring(svg_string)
        return self.parse_svg(root)
    
    def parse_svg(self, root: ET.Element) -> Document:
        """Parse the SVG root element."""
        # Get document dimensions
        width = self._parse_length(root.get('width', '300'))
        height = self._parse_length(root.get('height', '200'))
        
        # Handle viewBox
        viewbox = root.get('viewBox')
        if viewbox:
            vb_parts = viewbox.split()
            if len(vb_parts) == 4:
                width = float(vb_parts[2])
                height = float(vb_parts[3])
        
        self.document = Document(width=width, height=height)
        
        # Create default layer
        default_layer = Layer(name="SVG Import")
        self.document.add_layer(default_layer)
        
        # Parse all elements
        self._parse_element(root, default_layer)
        
        return self.document
    
    def _parse_element(self, element: ET.Element, layer: Layer) -> None:
        """Recursively parse SVG elements."""
        # Get tag name without namespace
        tag = element.tag.replace(self.SVG_NS, '')
        
        # Save current transform
        saved_transform = self.current_transform.copy()
        
        # Apply element's transform
        transform_str = element.get('transform')
        if transform_str:
            self._apply_transform(transform_str)
        
        # Parse element based on type
        shape = None
        if tag == 'rect':
            shape = self._parse_rect(element)
        elif tag == 'circle':
            shape = self._parse_circle(element)
        elif tag == 'ellipse':
            shape = self._parse_ellipse(element)
        elif tag == 'line':
            shape = self._parse_line(element)
        elif tag == 'polyline':
            shape = self._parse_polyline(element, closed=False)
        elif tag == 'polygon':
            shape = self._parse_polyline(element, closed=True)
        elif tag == 'path':
            shape = self._parse_path(element)
        elif tag in ('g', 'svg'):
            # Group - recurse into children
            for child in element:
                self._parse_element(child, layer)
        
        if shape:
            layer.add_shape(shape)
        
        # Restore transform
        self.current_transform = saved_transform
    
    def _parse_rect(self, element: ET.Element) -> Rectangle:
        """Parse a rect element."""
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))
        rx = float(element.get('rx', 0))
        ry = float(element.get('ry', rx))  # Default to rx if not specified
        corner_radius = max(rx, ry)
        
        return Rectangle(x, y, width, height, corner_radius)
    
    def _parse_circle(self, element: ET.Element) -> Ellipse:
        """Parse a circle element."""
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        r = float(element.get('r', 0))
        
        return Ellipse(cx, cy, r, r)
    
    def _parse_ellipse(self, element: ET.Element) -> Ellipse:
        """Parse an ellipse element."""
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        rx = float(element.get('rx', 0))
        ry = float(element.get('ry', 0))
        
        return Ellipse(cx, cy, rx, ry)
    
    def _parse_line(self, element: ET.Element) -> Path:
        """Parse a line element."""
        x1 = float(element.get('x1', 0))
        y1 = float(element.get('y1', 0))
        x2 = float(element.get('x2', 0))
        y2 = float(element.get('y2', 0))
        
        path = Path()
        path.move_to(x1, y1)
        path.line_to(x2, y2)
        return path
    
    def _parse_polyline(self, element: ET.Element, closed: bool) -> Path:
        """Parse a polyline or polygon element."""
        points_str = element.get('points', '')
        points = self._parse_points(points_str)
        
        if not points:
            return Path()
        
        path = Path()
        path.move_to(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.line_to(x, y)
        
        if closed:
            path.close()
        
        return path
    
    def _parse_path(self, element: ET.Element) -> Path:
        """Parse a path element's d attribute."""
        d = element.get('d', '')
        return self._parse_path_d(d)
    
    def _parse_path_d(self, d: str) -> Path:
        """
        Parse SVG path data string.
        
        Supports all path commands:
        M/m - moveto
        L/l - lineto
        H/h - horizontal lineto
        V/v - vertical lineto
        C/c - cubic bezier
        S/s - smooth cubic bezier
        Q/q - quadratic bezier
        T/t - smooth quadratic bezier
        A/a - elliptical arc
        Z/z - closepath
        """
        path = Path()
        
        # Tokenize the path string
        tokens = self._tokenize_path(d)
        if not tokens:
            return path
        
        current_x, current_y = 0.0, 0.0
        start_x, start_y = 0.0, 0.0
        last_control = None
        last_command = None
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token.isalpha():
                command = token
                i += 1
            else:
                # Repeat last command (except M becomes L)
                command = last_command
                if command == 'M':
                    command = 'L'
                elif command == 'm':
                    command = 'l'
            
            is_relative = command.islower()
            cmd_upper = command.upper()
            
            if cmd_upper == 'M':
                x, y = float(tokens[i]), float(tokens[i+1])
                i += 2
                if is_relative:
                    x += current_x
                    y += current_y
                path.move_to(x, y)
                current_x, current_y = x, y
                start_x, start_y = x, y
                last_control = None
                
            elif cmd_upper == 'L':
                x, y = float(tokens[i]), float(tokens[i+1])
                i += 2
                if is_relative:
                    x += current_x
                    y += current_y
                path.line_to(x, y)
                current_x, current_y = x, y
                last_control = None
                
            elif cmd_upper == 'H':
                x = float(tokens[i])
                i += 1
                if is_relative:
                    x += current_x
                path.line_to(x, current_y)
                current_x = x
                last_control = None
                
            elif cmd_upper == 'V':
                y = float(tokens[i])
                i += 1
                if is_relative:
                    y += current_y
                path.line_to(current_x, y)
                current_y = y
                last_control = None
                
            elif cmd_upper == 'C':
                x1, y1 = float(tokens[i]), float(tokens[i+1])
                x2, y2 = float(tokens[i+2]), float(tokens[i+3])
                x, y = float(tokens[i+4]), float(tokens[i+5])
                i += 6
                if is_relative:
                    x1 += current_x
                    y1 += current_y
                    x2 += current_x
                    y2 += current_y
                    x += current_x
                    y += current_y
                path.cubic_to(x1, y1, x2, y2, x, y)
                current_x, current_y = x, y
                last_control = Point(x2, y2)
                
            elif cmd_upper == 'S':
                # Smooth cubic - reflect last control point
                x2, y2 = float(tokens[i]), float(tokens[i+1])
                x, y = float(tokens[i+2]), float(tokens[i+3])
                i += 4
                if is_relative:
                    x2 += current_x
                    y2 += current_y
                    x += current_x
                    y += current_y
                # Reflect control point
                if last_control and last_command in ('C', 'c', 'S', 's'):
                    x1 = 2 * current_x - last_control.x
                    y1 = 2 * current_y - last_control.y
                else:
                    x1, y1 = current_x, current_y
                path.cubic_to(x1, y1, x2, y2, x, y)
                current_x, current_y = x, y
                last_control = Point(x2, y2)
                
            elif cmd_upper == 'Q':
                x1, y1 = float(tokens[i]), float(tokens[i+1])
                x, y = float(tokens[i+2]), float(tokens[i+3])
                i += 4
                if is_relative:
                    x1 += current_x
                    y1 += current_y
                    x += current_x
                    y += current_y
                path.quadratic_to(x1, y1, x, y)
                current_x, current_y = x, y
                last_control = Point(x1, y1)
                
            elif cmd_upper == 'T':
                # Smooth quadratic - reflect last control point
                x, y = float(tokens[i]), float(tokens[i+1])
                i += 2
                if is_relative:
                    x += current_x
                    y += current_y
                # Reflect control point
                if last_control and last_command in ('Q', 'q', 'T', 't'):
                    x1 = 2 * current_x - last_control.x
                    y1 = 2 * current_y - last_control.y
                else:
                    x1, y1 = current_x, current_y
                path.quadratic_to(x1, y1, x, y)
                current_x, current_y = x, y
                last_control = Point(x1, y1)
                
            elif cmd_upper == 'A':
                # Arc command - convert to bezier curves
                rx, ry = abs(float(tokens[i])), abs(float(tokens[i+1]))
                x_rot = float(tokens[i+2])
                large_arc = int(float(tokens[i+3]))
                sweep = int(float(tokens[i+4]))
                x, y = float(tokens[i+5]), float(tokens[i+6])
                i += 7
                if is_relative:
                    x += current_x
                    y += current_y
                
                # Convert arc to cubic beziers
                arc_paths = self._arc_to_bezier(
                    current_x, current_y, rx, ry, x_rot,
                    large_arc, sweep, x, y
                )
                for cp1, cp2, end in arc_paths:
                    path.cubic_to(cp1.x, cp1.y, cp2.x, cp2.y, end.x, end.y)
                
                current_x, current_y = x, y
                last_control = None
                
            elif cmd_upper == 'Z':
                path.close()
                current_x, current_y = start_x, start_y
                last_control = None
            
            last_command = command
        
        return path
    
    def _tokenize_path(self, d: str) -> List[str]:
        """Tokenize SVG path data into commands and numbers."""
        # Handle negative numbers and scientific notation
        pattern = r'([MmZzLlHhVvCcSsQqTtAa])|(-?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)'
        tokens = []
        for match in re.finditer(pattern, d):
            token = match.group()
            if token:
                tokens.append(token)
        return tokens
    
    def _parse_length(self, length_str: str) -> float:
        """Parse SVG length value with units."""
        if not length_str:
            return 0.0
        
        # Remove units and convert
        units = {
            'px': 1.0,
            'pt': 1.333,
            'pc': 16.0,
            'mm': 3.7795,
            'cm': 37.795,
            'in': 96.0,
            'em': 16.0,
        }
        
        for unit, factor in units.items():
            if length_str.endswith(unit):
                return float(length_str[:-len(unit)]) * factor
        
        return float(length_str)
    
    def _parse_points(self, points_str: str) -> List[Tuple[float, float]]:
        """Parse SVG points attribute."""
        points = []
        numbers = re.findall(r'-?[0-9]*\.?[0-9]+', points_str)
        for i in range(0, len(numbers) - 1, 2):
            points.append((float(numbers[i]), float(numbers[i+1])))
        return points
    
    def _apply_transform(self, transform_str: str) -> None:
        """Apply SVG transform to current matrix."""
        # Parse transforms like "translate(10, 20) rotate(45) scale(2)"
        transform_pattern = r'(translate|rotate|scale|matrix|skewX|skewY)\s*\(([^)]+)\)'
        
        for match in re.finditer(transform_pattern, transform_str):
            func = match.group(1)
            args = [float(x) for x in re.findall(r'-?[0-9]*\.?[0-9]+', match.group(2))]
            
            if func == 'translate':
                tx = args[0] if len(args) > 0 else 0
                ty = args[1] if len(args) > 1 else 0
                # Multiply current transform by translation
                # ... (matrix multiplication)
            elif func == 'rotate':
                angle = math.radians(args[0])
                # ... rotation matrix
            elif func == 'scale':
                sx = args[0] if len(args) > 0 else 1
                sy = args[1] if len(args) > 1 else sx
                # ... scale matrix
    
    def _arc_to_bezier(self, x1: float, y1: float, rx: float, ry: float,
                       phi: float, large_arc: int, sweep: int,
                       x2: float, y2: float) -> List[Tuple[Point, Point, Point]]:
        """Convert SVG arc to cubic bezier curves."""
        # Implementation of arc parameterization and bezier approximation
        # This is complex - using standard algorithm from W3C spec
        
        if rx == 0 or ry == 0:
            return []
        
        phi_rad = math.radians(phi)
        cos_phi = math.cos(phi_rad)
        sin_phi = math.sin(phi_rad)
        
        # Step 1: Compute (x1', y1')
        dx = (x1 - x2) / 2
        dy = (y1 - y2) / 2
        x1p = cos_phi * dx + sin_phi * dy
        y1p = -sin_phi * dx + cos_phi * dy
        
        # Ensure radii are large enough
        lambda_ = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
        if lambda_ > 1:
            rx *= math.sqrt(lambda_)
            ry *= math.sqrt(lambda_)
        
        # Step 2: Compute (cx', cy')
        sq = max(0, ((rx*rx * ry*ry) - (rx*rx * y1p*y1p) - (ry*ry * x1p*x1p)) /
                    ((rx*rx * y1p*y1p) + (ry*ry * x1p*x1p)))
        coef = math.sqrt(sq)
        if large_arc == sweep:
            coef = -coef
        cxp = coef * rx * y1p / ry
        cyp = -coef * ry * x1p / rx
        
        # Step 3: Compute (cx, cy) from (cx', cy')
        cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2
        cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2
        
        # Step 4: Compute theta1 and dtheta
        def angle(ux, uy, vx, vy):
            n = math.sqrt(ux*ux + uy*uy) * math.sqrt(vx*vx + vy*vy)
            c = (ux*vx + uy*vy) / n
            s = ux*vy - uy*vx
            return math.atan2(s, max(-1, min(1, c)))
        
        theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
        dtheta = angle((x1p - cxp) / rx, (y1p - cyp) / ry,
                       (-x1p - cxp) / rx, (-y1p - cyp) / ry)
        
        if sweep == 0 and dtheta > 0:
            dtheta -= 2 * math.pi
        elif sweep == 1 and dtheta < 0:
            dtheta += 2 * math.pi
        
        # Split arc into segments of max 90 degrees
        segments = max(1, int(math.ceil(abs(dtheta) / (math.pi / 2))))
        delta = dtheta / segments
        
        curves = []
        for i in range(segments):
            t1 = theta1 + i * delta
            t2 = theta1 + (i + 1) * delta
            
            # Bezier control points for arc segment
            alpha = math.sin(delta) * (math.sqrt(4 + 3 * math.tan(delta/2)**2) - 1) / 3
            
            x1_i = math.cos(t1)
            y1_i = math.sin(t1)
            x2_i = math.cos(t2)
            y2_i = math.sin(t2)
            
            cp1x = x1_i - alpha * y1_i
            cp1y = y1_i + alpha * x1_i
            cp2x = x2_i + alpha * y2_i
            cp2y = y2_i - alpha * x2_i
            
            # Transform back
            def transform_point(px, py):
                x = px * rx
                y = py * ry
                return Point(
                    cos_phi * x - sin_phi * y + cx,
                    sin_phi * x + cos_phi * y + cy
                )
            
            p1 = transform_point(x1_i, y1_i)
            c1 = transform_point(cp1x, cp1y)
            c2 = transform_point(cp2x, cp2y)
            p2 = transform_point(x2_i, y2_i)
            
            curves.append((c1, c2, p2))
        
        return curves


def export_svg(document: Document, filepath: str) -> None:
    """Export a Document to SVG format."""
    svg = ET.Element('svg')
    svg.set('xmlns', 'http://www.w3.org/2000/svg')
    svg.set('width', f'{document.width}mm')
    svg.set('height', f'{document.height}mm')
    svg.set('viewBox', f'0 0 {document.width} {document.height}')
    
    for layer in document.layers:
        g = ET.SubElement(svg, 'g')
        g.set('id', layer.name)
        g.set('stroke', layer.color)
        g.set('fill', 'none')
        
        for shape in layer.shapes:
            paths = shape.get_paths()
            for path_points in paths:
                if not path_points:
                    continue
                
                d = f'M {path_points[0].x},{path_points[0].y}'
                for point in path_points[1:]:
                    d += f' L {point.x},{point.y}'
                
                path_elem = ET.SubElement(g, 'path')
                path_elem.set('d', d)
    
    tree = ET.ElementTree(svg)
    tree.write(filepath, encoding='unicode', xml_declaration=True)
```

### 6.2 DXF Parser Implementation

```python
# src/io/dxf_parser.py

"""
DXF Parser for LaserBurn

Uses ezdxf library for parsing AutoCAD DXF files.
Supports DXF versions R12 through R2018.
"""

import ezdxf
from typing import List, Optional
from ..core.shapes import Shape, Path, Rectangle, Ellipse, Point
from ..core.document import Document
from ..core.layer import Layer


class DXFParser:
    """Parse DXF files into LaserBurn documents."""
    
    def __init__(self):
        self.document: Optional[Document] = None
    
    def parse_file(self, filepath: str) -> Document:
        """Parse a DXF file and return a Document."""
        dwg = ezdxf.readfile(filepath)
        return self._parse_drawing(dwg)
    
    def _parse_drawing(self, dwg) -> Document:
        """Parse ezdxf drawing object."""
        # Get drawing extents for document size
        # We'll calculate from entities
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        self.document = Document(width=300, height=200)
        
        # Create layer for each DXF layer
        modelspace = dwg.modelspace()
        dxf_layers = {}
        
        for entity in modelspace:
            layer_name = entity.dxf.layer
            
            if layer_name not in dxf_layers:
                layer = Layer(name=layer_name)
                dxf_layers[layer_name] = layer
                self.document.add_layer(layer)
            
            shape = self._parse_entity(entity)
            if shape:
                dxf_layers[layer_name].add_shape(shape)
                
                # Update bounds
                bb = shape.get_bounding_box()
                min_x = min(min_x, bb.min_x)
                min_y = min(min_y, bb.min_y)
                max_x = max(max_x, bb.max_x)
                max_y = max(max_y, bb.max_y)
        
        # Set document size based on extents
        if min_x != float('inf'):
            self.document.width = max_x - min_x + 20  # Add margin
            self.document.height = max_y - min_y + 20
        
        return self.document
    
    def _parse_entity(self, entity) -> Optional[Shape]:
        """Parse a single DXF entity."""
        dxf_type = entity.dxftype()
        
        if dxf_type == 'LINE':
            return self._parse_line(entity)
        elif dxf_type == 'CIRCLE':
            return self._parse_circle(entity)
        elif dxf_type == 'ARC':
            return self._parse_arc(entity)
        elif dxf_type == 'ELLIPSE':
            return self._parse_ellipse(entity)
        elif dxf_type == 'LWPOLYLINE':
            return self._parse_lwpolyline(entity)
        elif dxf_type == 'POLYLINE':
            return self._parse_polyline(entity)
        elif dxf_type == 'SPLINE':
            return self._parse_spline(entity)
        elif dxf_type == 'TEXT' or dxf_type == 'MTEXT':
            # Text handling would require font rendering
            # For now, skip or convert to paths
            pass
        
        return None
    
    def _parse_line(self, entity) -> Path:
        """Parse LINE entity."""
        start = entity.dxf.start
        end = entity.dxf.end
        
        path = Path()
        path.move_to(start.x, start.y)
        path.line_to(end.x, end.y)
        return path
    
    def _parse_circle(self, entity) -> Ellipse:
        """Parse CIRCLE entity."""
        center = entity.dxf.center
        radius = entity.dxf.radius
        
        return Ellipse(center.x, center.y, radius, radius)
    
    def _parse_arc(self, entity) -> Path:
        """Parse ARC entity."""
        import math
        
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)
        
        # Generate arc as line segments
        path = Path()
        
        # Determine number of segments
        angle_span = end_angle - start_angle
        if angle_span < 0:
            angle_span += 2 * math.pi
        
        segments = max(8, int(angle_span * radius / 2))
        
        for i in range(segments + 1):
            t = i / segments
            angle = start_angle + t * angle_span
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            
            if i == 0:
                path.move_to(x, y)
            else:
                path.line_to(x, y)
        
        return path
    
    def _parse_ellipse(self, entity) -> Ellipse:
        """Parse ELLIPSE entity."""
        center = entity.dxf.center
        major_axis = entity.dxf.major_axis
        ratio = entity.dxf.ratio  # minor/major ratio
        
        import math
        rx = math.sqrt(major_axis.x**2 + major_axis.y**2)
        ry = rx * ratio
        
        return Ellipse(center.x, center.y, rx, ry)
    
    def _parse_lwpolyline(self, entity) -> Path:
        """Parse LWPOLYLINE (lightweight polyline) entity."""
        path = Path()
        
        points = list(entity.get_points())
        if not points:
            return path
        
        # First point
        path.move_to(points[0][0], points[0][1])
        
        for i, point in enumerate(points[1:], 1):
            x, y = point[0], point[1]
            bulge = points[i-1][4] if len(points[i-1]) > 4 else 0
            
            if bulge != 0:
                # Bulge indicates arc - convert to line segments
                prev_x, prev_y = points[i-1][0], points[i-1][1]
                arc_points = self._bulge_to_arc(prev_x, prev_y, x, y, bulge)
                for ax, ay in arc_points[1:]:
                    path.line_to(ax, ay)
            else:
                path.line_to(x, y)
        
        if entity.closed:
            path.close()
        
        return path
    
    def _parse_polyline(self, entity) -> Path:
        """Parse POLYLINE entity (older format)."""
        path = Path()
        
        vertices = list(entity.vertices)
        if not vertices:
            return path
        
        path.move_to(vertices[0].dxf.location.x, vertices[0].dxf.location.y)
        
        for vertex in vertices[1:]:
            path.line_to(vertex.dxf.location.x, vertex.dxf.location.y)
        
        if entity.is_closed:
            path.close()
        
        return path
    
    def _parse_spline(self, entity) -> Path:
        """Parse SPLINE entity (B-spline)."""
        path = Path()
        
        # Get flattened points from spline
        try:
            points = list(entity.flattening(0.1))  # tolerance
            if not points:
                return path
            
            path.move_to(points[0].x, points[0].y)
            for point in points[1:]:
                path.line_to(point.x, point.y)
        except:
            # Fallback to control points
            control_points = entity.control_points
            if control_points:
                path.move_to(control_points[0].x, control_points[0].y)
                for cp in control_points[1:]:
                    path.line_to(cp.x, cp.y)
        
        return path
    
    def _bulge_to_arc(self, x1: float, y1: float, x2: float, y2: float,
                      bulge: float, segments: int = 8) -> List[tuple]:
        """Convert DXF bulge value to arc points."""
        import math
        
        # Bulge = tan(angle/4)
        angle = 4 * math.atan(bulge)
        
        # Chord length
        dx = x2 - x1
        dy = y2 - y1
        chord = math.sqrt(dx*dx + dy*dy)
        
        if chord == 0:
            return [(x2, y2)]
        
        # Radius
        radius = abs(chord / (2 * math.sin(angle / 2)))
        
        # Sagitta (height of arc)
        sagitta = abs(bulge * chord / 2)
        
        # Center of arc
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        
        # Perpendicular direction
        px = -dy / chord
        py = dx / chord
        
        # Distance from midpoint to center
        d = math.sqrt(radius*radius - (chord/2)**2)
        if bulge < 0:
            d = -d
        
        cx = mx + d * px
        cy = my + d * py
        
        # Start and end angles
        start_angle = math.atan2(y1 - cy, x1 - cx)
        end_angle = math.atan2(y2 - cy, x2 - cx)
        
        # Generate arc points
        points = [(x1, y1)]
        for i in range(1, segments):
            t = i / segments
            a = start_angle + t * angle
            x = cx + radius * math.cos(a)
            y = cy + radius * math.sin(a)
            points.append((x, y))
        points.append((x2, y2))
        
        return points


def export_dxf(document: Document, filepath: str) -> None:
    """Export a Document to DXF format."""
    dwg = ezdxf.new('R2010')
    modelspace = dwg.modelspace()
    
    for layer in document.layers:
        # Create DXF layer
        dwg.layers.add(name=layer.name, color=1)
        
        for shape in layer.shapes:
            paths = shape.get_paths()
            for path_points in paths:
                if len(path_points) < 2:
                    continue
                
                # Create polyline
                points = [(p.x, p.y) for p in path_points]
                modelspace.add_lwpolyline(
                    points,
                    dxfattribs={'layer': layer.name}
                )
    
    dwg.saveas(filepath)
```

---

*Continued in Part 2: [DEVELOPMENT_GUIDE_PART2.md](DEVELOPMENT_GUIDE_PART2.md)*

