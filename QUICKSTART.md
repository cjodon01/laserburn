# LaserBurn Quick Start Guide

## Installation

1. **Install Python 3.10+**
   - Download from https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Installation**
   ```bash
   python test_app.py
   ```
   All tests should pass.

## Running the Application

### Option 1: Using the launcher script
```bash
python run_laserburn.py
```

### Option 2: Direct Python module
```bash
python -m src.main
```

## Basic Usage

### Creating Shapes

1. **Select a drawing tool:**
   - Press `R` for Rectangle
   - Press `E` for Ellipse
   - Press `V` for Select tool

2. **Draw a shape:**
   - Click and drag on the canvas to create a rectangle or ellipse
   - Release to finish the shape

3. **Select and delete:**
   - Click on a shape to select it
   - Press `Delete` to remove selected shapes
   - Press `Ctrl+A` to select all shapes

### Importing Files

1. **Import SVG:**
   - Go to `File > Import...`
   - Select an SVG file
   - The shapes will be added to your document
   - Supports all SVG path commands, transforms, and basic shapes

2. **Import Images:**
   - Go to `File > Import...`
   - Select an image file (PNG, JPG, GIF, BMP)
   - Configure dithering settings in the image settings dialog
   - Adjust brightness, contrast, DPI, and dithering method
   - Preview the result before applying

3. **Open Project:**
   - Go to `File > Open...`
   - Select a `.lbrn` project file
   - All layers, shapes, and settings will be restored

### Working with Layers

1. **Create/Manage Layers:**
   - Use the Layers panel on the right side
   - Click "+" to add a new layer
   - Click the eye icon to toggle visibility
   - Right-click for layer options (rename, delete, etc.)

2. **Layer Settings:**
   - Select a layer to configure its laser settings
   - Set power, speed, passes, and operation type
   - Enable fill patterns for filled shapes

### Laser Settings

1. **Configure Laser Settings:**
   - Select a shape or layer
   - Use the Properties panel or Laser panel
   - Set power (0-100%), speed (mm/s), and passes
   - Choose operation type: Cut, Engrave, or Fill

2. **Fill Patterns:**
   - Enable fill in laser settings
   - Choose pattern: Horizontal, Vertical, Crosshatch, or Diagonal
   - Set line interval (spacing between lines)
   - Fill patterns use optimized bidirectional scanning for performance

### Connecting to Laser

1. **Connect to GRBL Controller:**
   - Go to `Laser > Connect...`
   - Select your serial port
   - Set baud rate (typically 115200)
   - Click Connect
   - Work area and max power are auto-detected

2. **Run a Job:**
   - Create or open your design
   - Configure laser settings for each layer
   - Go to `Laser > Start Job`
   - Monitor progress in the console
   - Use Pause/Resume/Stop as needed

### Exporting G-Code

1. **Export to G-Code:**
   - Go to `File > Export G-Code...`
   - Choose a location and filename
   - Configure job origin and start position
   - The G-code file will be generated with optimizations:
     - Path optimization (reduced travel time)
     - Bidirectional scanning for fill patterns
     - Intelligent move filtering

### View Controls

- **Zoom:** Use mouse wheel or `Ctrl +` / `Ctrl -`
- **Pan:** Hold `Shift` and drag, or use middle mouse button
- **Fit to view:** Press `Ctrl+0`

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New Document | `Ctrl+N` |
| Open File | `Ctrl+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Import | `Ctrl+I` |
| Export G-Code | `Ctrl+E` |
| Select Tool | `V` |
| Rectangle Tool | `R` |
| Ellipse Tool | `E` |
| Line Tool | `L` |
| Polygon Tool | `P` |
| Pen Tool | `N` |
| Text Tool | `T` |
| Delete | `Delete` |
| Select All | `Ctrl+A` |
| Zoom In | `Ctrl++` or `Ctrl+=` |
| Zoom Out | `Ctrl+-` |
| Fit to View | `Ctrl+0` |
| Rotate 90° | `R` (when shape selected) |
| Mirror Horizontal | `H` (when shape selected) |
| Mirror Vertical | `V` (when shape selected) |

## Troubleshooting

### Application won't start
- Make sure PyQt6 is installed: `pip install PyQt6`
- Check Python version: `python --version` (should be 3.10+)

### Import errors
- Run `pip install -r requirements.txt` again
- Make sure you're in the project root directory

### Shapes not appearing
- Check that a layer is selected in the Layers panel
- Make sure the layer is visible (eye icon)

## Advanced Features

### Cylinder Engraving
- Go to `Edit > Cylinder Engraving...`
- Configure cylinder diameter and material thickness
- Preview the warped design
- Power compensation is automatically applied during engraving

### Image Dithering
- Import an image and open the image settings dialog
- Choose from multiple dithering algorithms:
  - Floyd-Steinberg (recommended for photos)
  - Jarvis-Judice-Ninke
  - Stucki
  - Atkinson
  - Bayer (2x2, 4x4, 8x8)
  - Threshold (no dithering)
- Adjust brightness and contrast
- Set DPI for engraving resolution
- Preview the result before applying

### Fill Patterns
- Enable fill in laser settings for any shape
- Choose pattern type and spacing
- Fill patterns automatically use bidirectional scanning for optimal performance
- Supports complex paths with holes (even-odd fill rule)

## Next Steps

- Read the full documentation in `DEVELOPMENT_GUIDE.md`
- Check `BUILD_STATUS.md` for feature completion status
- Read `docs/CYLINDER_ENGRAVING.md` for cylinder engraving details
- Report issues on GitHub

Enjoy using LaserBurn!

