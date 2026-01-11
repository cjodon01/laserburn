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

### Exporting G-Code

1. **Export to G-Code:**
   - Go to `File > Export G-Code...`
   - Choose a location and filename
   - The G-code file will be generated for your laser cutter

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
| Import | `Ctrl+I` |
| Export G-Code | `Ctrl+E` |
| Select Tool | `V` |
| Rectangle Tool | `R` |
| Ellipse Tool | `E` |
| Delete | `Delete` |
| Select All | `Ctrl+A` |
| Zoom In | `Ctrl++` |
| Zoom Out | `Ctrl+-` |
| Fit to View | `Ctrl+0` |

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

## Next Steps

- Read the full documentation in `DEVELOPMENT_GUIDE.md`
- Check `BUILD_STATUS.md` for feature completion status
- Report issues on GitHub

Enjoy using LaserBurn!

