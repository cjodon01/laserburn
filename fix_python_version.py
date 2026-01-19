#!/usr/bin/env python3
"""
Fix Python version compatibility issue by recreating venv with Python 3.12 or 3.11.

Python 3.14.2 is too new and causes segmentation faults with PyQt6.
This script helps set up a compatible Python version.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

def find_python_version(versions):
    """Find an available Python version."""
    for version in versions:
        # Try common locations
        paths = [
            f"/opt/homebrew/bin/python{version}",
            f"/usr/local/bin/python{version}",
            f"/Library/Frameworks/Python.framework/Versions/{version}/bin/python{version}",
        ]
        for path in paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run(
                        [path, "--version"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"   ✓ Found: {path} ({result.stdout.strip()})")
                        return path
                except:
                    pass
    return None

def main():
    print("Python Version Compatibility Fix")
    print("=" * 60)
    print("\nPython 3.14.2 is too new and causes segmentation faults with PyQt6.")
    print("We need to use Python 3.12 or 3.11 instead.\n")
    
    # Check for available Python versions
    print("1. Checking for compatible Python versions...")
    python_path = find_python_version(["3.12", "3.11", "3.10"])
    
    if not python_path:
        print("\n   ✗ No compatible Python version found (3.10, 3.11, or 3.12)")
        print("\n   Please install Python 3.12 via Homebrew:")
        print("   brew install python@3.12")
        print("\n   Then run this script again.")
        return 1
    
    # Check if venv exists
    venv_path = Path(".venv")
    if venv_path.exists():
        print(f"\n2. Backing up existing virtual environment...")
        backup_path = Path(".venv.backup")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.move(venv_path, backup_path)
        print(f"   ✓ Backed up to: {backup_path}")
    
    # Create new venv
    print(f"\n3. Creating new virtual environment with {python_path}...")
    try:
        result = subprocess.run(
            [python_path, "-m", "venv", ".venv"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"   ✗ Failed to create virtual environment:")
            print(result.stderr)
            return 1
        print("   ✓ Virtual environment created")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return 1
    
    # Get venv python
    if sys.platform == "win32":
        venv_python = venv_path / "Scripts" / "python.exe"
    else:
        venv_python = venv_path / "bin" / "python"
    
    # Upgrade pip
    print("\n4. Upgrading pip...")
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        print("   ✓ pip upgraded")
    except Exception as e:
        print(f"   ✗ Failed to upgrade pip: {e}")
        return 1
    
    # Install requirements
    print("\n5. Installing dependencies...")
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"   ✗ Installation failed:")
            print(result.stderr)
            return 1
        print("   ✓ Dependencies installed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return 1
    
    # Verify PyQt6
    print("\n6. Verifying PyQt6 installation...")
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "from PyQt6 import QtWidgets, QtCore; print('PyQt6 OK')"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("   ✓ PyQt6 is working correctly!")
        else:
            print(f"   ✗ PyQt6 verification failed:")
            print(result.stderr)
            return 1
    except Exception as e:
        print(f"   ✗ Error verifying PyQt6: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("SUCCESS: Virtual environment recreated with compatible Python version!")
    print("=" * 60)
    print("\nYou can now run the application with:")
    print("  python run_laserburn.py")
    print("\nOr activate the virtual environment:")
    print("  source .venv/bin/activate")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
