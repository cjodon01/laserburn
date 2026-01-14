# Bundled Fonts Directory

This directory contains fonts bundled with LaserBurn to ensure consistent font availability across platforms.

## Adding Fonts

1. **Download fonts** with open-source licenses (SIL OFL, Apache 2.0, MIT)
2. **Place font files** (.ttf or .otf) in this directory
3. **Include license files** - Keep the license file (OFL.txt, LICENSE, etc.) with the font
4. **Restart application** - Fonts are loaded automatically on startup

## Recommended Font Sources

- **Google Fonts** (https://fonts.google.com) - All fonts are open-source
- **Font Squirrel** (https://www.fontsquirrel.com) - Filter by "Free for Commercial Use"
- **Adobe Fonts** - Some fonts available under open licenses

## Recommended Fonts for Laser Engraving

### Sans-Serif (General Purpose)
- **Roboto** - Modern, clean, highly readable
- **Open Sans** - Excellent readability at all sizes
- **Source Sans Pro** - Professional, designed for UI

### Serif (Traditional)
- **Merriweather** - Readable serif, good for body text
- **Lora** - Elegant serif with good character

### Monospace (Technical/Code)
- **Source Code Pro** - Programming font, excellent for technical text
- **Fira Code** - Programming font with ligatures

### Display (Bold, Eye-Catching)
- **Bebas Neue** - Bold, geometric, perfect for headings
- **Oswald** - Condensed, strong presence
- **Raleway** - Elegant sans-serif, good for titles

### Script/Handwriting
- **Dancing Script** - Casual script font
- **Pacifico** - Brush script style

## License Requirements

**IMPORTANT:** Only include fonts with permissive licenses:
- ✅ SIL Open Font License (OFL)
- ✅ Apache License 2.0
- ✅ MIT License
- ✅ Public Domain

**DO NOT** include fonts with restrictive licenses or unclear licensing.

## Font File Naming

Use descriptive names that include the font family:
- `Roboto-Regular.ttf`
- `BebasNeue-Regular.ttf`
- `SourceCodePro-Regular.ttf`

## Testing

After adding fonts:
1. Restart LaserBurn
2. Open text tool or properties panel
3. Check font dropdown - new fonts should appear
4. Test rendering - create text with new font
5. Verify G-code generation works correctly

## Current Fonts

*(This section will be updated as fonts are added)*

Currently, LaserBurn uses system fonts. Bundled fonts will be listed here once added.
