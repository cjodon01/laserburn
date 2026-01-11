"""
Build script for creating standalone executables with PyInstaller.
"""

import sys
import os
import subprocess

# Application info
APP_NAME = "LaserBurn"
VERSION = "0.1.0"
ENTRY_POINT = "src/main.py"

def build_executable():
    """Build executable using PyInstaller."""
    
    if not os.path.exists("requirements.txt"):
        print("Error: requirements.txt not found")
        return False
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyInstaller"])
    
    # Build options
    opts = [
        ENTRY_POINT,
        f'--name={APP_NAME}',
        '--windowed',  # No console window on Windows
        '--onedir',    # Create a folder with executable
        '--clean',
        '--noconfirm',
        
        # Add data files
        '--add-data=resources;resources' if sys.platform == 'win32' else '--add-data=resources:resources',
        
        # Hidden imports
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=src',
        '--hidden-import=src.core',
        '--hidden-import=src.ui',
        '--hidden-import=src.io',
        '--hidden-import=src.laser',
    ]
    
    # Platform-specific
    if sys.platform == 'win32':
        opts.append('--icon=NONE')  # Add icon path if available
    
    print(f"Building {APP_NAME} {VERSION}...")
    print(f"Command: pyinstaller {' '.join(opts)}")
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(opts)
        print(f"\n[SUCCESS] Build complete! Check 'dist/{APP_NAME}' folder")
        return True
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        return False


if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)

