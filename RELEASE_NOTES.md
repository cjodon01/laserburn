# LaserBurn v0.1.0 - Release Notes

## 🎉 Initial Release

LaserBurn is now ready for use! This is the first functional release with core features implemented.

## 🔄 Recent Updates (2026-01-13)

### Performance Optimization: Bidirectional Scanning
- **Faster Engraving**: Implemented bidirectional scanning for SVG fill patterns and image engraving
  - Alternates left-to-right and right-to-left on each scanline
  - Eliminates unnecessary returns to start of each line
  - Significantly reduces engraving time, especially for wide designs
  - Maintains full functionality while improving performance

### G-Code Optimization Improvements
- **Better Controller Compatibility**: Changed white space handling from G0 (rapid moves) to G1 S0 (feed rate with laser off) to match LightBurn's approach, ensuring better compatibility with various GRBL controllers
- **Reduced File Size**: Added intelligent move filtering that automatically skips very small moves (< 0.05mm), significantly reducing G-code file size without noticeable quality impact
- **Improved Efficiency**: Very small runs are now automatically filtered out, resulting in faster processing and smaller file sizes

## ✅ What's Working

### Core Features
- ✅ **Shape Creation**: Create rectangles, ellipses, lines, polygons, text, and freehand drawings
- ✅ **Shape Selection**: Click to select shapes, delete with Delete key, transform with handles
- ✅ **SVG Import**: Import SVG files with full path command support (all commands: M, L, H, V, C, S, Q, T, A, Z)
- ✅ **Image Import**: Import PNG, JPG, GIF, BMP with dithering and processing options
- ✅ **G-Code Export**: Export designs to G-code with path optimization and bidirectional scanning
- ✅ **Layer Management**: Organize shapes into layers with individual laser settings
- ✅ **Zoom & Pan**: Navigate your designs easily
- ✅ **Document Management**: Create, save, and load projects (.lbrn format)
- ✅ **Transform Tools**: Scale, rotate, and mirror shapes with interactive handles

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
- `L` - Line tool
- `P` - Polygon tool
- `N` - Pen tool (freehand)
- `T` - Text tool

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
- **Import**: SVG (full path command support), PNG, JPG, GIF, BMP, native project (.lbrn)
- **Export**: G-code (.gcode, .nc, .ngc), SVG, native project (.lbrn)

### G-Code Compatibility
- GRBL 1.1+ compatible (fully operational controller support)
- Standard G-code commands (G0, G1, M3, M4, M5)
- Configurable power and speed settings
- **Path optimization**: TSP approximation for reduced travel time
- **Bidirectional scanning**: Optimized fill patterns and image engraving
- **Optimized output**: Uses G1 S0 for white space (matching LightBurn) for better controller compatibility
- **Intelligent filtering**: Automatically skips tiny moves (< 0.05mm) to reduce file size
- **Fill patterns**: Horizontal, vertical, crosshatch, and diagonal with even-odd fill rule

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

## 🐛 Known Limitations

- No undo/redo functionality yet
- Node editing not yet implemented
- Boolean operations not yet implemented
- DXF import/export not yet implemented
- Image tracing (vectorization) not yet implemented
- Material library not yet implemented
- Camera integration not yet implemented

## 🔮 Coming Soon

- Undo/redo system
- Node editing for path manipulation
- Boolean operations (union, difference, intersection)
- DXF file support
- Image tracing (vectorization)
- Material library with presets
- Camera integration
- Additional controller support (Marlin, Smoothieware, Ruida, etc.)

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

