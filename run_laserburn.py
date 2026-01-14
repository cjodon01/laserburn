#!/usr/bin/env python3
"""
LaserBurn Launcher Script

Simple launcher for the LaserBurn application.
"""

import sys
import os

# Add src to path if needed
if os.path.dirname(__file__) not in sys.path:
    sys.path.insert(0, os.path.dirname(__file__))


def setup_qt_plugins():
    """Set up Qt plugin paths for macOS compatibility."""
    if sys.platform == 'darwin':
        try:
            import PyQt6
            from PyQt6 import QtCore
            
            # PyQt6.__file__ might be None for namespace packages
            # Try to get path from QtCore instead
            pyqt6_path = None
            if hasattr(PyQt6, '__file__') and PyQt6.__file__:
                pyqt6_path = os.path.dirname(PyQt6.__file__)
            elif hasattr(QtCore, '__file__') and QtCore.__file__:
                # Get path from QtCore module
                pyqt6_path = os.path.dirname(os.path.dirname(QtCore.__file__))
            
            possible_plugin_paths = []
            
            if pyqt6_path:
                # Try multiple possible plugin locations relative to PyQt6
                possible_plugin_paths.extend([
                    os.path.join(pyqt6_path, 'Qt6', 'plugins'),
                    os.path.join(pyqt6_path, 'Qt', 'plugins'),
                    os.path.join(pyqt6_path, 'plugins'),
                ])
            
            # Also check if installed via Homebrew or in site-packages
            try:
                import site
                site_packages = site.getsitepackages()
                for site_pkg in site_packages:
                    possible_plugin_paths.extend([
                        os.path.join(site_pkg, 'PyQt6', 'Qt6', 'plugins'),
                        os.path.join(site_pkg, 'PyQt6', 'Qt', 'plugins'),
                    ])
            except:
                pass
            
            # Find the first existing plugin path
            for plugin_path in possible_plugin_paths:
                if plugin_path and os.path.exists(plugin_path):
                    os.environ['QT_PLUGIN_PATH'] = plugin_path
                    # Also set QT_QPA_PLATFORM_PLUGIN_PATH for better compatibility
                    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
                    break
        except (ImportError, AttributeError):
            # If PyQt6 isn't available or has issues, just continue
            # The actual import error will be caught later
            pass


if __name__ == "__main__":
    # Set up Qt plugins before importing Qt modules
    setup_qt_plugins()
    
    # On macOS, also try to set the platform plugin explicitly if needed
    if sys.platform == 'darwin':
        # Try to use cocoa plugin (native macOS)
        if 'QT_QPA_PLATFORM' not in os.environ:
            os.environ['QT_QPA_PLATFORM'] = 'cocoa'
    
    try:
        # Test PyQt6 import before proceeding
        try:
            from PyQt6 import QtWidgets, QtCore
        except ImportError as qt_error:
            print("PyQt6 Import Error:")
            print("=" * 60)
            print(f"Error: {qt_error}")
            print("\nPyQt6 appears to be installed but QtWidgets cannot be imported.")
            print("This usually means PyQt6 installation is incomplete.")
            print("\nTry these solutions:")
            print("1. Reinstall PyQt6 completely:")
            print("   pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip")
            print("   pip install PyQt6")
            print("\n2. If that doesn't work, try installing with --force-reinstall:")
            print("   pip install --force-reinstall --no-cache-dir PyQt6")
            print("\n3. Check your Python version (PyQt6 requires Python 3.8+):")
            print(f"   Current: {sys.version}")
            print("=" * 60)
            sys.exit(1)
        
        from src.main import main
        sys.exit(main())
    except ImportError as e:
        print(f"Error: Failed to import LaserBurn modules: {e}")
        print("\nPlease ensure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        error_msg = str(e)
        if 'platform plugin' in error_msg.lower() or 'qt' in error_msg.lower():
            print("Qt Platform Plugin Error:")
            print("=" * 60)
            print("This error usually occurs when Qt plugins cannot be found.")
            print("\nPossible solutions:")
            print("1. Reinstall PyQt6:")
            print("   pip uninstall PyQt6")
            print("   pip install PyQt6")
            print("\n2. If using a virtual environment, ensure it's activated")
            print("\n3. On macOS, try installing via Homebrew:")
            print("   brew install pyqt6")
            print("\n4. Check if Qt plugins exist:")
            try:
                import PyQt6
                pyqt6_path = os.path.dirname(PyQt6.__file__)
                print(f"   PyQt6 path: {pyqt6_path}")
                plugin_path = os.path.join(pyqt6_path, 'Qt6', 'plugins')
                print(f"   Plugin path: {plugin_path}")
                print(f"   Exists: {os.path.exists(plugin_path)}")
            except:
                pass
            print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

