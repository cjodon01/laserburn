#!/usr/bin/env python3
"""
LaserBurn - Main Entry Point

This is the main entry point for the LaserBurn application.
Run with: python -m src.main
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    """Main entry point for LaserBurn application."""
    try:
        # Enable high DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("LaserBurn")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("LaserBurn")
        app.setOrganizationDomain("laserburn.app")
        
        # Import here to avoid circular imports and speed up startup check
        from .ui.mainwindow import MainWindow
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run event loop
        return app.exec()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

