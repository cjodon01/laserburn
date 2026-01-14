#!/usr/bin/env python3
"""
Fix corrupted PyQt6 installation by manually removing it and reinstalling.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

def find_pyqt6_paths():
    """Find all PyQt6-related paths in site-packages."""
    import site
    site_packages = site.getsitepackages()
    
    pyqt6_paths = []
    for site_pkg in site_packages:
        pyqt6_dir = os.path.join(site_pkg, 'PyQt6')
        if os.path.exists(pyqt6_dir):
            pyqt6_paths.append(pyqt6_dir)
        
        # Also check for pyqt6 egg-info
        for item in os.listdir(site_pkg):
            if 'pyqt6' in item.lower() or 'PyQt6' in item:
                full_path = os.path.join(site_pkg, item)
                if os.path.isdir(full_path) or item.endswith('.dist-info'):
                    pyqt6_paths.append(full_path)
    
    return pyqt6_paths

def main():
    print("PyQt6 Fix Script")
    print("=" * 60)
    
    # Find PyQt6 installations
    print("\n1. Finding PyQt6 installations...")
    pyqt6_paths = find_pyqt6_paths()
    
    if not pyqt6_paths:
        print("   No PyQt6 installations found.")
        return
    
    print(f"   Found {len(pyqt6_paths)} PyQt6-related paths:")
    for path in pyqt6_paths:
        print(f"     - {path}")
    
    # Ask for confirmation
    print("\n2. Removing corrupted PyQt6 installation...")
    for path in pyqt6_paths:
        try:
            if os.path.isdir(path):
                print(f"   Removing directory: {path}")
                shutil.rmtree(path)
            elif os.path.isfile(path):
                print(f"   Removing file: {path}")
                os.remove(path)
            print(f"   ✓ Removed: {path}")
        except Exception as e:
            print(f"   ✗ Error removing {path}: {e}")
    
    print("\n3. Reinstalling PyQt6...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "PyQt6"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("   ✓ PyQt6 reinstalled successfully!")
            print("\n4. Verifying installation...")
            try:
                from PyQt6 import QtWidgets, QtCore
                print("   ✓ PyQt6.QtWidgets import successful!")
                print("   ✓ PyQt6.QtCore import successful!")
                print("\n" + "=" * 60)
                print("SUCCESS: PyQt6 is now properly installed!")
                print("=" * 60)
            except ImportError as e:
                print(f"   ✗ Import test failed: {e}")
                print("\n   You may need to restart your terminal/IDE.")
        else:
            print(f"   ✗ Installation failed:")
            print(result.stderr)
    except Exception as e:
        print(f"   ✗ Error during installation: {e}")

if __name__ == "__main__":
    main()
