# LaserBurn Deployment Guide

## Building Standalone Executable

### Prerequisites
- Python 3.10+
- All dependencies installed
- PyInstaller (will be installed automatically)

### Build Steps

1. **Install build dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run the build script:**
   ```bash
   python scripts/build.py
   ```

3. **Find the executable:**
   - Windows: `dist/LaserBurn/LaserBurn.exe`
   - The executable and all dependencies will be in the `dist/LaserBurn` folder

### Manual Build

If you prefer to build manually:

```bash
pyinstaller --name=LaserBurn --windowed --onedir --clean \
  --add-data=resources;resources \
  --hidden-import=PyQt6.QtCore \
  --hidden-import=PyQt6.QtGui \
  --hidden-import=PyQt6.QtWidgets \
  src/main.py
```

## Distribution

### Windows

1. **Create installer (optional):**
   - Use NSIS, Inno Setup, or WiX
   - Include the entire `dist/LaserBurn` folder
   - Add uninstaller

2. **Zip distribution:**
   - Zip the `dist/LaserBurn` folder
   - Users can extract and run `LaserBurn.exe`

### Testing the Build

1. **Test on clean system:**
   - Copy `dist/LaserBurn` to a machine without Python
   - Run `LaserBurn.exe`
   - Verify all features work

## Version Information

Update version in:
- `src/__init__.py` - `__version__`
- `setup.py` - `version`
- `scripts/build.py` - `VERSION`

## Code Signing (Optional)

For Windows distribution, consider code signing:
```bash
signtool sign /f certificate.pfx /p password LaserBurn.exe
```

## Release Checklist

- [ ] All tests pass (`python test_app.py`)
- [ ] Application runs without errors
- [ ] Build executable successfully
- [ ] Test executable on clean system
- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Create release notes
- [ ] Tag git release
- [ ] Upload to distribution platform

