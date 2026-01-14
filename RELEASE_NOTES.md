# LaserBurn v0.1.0 - Release Notes

## 🎉 Initial Release

LaserBurn is now ready for use! This is the first functional release with core features implemented.

## 🔄 Recent Updates (2026-01-13)

### G-Code Optimization Improvements
- **Better Controller Compatibility**: Changed white space handling from G0 (rapid moves) to G1 S0 (feed rate with laser off) to match LightBurn's approach, ensuring better compatibility with various GRBL controllers
- **Reduced File Size**: Added intelligent move filtering that automatically skips very small moves (< 0.05mm), significantly reducing G-code file size without noticeable quality impact
- **Improved Efficiency**: Very small runs are now automatically filtered out, resulting in faster processing and smaller file sizes

## ✅ What's Working

### Core Features
- ✅ **Shape Creation**: Create rectangles and ellipses by drawing on the canvas
- ✅ **Shape Selection**: Click to select shapes, delete with Delete key
- ✅ **SVG Import**: Import SVG files with basic shape support
- ✅ **G-Code Export**: Export designs to G-code for laser cutters
- ✅ **Layer Management**: Organize shapes into layers
- ✅ **Zoom & Pan**: Navigate your designs easily
- ✅ **Document Management**: Create, save, and load projects

### User Interface
- ✅ Modern, clean interface with dockable panels
- ✅ Toolbars for quick access to tools
- ✅ Menu system with keyboard shortcuts
- ✅ Status bar for feedback
- ✅ Layers panel for organization

## 🚀 Getting Started

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python run_laserburn.py
   ```

3. **Create your first design:**
   - Press `R` to select Rectangle tool
   - Click and drag on canvas to draw
   - Press `E` for Ellipse tool
   - Export with `Ctrl+E` to generate G-code

## 📋 Quick Reference

### Drawing Tools
- `V` - Select tool
- `R` - Rectangle tool
- `E` - Ellipse tool

### File Operations
- `Ctrl+N` - New document
- `Ctrl+O` - Open file
- `Ctrl+S` - Save
- `Ctrl+I` - Import SVG
- `Ctrl+E` - Export G-code

### View Controls
- Mouse wheel - Zoom
- `Shift + Drag` - Pan
- `Ctrl+0` - Fit to view
- `Ctrl++` - Zoom in
- `Ctrl+-` - Zoom out

## 🔧 Technical Details

### Supported File Formats
- **Import**: SVG (basic shapes and paths)
- **Export**: G-code (.gcode, .nc, .ngc), SVG

### G-Code Compatibility
- GRBL 1.1+ compatible
- Standard G-code commands (G0, G1, M3, M4, M5)
- Configurable power and speed settings
- **Optimized output**: Uses G1 S0 for white space (matching LightBurn) for better controller compatibility
- **Intelligent filtering**: Automatically skips tiny moves (< 0.05mm) to reduce file size

### System Requirements
- Python 3.10 or higher
- Windows 10/11, macOS 10.14+, or Linux
- 4GB RAM minimum
- 100MB disk space

## 📚 Documentation

- **Quick Start**: See `QUICKSTART.md`
- **Development Guide**: See `DEVELOPMENT_GUIDE.md` (3 parts)
- **Build Status**: See `BUILD_STATUS.md`
- **Deployment**: See `DEPLOYMENT.md`

## 🐛 Known Issues

- GRBL controller communication not yet implemented (G-code export works)
- Some advanced SVG features may not import correctly
- No undo/redo functionality yet
- Limited to basic shapes (rectangle, ellipse, paths)

## 🔮 Coming Soon

- Direct laser controller communication
- Image processing and dithering
- Material library with presets
- More drawing tools (polygon, text, pen)
- Boolean operations
- DXF file support
- Camera integration

## 🙏 Acknowledgments

Built with:
- PyQt6 for the user interface
- Python for the core engine
- Open-source laser cutting community

## 📞 Support

For issues, questions, or contributions:
- Check the documentation files
- Review `BUILD_STATUS.md` for feature status
- Test your setup with `python test_app.py`

---

**Enjoy creating with LaserBurn!** 🎨✨

