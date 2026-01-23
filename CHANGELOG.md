# Changelog

All notable changes to LaserBurn will be documented in this file.

## [Unreleased] - 2026-01-13

### Added
- **Bidirectional scanning optimization** for SVG fill patterns and image engraving
  - Alternates left-to-right and right-to-left on each scanline
  - Eliminates unnecessary returns to start of each line
  - Significantly reduces engraving time for wide designs
  - Maintains full functionality while improving performance
- G-code optimization improvements for better efficiency and compatibility
  - Changed white space handling from G0 (rapid moves) to G1 S0 (feed rate with laser off) to match LightBurn's approach
  - Added minimum move threshold (0.05mm) to automatically skip tiny moves and reduce file size
  - Automatic filtering of very small runs (< 0.05mm) for improved G-code efficiency

### Changed
- Fill pattern processing now uses bidirectional scanning for optimal performance
- G-code generation now uses G1 S0 for white space moves instead of G0 for better controller compatibility
- Very small moves (< 0.05mm) are now automatically skipped to reduce file size without significant quality impact

### Technical
- Optimized `_process_fill_patterns_optimized()` to use true bidirectional scanning
- Improved G-code file size and efficiency through intelligent move filtering
- Better compatibility with various GRBL controllers by matching LightBurn's white space handling approach

## [0.1.0] - 2026-01-07

### Added
- Core shape system (Rectangle, Ellipse, Path)
- Document and Layer management
- SVG file import/export
- G-code generation for GRBL-compatible controllers
- Main application window with menus and toolbars
- Drawing canvas with zoom, pan, and selection
- Layer management panel
- Basic drawing tools (Rectangle, Ellipse)
- Shape selection and deletion
- G-code export functionality

### Technical
- Complete project structure
- Comprehensive development documentation (3 parts)
- Test suite
- Build scripts
- Setup.py for package installation

### Known Limitations
- GRBL controller communication not yet implemented
- Image processing (dithering, tracing) not yet implemented
- Material library not yet implemented
- Camera integration not yet implemented
- Advanced drawing tools (polygon, text, pen) not yet implemented
- Boolean operations not yet implemented
- DXF import/export not yet implemented

### Next Steps
- Implement GRBL controller for direct laser communication
- Add image processing capabilities
- Implement material library
- Add more drawing tools
- Implement boolean operations
- Add DXF support

