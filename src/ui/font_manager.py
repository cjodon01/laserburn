"""
Font Manager for LaserBurn

Manages bundled fonts and provides utilities for font discovery and loading.
"""

from PyQt6.QtGui import QFontDatabase
from pathlib import Path
from typing import List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class FontManager:
    """
    Manages bundled and custom fonts for LaserBurn.
    
    Features:
    - Loads bundled fonts from resources/fonts directory
    - Allows loading custom fonts at runtime
    - Provides font discovery and categorization
    """
    
    def __init__(self):
        """Initialize the font manager."""
        self.font_db = QFontDatabase()
        self.bundled_fonts: List[str] = []
        self.custom_fonts: List[str] = []
        self._loaded_font_ids: List[int] = []
    
    def load_bundled_fonts(self) -> int:
        """
        Load fonts from resources/fonts directory.
        
        Returns:
            Number of fonts successfully loaded
        """
        # Try to find resources/fonts directory relative to project root
        # This works whether running from source or installed
        project_root = Path(__file__).parent.parent.parent
        fonts_dir = project_root / "resources" / "fonts"
        
        # Also try relative to src directory (for development)
        if not fonts_dir.exists():
            fonts_dir = Path(__file__).parent.parent / "resources" / "fonts"
        
        if not fonts_dir.exists():
            logger.info(f"Fonts directory not found at {fonts_dir}. Skipping bundled fonts.")
            return 0
        
        loaded_count = 0
        
        # Load TTF fonts
        for font_file in fonts_dir.glob("*.ttf"):
            if self._load_font_file(str(font_file)):
                loaded_count += 1
        
        # Load OTF fonts
        for font_file in fonts_dir.glob("*.otf"):
            if self._load_font_file(str(font_file)):
                loaded_count += 1
        
        logger.info(f"Loaded {loaded_count} bundled fonts from {fonts_dir}")
        return loaded_count
    
    def _load_font_file(self, font_path: str) -> bool:
        """
        Load a single font file.
        
        Args:
            font_path: Path to font file (.ttf or .otf)
        
        Returns:
            True if font loaded successfully
        """
        try:
            font_id = self.font_db.addApplicationFont(font_path)
            if font_id != -1:
                families = self.font_db.applicationFontFamilies(font_id)
                self._loaded_font_ids.append(font_id)
                
                # Track bundled vs custom fonts
                if "resources" in font_path or "bundled" in font_path.lower():
                    self.bundled_fonts.extend(families)
                else:
                    self.custom_fonts.extend(families)
                
                logger.debug(f"Loaded font: {families} from {font_path}")
                return True
            else:
                logger.warning(f"Failed to load font from {font_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading font from {font_path}: {e}")
            return False
    
    def load_custom_font(self, font_path: str) -> bool:
        """
        Load a custom font file at runtime.
        
        Args:
            font_path: Path to font file
        
        Returns:
            True if font loaded successfully
        """
        return self._load_font_file(font_path)
    
    def get_all_fonts(self) -> List[str]:
        """
        Get all available fonts (system + bundled + custom).
        
        Returns:
            Sorted list of font family names
        """
        system_fonts = self.font_db.families()
        all_fonts = set(system_fonts) | set(self.bundled_fonts) | set(self.custom_fonts)
        return sorted(all_fonts)
    
    def get_bundled_fonts(self) -> List[str]:
        """Get list of bundled font families."""
        return sorted(set(self.bundled_fonts))
    
    def get_custom_fonts(self) -> List[str]:
        """Get list of custom-loaded font families."""
        return sorted(set(self.custom_fonts))
    
    def get_system_fonts(self) -> List[str]:
        """Get list of system font families."""
        all_fonts = set(self.font_db.families())
        bundled_set = set(self.bundled_fonts)
        custom_set = set(self.custom_fonts)
        system_fonts = all_fonts - bundled_set - custom_set
        return sorted(system_fonts)
    
    def is_font_available(self, font_family: str) -> bool:
        """
        Check if a font family is available.
        
        Args:
            font_family: Font family name to check
        
        Returns:
            True if font is available
        """
        return self.font_db.hasFamily(font_family)
    
    def get_font_styles(self, font_family: str) -> List[str]:
        """
        Get available styles for a font family.
        
        Args:
            font_family: Font family name
        
        Returns:
            List of style names (e.g., ["Regular", "Bold", "Italic"])
        """
        if not self.is_font_available(font_family):
            return []
        return self.font_db.styles(font_family)
    
    def categorize_font(self, font_family: str) -> str:
        """
        Categorize a font into a basic category.
        
        Args:
            font_family: Font family name
        
        Returns:
            Category name: "Sans-Serif", "Serif", "Monospace", "Script", "Display", or "Unknown"
        """
        font_lower = font_family.lower()
        
        # Monospace detection
        if any(keyword in font_lower for keyword in ['mono', 'code', 'console', 'courier']):
            return "Monospace"
        
        # Script/Handwriting detection
        if any(keyword in font_lower for keyword in ['script', 'handwriting', 'brush', 'calligraphy', 'cursive']):
            return "Script"
        
        # Display/Decorative detection
        if any(keyword in font_lower for keyword in ['display', 'decorative', 'ornamental', 'black', 'heavy']):
            return "Display"
        
        # Serif detection (common serif fonts)
        serif_keywords = ['serif', 'times', 'georgia', 'garamond', 'baskerville', 'caslon', 'minion']
        if any(keyword in font_lower for keyword in serif_keywords):
            return "Serif"
        
        # Default to Sans-Serif (most common)
        return "Sans-Serif"
    
    def get_fonts_by_category(self, category: str) -> List[str]:
        """
        Get all fonts in a specific category.
        
        Args:
            category: Category name
        
        Returns:
            List of font family names in that category
        """
        all_fonts = self.get_all_fonts()
        return [font for font in all_fonts if self.categorize_font(font) == category]
    
    def search_fonts(self, query: str) -> List[str]:
        """
        Search fonts by name.
        
        Args:
            query: Search query (case-insensitive)
        
        Returns:
            List of matching font family names
        """
        query_lower = query.lower()
        all_fonts = self.get_all_fonts()
        return [font for font in all_fonts if query_lower in font.lower()]


# Global font manager instance
_font_manager: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    """
    Get the global font manager instance.
    
    Returns:
        FontManager instance
    """
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
        # Auto-load bundled fonts on first access
        _font_manager.load_bundled_fonts()
    return _font_manager
