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
            pyqt6_path = os.path.dirname(PyQt6.__file__)
            qt6_plugins = os.path.join(pyqt6_path, 'Qt6', 'plugins')
            if os.path.exists(qt6_plugins):
                os.environ['QT_PLUGIN_PATH'] = qt6_plugins
        except ImportError:
            pass


if __name__ == "__main__":
    # Set up Qt plugins before importing Qt modules
    setup_qt_plugins()
    
    try:
        from src.main import main
        sys.exit(main())
    except ImportError as e:
        print(f"Error: Failed to import LaserBurn modules: {e}")
        print("\nPlease ensure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

