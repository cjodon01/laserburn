# Font Library Review and Expansion Plan

## Current Implementation Review

### Text/Lettering System Overview

The LaserBurn text system is well-architected with the following components:

1. **Core Text Shape** (`src/core/shapes.py`)
   - `Text` class extends `Shape`
   - Stores text content, font family, size, bold, italic
   - Converts text to vector paths using Qt's `QPainterPath.addText()`
   - Caches paths for performance

2. **Graphics Layer** (`src/graphics/text_item.py`)
   - `EditableTextItem` - PowerPoint-style inline editing
   - Real-time editing on canvas
   - Converts to `Text` shape when finished

3. **UI Components**
   - `TextDialog` - Uses `QFontComboBox` (shows ALL system fonts)
   - `PropertiesPanel` - Uses hardcoded list (only 7 fonts)
   - `TextTool` - Creates editable text items

### Current Font Limitations

**Issues Identified:**

1. **Inconsistent Font Selection**
   - `TextDialog` uses `QFontComboBox` (all system fonts available)
   - `PropertiesPanel` uses hardcoded list (only 7 fonts)
   - Users can't access all fonts from properties panel

2. **No Bundled Fonts**
   - Relies entirely on system fonts
   - No guarantee fonts exist across platforms
   - Development guide mentions `resources/fonts/` but it doesn't exist

3. **Limited Font Discovery**
   - No font preview
   - No font categories (serif, sans-serif, decorative, etc.)
   - No font search/filtering

4. **No Font Management**
   - Can't add custom fonts
   - Can't organize favorite fonts
   - No font metadata (license, designer, etc.)

## Expansion Recommendations

### Phase 1: Fix Inconsistency (Quick Win)

**Problem:** PropertiesPanel has hardcoded font list while TextDialog uses QFontComboBox

**Solution:** Replace hardcoded list with QFontComboBox in PropertiesPanel

**Benefits:**
- Immediate access to all system fonts
- Consistent UI across dialogs
- No code duplication

**Implementation:**
```python
# In properties_panel.py, replace:
self._font_family_combo = QComboBox()
self._font_family_combo.addItems([...])  # Remove hardcoded list

# With:
from PyQt6.QtWidgets import QFontComboBox
self._font_family_combo = QFontComboBox()
```

### Phase 2: Add Bundled Fonts (Medium Effort)

**Problem:** No guaranteed fonts across platforms

**Solution:** Bundle open-source fonts with the application

**Recommended Fonts to Bundle:**

1. **Sans-Serif (General Purpose)**
   - Roboto (Google Fonts) - Modern, clean
   - Open Sans (Google Fonts) - Highly readable
   - Source Sans Pro (Adobe) - Professional

2. **Serif (Traditional)**
   - Merriweather (Google Fonts) - Readable serif
   - Lora (Google Fonts) - Elegant serif

3. **Monospace (Technical)**
   - Source Code Pro (Adobe) - Programming font
   - Fira Code (Mozilla) - With ligatures

4. **Decorative/Display (Laser-Friendly)**
   - Bebas Neue (Google Fonts) - Bold, geometric
   - Oswald (Google Fonts) - Condensed, strong
   - Raleway (Google Fonts) - Elegant sans-serif

5. **Handwriting/Script**
   - Dancing Script (Google Fonts) - Casual script
   - Pacifico (Google Fonts) - Brush script

**Implementation Steps:**

1. Create `resources/fonts/` directory
2. Download fonts (ensure open-source licenses)
3. Create font loader utility:
```python
# src/ui/font_manager.py
from PyQt6.QtGui import QFontDatabase
from pathlib import Path

class FontManager:
    """Manages bundled and custom fonts."""
    
    def __init__(self):
        self.font_db = QFontDatabase()
        self.bundled_fonts = []
        self.custom_fonts = []
    
    def load_bundled_fonts(self):
        """Load fonts from resources/fonts directory."""
        fonts_dir = Path(__file__).parent.parent.parent / "resources" / "fonts"
        
        if not fonts_dir.exists():
            return
        
        for font_file in fonts_dir.glob("*.ttf"):
            font_id = self.font_db.addApplicationFont(str(font_file))
            if font_id != -1:
                families = self.font_db.applicationFontFamilies(font_id)
                self.bundled_fonts.extend(families)
    
    def get_all_fonts(self):
        """Get all available fonts (system + bundled + custom)."""
        system_fonts = self.font_db.families()
        return sorted(set(system_fonts + self.bundled_fonts + self.custom_fonts))
    
    def load_custom_font(self, font_path: str) -> bool:
        """Load a custom font file."""
        font_id = self.font_db.addApplicationFont(font_path)
        if font_id != -1:
            families = self.font_db.applicationFontFamilies(font_id)
            self.custom_fonts.extend(families)
            return True
        return False
```

4. Initialize in main application:
```python
# In src/main.py
from src.ui.font_manager import FontManager

font_manager = FontManager()
font_manager.load_bundled_fonts()
```

### Phase 3: Enhanced Font Selection UI (Advanced)

**Features:**
- Font preview
- Font categories (Serif, Sans-Serif, Monospace, Display, Script)
- Search/filter
- Favorite fonts
- Recently used fonts

