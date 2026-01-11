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

if __name__ == "__main__":
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

