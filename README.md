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

## 🎯 Target Features

### Core Features (LightBurn Parity)

- **File Support**
  - Import: SVG, DXF, AI, PDF, PLT, PNG, JPG, GIF, BMP
  - Export: SVG, DXF, G-Code, native project format

- **Design Tools**
  - Shape primitives: Line, Rectangle, Ellipse, Polygon, Star, Text
  - Path editing: Node manipulation, bezier curves
  - Boolean operations: Union, Difference, Intersection, XOR
  - Transformations: Scale, Rotate, Mirror, Align

- **Laser Settings**
  - Layer-based power/speed control
  - Multiple operation types: Cut, Engrave, Fill
  - Multi-pass support
  - Air assist control
  - Z-offset for focus

- **Controller Support**
  - GRBL (1.1+)
  - Marlin
  - Smoothieware
  - Ruida (DSP)
  - Trocen
  - TopWisdom

- **Image Processing**
  - Multiple dithering algorithms (Floyd-Steinberg, Jarvis, Atkinson, Bayer, etc.)
  - Image tracing (vectorization)
  - Brightness/contrast adjustment
  - Variable DPI engraving

- **Optimization**
  - Path optimization (TSP approximation)
  - Cut order optimization
  - Start point optimization for closed paths

- **Additional Features**
  - Material library with presets
  - Camera alignment integration
  - Job preview and simulation
  - Time estimation

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

## 📖 Development Guide Overview

### Phase 1: Foundation (Weeks 1-4)
- Set up project structure
- Implement core data structures (Point, Shape, Path, Layer, Document)
- Basic serialization/deserialization

### Phase 2: File I/O (Weeks 5-8)
- SVG parser with full path command support
- DXF parser using ezdxf
- Image import and basic processing

### Phase 3: Graphics Engine (Weeks 9-12)
- Qt Graphics View canvas implementation
- Drawing tools (line, rectangle, ellipse, polygon)
- Selection and transformation tools
- Undo/redo system

### Phase 4: Laser Control (Weeks 13-16)
- G-code generator with optimization
- GRBL controller implementation
- Serial communication handling
- Job management (start, pause, stop)

### Phase 5: Image Processing (Weeks 17-20)
- Dithering algorithms implementation
- Image tracing (potrace integration)
- Scanline generation for engraving

### Phase 6: Polish (Weeks 21-24)
- Material library with SQLite
- Camera integration
- UI refinement
- Testing and documentation
- Packaging and distribution

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

