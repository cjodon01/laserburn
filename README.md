# LaserBurn

**Open-Source Laser Engraving & Cutting Software**

A comprehensive laser engraving software designed to achieve feature parity with LightBurn. Built with Python and PyQt6 for cross-platform compatibility.

---

## 📋 Documentation

This repository contains a comprehensive development guide split into three parts:

| Document | Contents |
|----------|----------|
| [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Project overview, setup, architecture, core shapes, file parsing (SVG/DXF) |
| [DEVELOPMENT_GUIDE_PART2.md](DEVELOPMENT_GUIDE_PART2.md) | Boolean operations, path optimization, G-code generation, laser controller communication, image processing (dithering, tracing) |
| [DEVELOPMENT_GUIDE_PART3.md](DEVELOPMENT_GUIDE_PART3.md) | User interface, material library, camera integration, testing, deployment |

---

## 🎯 Features

### ✅ Implemented Features

- **File Support**
  - ✅ Import: SVG (full path command support), PNG, JPG, GIF, BMP
  - ✅ Export: SVG, G-Code, native project format (.lbrn)
  - ✅ Native project file format with complete serialization

- **Design Tools**
  - ✅ Shape primitives: Line, Rectangle, Ellipse, Polygon, Text
  - ✅ Freehand drawing (Pen tool)
  - ✅ Text tool with font selection
  - ✅ Transformations: Scale, Rotate, Mirror
  - ✅ Interactive selection handles for resizing and rotation
  - ✅ Path support with bezier curves

- **Laser Settings**
  - ✅ Layer-based power/speed control
  - ✅ Multiple operation types: Cut, Engrave, Fill
  - ✅ Fill patterns: Horizontal, Vertical, Crosshatch, Diagonal
  - ✅ Multi-pass support
  - ✅ Air assist control
  - ✅ Z-offset for focus
  - ✅ Work area limits and validation

- **Controller Support**
  - ✅ GRBL (1.1+) - **Fully Operational**
    - Serial communication with flow control
    - Real-time status monitoring
    - Jog functionality
    - Home and set home position
    - Auto-detection of work area and max power ($30)
    - Job queue management

- **Image Processing**
  - ✅ Multiple dithering algorithms (Floyd-Steinberg, Jarvis-Judice-Ninke, Stucki, Atkinson, Bayer 2x2/4x4/8x8, Threshold)
  - ✅ Brightness/contrast adjustment
  - ✅ Image inversion
  - ✅ Variable DPI engraving
  - ✅ Transparency (alpha channel) support
  - ✅ Live preview with dithering applied

- **Optimization**
  - ✅ Path optimization (TSP approximation)
  - ✅ Cut order optimization
  - ✅ Start point optimization for closed paths
  - ✅ **Bidirectional scanning** for fill patterns and image engraving (optimized performance)
  - ✅ Intelligent move filtering (skips tiny moves < 0.05mm)

- **Special Features**
  - ✅ Cylinder engraving (non-rotary) with automatic power compensation
  - ✅ G-code preview widget
  - ✅ Frame function (outline design perimeter)
  - ✅ Job time estimation

### 🚧 Planned Features

- **File Support**
  - DXF import/export
  - AI, PDF, PLT support

- **Design Tools**
  - Node editing
  - Boolean operations (Union, Difference, Intersection, XOR)
  - Path offsetting
  - Undo/redo system
  - Copy/paste functionality

- **Controller Support**
  - Marlin, Smoothieware, Ruida, Trocen, TopWisdom

- **Image Processing**
  - Image tracing (vectorization)

- **Additional Features**
  - Material library with presets
  - Camera alignment integration

---

## 🛠️ Technology Stack

```
Language:           Python 3.10+
GUI Framework:      PyQt6
Graphics:           Qt Graphics View Framework
Image Processing:   OpenCV, Pillow, NumPy
Vector Operations:  pyclipper (Clipper2)
Serial Comm:        pyserial
File Parsing:       Custom + ezdxf, svgpathtools
Database:           SQLite3
Testing:            pytest, pytest-qt
Packaging:          PyInstaller
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or later
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/laserburn.git
cd laserburn

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.main
```

### Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Code formatting
black src/ tests/

# Type checking
mypy src/

# Build executable
python scripts/build.py
```

---

## 📁 Project Structure

```
laserburn/
├── src/
│   ├── core/           # Document model, shapes, paths
│   ├── graphics/       # Canvas, drawing tools, selection
│   ├── io/             # File parsers (SVG, DXF, etc.)
│   ├── laser/          # G-code generation, controllers
│   ├── image/          # Dithering, tracing, adjustments
│   ├── ui/             # Main window, panels, dialogs
│   ├── materials/      # Material library database
│   ├── camera/         # Camera capture and calibration
│   └── main.py         # Entry point
├── resources/
│   ├── icons/          # UI icons
│   ├── fonts/          # Bundled fonts
│   └── styles/         # Qt stylesheets
├── tests/              # Test files
├── docs/               # Additional documentation
├── scripts/            # Build and utility scripts
├── requirements.txt    # Production dependencies
├── requirements-dev.txt # Development dependencies
└── README.md
```

---

## 📖 Current Status

### ✅ Completed Phases

**Phase 1: Foundation** ✅
- Project structure complete
- Core data structures implemented (Point, Shape, Path, Layer, Document)
- Complete serialization/deserialization

**Phase 2: File I/O** ✅
- SVG parser with full path command support (all commands: M, L, H, V, C, S, Q, T, A, Z)
- SVG transforms support (translate, rotate, scale, matrix, skew)
- Image import with dithering and processing
- Native project file format (.lbrn)

**Phase 3: Graphics Engine** ✅
- Qt Graphics View canvas implementation
- Drawing tools (line, rectangle, ellipse, polygon, pen, text)
- Selection and transformation tools (scale, rotate, mirror)
- Interactive selection handles

**Phase 4: Laser Control** ✅
- G-code generator with optimization
- GRBL controller implementation (fully operational)
- Serial communication with flow control
- Job management (start, pause, stop, queue)
- Path optimization (TSP approximation)
- **Bidirectional scanning optimization** for fill patterns

**Phase 5: Image Processing** ✅
- Multiple dithering algorithms implemented
- Brightness/contrast adjustment
- Scanline generation for engraving
- Cylinder engraving with power compensation

### 🚧 In Progress / Planned

**Phase 6: Advanced Features**
- Material library with SQLite
- Camera integration
- Image tracing (vectorization)
- Boolean operations
- Node editing
- Undo/redo system

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines (coming soon).

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for public APIs
- Add tests for new features

### Commit Messages

```
feat: Add new feature
fix: Fix bug
docs: Update documentation
test: Add or update tests
refactor: Code refactoring
style: Formatting changes
```

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- [LightBurn](https://lightburnsoftware.com/) - For setting the standard in laser software
- [GRBL](https://github.com/gnea/grbl) - Open-source CNC controller
- [Clipper2](https://github.com/AngusJohnson/Clipper2) - Polygon boolean operations
- [potrace](http://potrace.sourceforge.net/) - Bitmap tracing
- The open-source laser cutting community

---

## 📬 Contact

- Issues: Use GitHub Issues for bug reports and feature requests
- Discussions: GitHub Discussions for questions and ideas

