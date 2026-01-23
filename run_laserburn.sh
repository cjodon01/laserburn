#!/bin/bash
# LaserBurn Launcher Script for macOS
# This script sets up the Qt plugin path before launching Python

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Find PyQt6 and set plugin path
PYTHON_CMD="python3"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

# Get PyQt6 plugin path using Python
QT_PLUGIN_PATH=$($PYTHON_CMD -c "
import sys
import os
try:
    import importlib.util
    spec = importlib.util.find_spec('PyQt6')
    if spec and spec.origin:
        pyqt6_path = os.path.dirname(spec.origin)
        plugins_path = os.path.join(pyqt6_path, 'Qt6', 'plugins')
        if os.path.exists(plugins_path):
            print(plugins_path)
except Exception:
    pass
" 2>/dev/null)

# Set environment variables if we found the plugin path
if [ -n "$QT_PLUGIN_PATH" ] && [ -d "$QT_PLUGIN_PATH" ]; then
    export QT_PLUGIN_PATH="$QT_PLUGIN_PATH"
    export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLUGIN_PATH"
    echo "Qt plugin path set to: $QT_PLUGIN_PATH"
fi

# Run the application
exec $PYTHON_CMD run_laserburn.py "$@"