**Implementation:**
```python
# src/ui/widgets/font_selector.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QLineEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QFont, QFontDatabase, QPainter, QPixmap
from PyQt6.QtCore import Qt

class FontSelector(QWidget):
    """Enhanced font selector with preview and categories."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_db = QFontDatabase()
        self._setup_ui()
        self._load_fonts()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Search box
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search fonts...")
        self.search.textChanged.connect(self._filter_fonts)
        layout.addWidget(self.search)
        
        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "All", "Sans-Serif", "Serif", "Monospace", 
            "Display", "Script", "Handwriting"
        ])
        self.category_combo.currentTextChanged.connect(self._filter_fonts)
        layout.addWidget(self.category_combo)
        
        # Font list with preview
        self.font_list = QListWidget()
        self.font_list.currentItemChanged.connect(self._on_font_selected)
        layout.addWidget(self.font_list)
    
    def _load_fonts(self):
        """Load and categorize fonts."""
        all_fonts = self.font_db.families()
        
        for font_family in sorted(all_fonts):
            item = QListWidgetItem(font_family)
            
            # Create preview
            preview = self._create_preview(font_family)
            item.setIcon(preview)
            
            # Categorize
            category = self._categorize_font(font_family)
            item.setData(Qt.ItemDataRole.UserRole, category)
            
            self.font_list.addItem(item)
    
    def _create_preview(self, font_family: str) -> QPixmap:
        """Create a small preview of the font."""
        pixmap = QPixmap(200, 30)
        pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(pixmap)
        font = QFont(font_family, 16)
        painter.setFont(font)
        painter.drawText(10, 20, "AaBbCc 123")
        painter.end()
        
        return pixmap
    
    def _categorize_font(self, font_family: str) -> str:
        """Categorize font based on name and characteristics."""
        font_family_lower = font_family.lower()
        
        # Check font database for style hints
        styles = self.font_db.styles(font_family)
        
        # Simple heuristics (can be improved)
        if any(x in font_family_lower for x in ['mono', 'code', 'console']):
            return "Monospace"
        elif any(x in font_family_lower for x in ['script', 'handwriting', 'brush']):
            return "Script"
        elif any(x in font_family_lower for x in ['display', 'bold', 'black']):
            return "Display"
        elif self.font_db.hasFamily(font_family):
            # Check if it's serif or sans-serif
            # This is simplified - real implementation would check font metrics
            return "Sans-Serif"  # Default
        return "Sans-Serif"
    
    def _filter_fonts(self):
        """Filter fonts based on search and category."""
        search_text = self.search.text().lower()
        category = self.category_combo.currentText()
        
        for i in range(self.font_list.count()):
            item = self.font_list.item(i)
            font_name = item.text().lower()
            font_category = item.data(Qt.ItemDataRole.UserRole)
            
            # Check search match
            search_match = search_text in font_name if search_text else True
            
            # Check category match
            category_match = (category == "All" or 
                            font_category == category)
            
            item.setHidden(not (search_match and category_match))
    
    def _on_font_selected(self, item):
        """Handle font selection."""
        if item:
            self.font_selected.emit(item.text())
```

### Phase 4: Font Management Features (Future)

**Additional Features:**
- Import custom fonts (drag & drop)
- Font favorites/bookmarks
- Font collections (e.g., "Laser-Friendly Fonts")
- Font metadata display (license, designer, etc.)
- Font preview with custom text
- Font comparison view

## Implementation Priority

### High Priority (Do First)
1. ✅ Fix PropertiesPanel to use QFontComboBox (5 minutes)
2. ✅ Create resources/fonts directory structure (10 minutes)
3. ✅ Implement FontManager class (30 minutes)
4. ✅ Bundle 5-10 essential open-source fonts (1 hour)

### Medium Priority (Next Sprint)
5. Enhanced font selector with preview
6. Font categories
7. Font search/filter

### Low Priority (Future)
8. Font favorites
9. Custom font import
10. Font collections

## Technical Considerations

### Font Licensing
- **Critical:** Only bundle fonts with permissive licenses
- Recommended licenses: SIL Open Font License (OFL), Apache 2.0, MIT
- Google Fonts are excellent source (all open-source)
- Always include license files with fonts

### Font File Formats
- **TTF (TrueType)** - Most compatible, recommended
- **OTF (OpenType)** - Also supported by Qt
- **WOFF/WOFF2** - Web fonts, not needed for desktop

### Performance
- Font loading is fast (Qt caches internally)
- Font preview generation should be lazy (on-demand)
- Consider caching preview images

### Cross-Platform
- System fonts vary by OS
- Bundled fonts ensure consistency
- Test on Windows, macOS, Linux

## Example: Quick Fix Implementation

Here's the immediate fix for the PropertiesPanel inconsistency:

```python
# In src/ui/panels/properties_panel.py

# Replace line 116-117:
from PyQt6.QtWidgets import QFontComboBox  # Add import

# Replace:
self._font_family_combo = QComboBox()
self._font_family_combo.addItems(["Arial", "Times New Roman", ...])

# With:
self._font_family_combo = QFontComboBox()
# QFontComboBox automatically populates with all system fonts
```

## Conclusion

**Yes, we can definitely expand the font library!** The current implementation is solid but has room for improvement:

1. **Immediate:** Fix inconsistency (use QFontComboBox everywhere)
2. **Short-term:** Bundle essential open-source fonts
3. **Long-term:** Add font management features

The architecture supports expansion well - the `Text` shape class is font-agnostic and works with any font Qt can load.
